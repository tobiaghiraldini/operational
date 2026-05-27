import type { Edge, Node, OnConnect, OnEdgesChange, OnNodesChange } from "@xyflow/react";
import {
  addEdge,
  Background,
  BackgroundVariant,
  Controls,
  MiniMap,
  Panel,
  ReactFlow,
  ReactFlowProvider,
  useEdgesState,
  useNodesState,
  useReactFlow,
} from "@xyflow/react";
import type { Dispatch, SetStateAction } from "react";
import { useCallback, useEffect, useMemo, useState } from "react";
import { HumanGateNode } from "./nodes/HumanGateNode";
import { JunctionNode } from "./nodes/JunctionNode";
import { MergeNode } from "./nodes/MergeNode";
import { StepNode } from "./nodes/StepNode";
import type { WorkflowDefinitionV2 } from "./types";

export type AppProps = {
  definitionApiUrl: string;
  linksApiUrl: string;
  csrfToken: string;
  category: string;
  nodeTypes: string[];
  primaryNodeType: string;
};

function newId(): string {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return crypto.randomUUID();
  }
  return `n-${Date.now()}-${Math.floor(Math.random() * 1e9)}`;
}

function defaultDataForType(type: string): Record<string, string> {
  if (type === "junction") {
    return { title: "Junction", subtitle: "Conditional split", mode: "conditional" };
  }
  if (type === "merge") {
    return { title: "Converge", subtitle: "Join branches" };
  }
  if (type === "humanGate") {
    return {
      title: "Human review",
      subtitle: "Approve before continue",
      assignee: "Operations",
      decision: "Approve or request changes",
    };
  }
  return {
    title: "Step",
    subtitle: "",
    status: "new",
    status_label: "New",
    source_kind: "",
    source_label: "",
    account_label: "",
    account_name: "",
    tools_summary: "",
  };
}

type SavePanelProps = {
  definitionApiUrl: string;
  csrfToken: string;
  category: string;
  meta: Record<string, unknown>;
  nodes: Node[];
  edges: Edge[];
  onStatus: (s: string) => void;
};

function SavePanel(props: SavePanelProps) {
  const { definitionApiUrl, csrfToken, category, meta, nodes, edges, onStatus } = props;
  const rf = useReactFlow();

  const save = useCallback(async () => {
    const v = rf.getViewport();
    const body: WorkflowDefinitionV2 = {
      schemaVersion: 2,
      meta: {
        ...meta,
        category: category || String(meta.category ?? "general"),
        engine: "react-flow",
      },
      nodes: nodes.map((n) => ({
        id: n.id,
        type: n.type ?? "step",
        position: n.position,
        data: (n.data as Record<string, unknown>) || {},
      })) as Node[],
      edges: edges.map((e) => ({
        id: e.id,
        source: e.source,
        target: e.target,
        type: e.type ?? "default",
        animated: e.animated,
        ...(e.markerEnd ? { markerEnd: e.markerEnd } : {}),
        ...(e.data && typeof e.data === "object" ? { data: e.data } : {}),
      })) as Edge[],
      viewport: { x: v.x, y: v.y, zoom: v.zoom },
    };
    onStatus("Saving…");
    try {
      const r = await fetch(definitionApiUrl, {
        method: "PUT",
        credentials: "same-origin",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": csrfToken,
        },
        body: JSON.stringify(body),
      });
      if (!r.ok) {
        let msg = `Save failed (${r.status})`;
        try {
          const t = await r.text();
          const j = JSON.parse(t) as { detail?: string };
          if (j.detail) msg = j.detail;
        } catch {
          /* ignore */
        }
        onStatus(msg);
        return;
      }
      onStatus("Saved");
    } catch {
      onStatus("Save failed (network)");
    }
  }, [category, csrfToken, definitionApiUrl, edges, meta, nodes, onStatus, rf]);

  return (
    <Panel position="top-right" className="m-2 flex gap-2">
      <button
        type="button"
        className="rounded-md border border-border bg-card px-3 py-1.5 text-sm font-medium text-foreground shadow-sm hover:bg-muted"
        onClick={() => void save()}
      >
        Save
      </button>
    </Panel>
  );
}

type AddPanelProps = {
  nodeTypes: string[];
  primaryNodeType: string;
  setNodes: Dispatch<SetStateAction<Node[]>>;
  setSelectedId: (id: string | null) => void;
  setStatus: (s: string) => void;
};

function AddNodePanel(props: AddPanelProps) {
  const { nodeTypes, primaryNodeType, setNodes, setSelectedId, setStatus } = props;
  const rf = useReactFlow();

  const addNode = useCallback(
    (type: string) => {
      if (!nodeTypes.includes(type)) return;
      const id = newId();
      const pos = rf.screenToFlowPosition({
        x: window.innerWidth * 0.38,
        y: window.innerHeight * 0.38,
      });
      setNodes((ns) => [
        ...ns,
        {
          id,
          type,
          position: pos,
          data: defaultDataForType(type),
        },
      ]);
      setSelectedId(id);
      setStatus("");
    },
    [nodeTypes, rf, setNodes, setSelectedId, setStatus],
  );

  return (
    <Panel position="top-left" className="m-2 flex max-w-[20rem] flex-col gap-2 rounded-lg border border-border bg-card/95 p-2 text-xs shadow-md backdrop-blur">
      <span className="font-medium text-foreground">Add nodes</span>
      {nodeTypes.includes(primaryNodeType) && (
        <button
          type="button"
          className="rounded border border-primary/40 bg-primary px-2 py-1 text-left text-primary-foreground"
          onClick={() => addNode(primaryNodeType)}
        >
          Add primary ({primaryNodeType})
        </button>
      )}
      {nodeTypes.includes("junction") && (
        <button type="button" className="rounded border border-border bg-secondary px-2 py-1 text-left" onClick={() => addNode("junction")}>
          Branch (junction)
        </button>
      )}
      {nodeTypes.includes("merge") && (
        <button type="button" className="rounded border border-border bg-secondary px-2 py-1 text-left" onClick={() => addNode("merge")}>
          Merge
        </button>
      )}
      {nodeTypes.includes("humanGate") && (
        <button type="button" className="rounded border border-border bg-secondary px-2 py-1 text-left" onClick={() => addNode("humanGate")}>
          Review gate
        </button>
      )}
      <span className="text-muted-foreground">Drag from a handle to another node to connect.</span>
    </Panel>
  );
}

function FlowEditor(props: AppProps) {
  const { definitionApiUrl, linksApiUrl, csrfToken, nodeTypes, primaryNodeType, category } = props;
  const [nodes, setNodes, onNodesChange] = useNodesState<Node>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([]);
  const [viewport, setViewport] = useState({ x: 0, y: 0, zoom: 1 });
  const [meta, setMeta] = useState<Record<string, unknown>>({});
  const [status, setStatus] = useState("Loading…");
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [flowKey, setFlowKey] = useState(0);
  const [links, setLinks] = useState<
    { id: string; node_id: string; app_label: string; model: string; object_id: string; role: string }[]
  >([]);

  const nodeTypesMap = useMemo(
    () => ({
      step: StepNode,
      junction: JunctionNode,
      merge: MergeNode,
      humanGate: HumanGateNode,
    }),
    [],
  );

  const loadDefinition = useCallback(async () => {
    setStatus("Loading…");
    try {
      const r = await fetch(definitionApiUrl, { credentials: "same-origin" });
      if (!r.ok) {
        setStatus(`Load failed (${r.status})`);
        return;
      }
      const raw = (await r.json()) as WorkflowDefinitionV2;
      if (raw.schemaVersion !== 2) {
        setStatus("Unsupported definition version (expected schemaVersion 2).");
        return;
      }
      setNodes((raw.nodes || []) as Node[]);
      setEdges((raw.edges || []) as Edge[]);
      const vp = raw.viewport || { x: 0, y: 0, zoom: 1 };
      setViewport({
        x: Number(vp.x) || 0,
        y: Number(vp.y) || 0,
        zoom: typeof vp.zoom === "number" && vp.zoom > 0 ? vp.zoom : 1,
      });
      setMeta(typeof raw.meta === "object" && raw.meta !== null ? { ...raw.meta } : {});
      setFlowKey((k) => k + 1);
      setStatus("");
    } catch {
      setStatus("Load failed (network)");
    }
  }, [definitionApiUrl, setEdges, setNodes]);

  const loadLinks = useCallback(async () => {
    if (!linksApiUrl) return;
    try {
      const r = await fetch(linksApiUrl, { credentials: "same-origin" });
      if (!r.ok) return;
      const data = await r.json();
      if (Array.isArray(data)) setLinks(data);
    } catch {
      /* ignore */
    }
  }, [linksApiUrl]);

  useEffect(() => {
    void loadDefinition();
  }, [loadDefinition]);

  useEffect(() => {
    void loadLinks();
  }, [loadLinks]);

  const onConnect: OnConnect = useCallback(
    (connection) => {
      setEdges((eds) =>
        addEdge(
          {
            ...connection,
            id: newId(),
            type: "default",
          },
          eds,
        ),
      );
      setStatus("");
    },
    [setEdges],
  );

  const onEdgesChangeWrapped: OnEdgesChange = useCallback(
    (changes) => {
      onEdgesChange(changes);
      setStatus("");
    },
    [onEdgesChange],
  );

  const onNodesChangeWrapped: OnNodesChange = useCallback(
    (changes) => {
      onNodesChange(changes);
      setStatus("");
    },
    [onNodesChange],
  );

  const selected = nodes.find((n) => n.id === selectedId) ?? null;

  const updateSelectedData = (patch: Record<string, string>) => {
    if (!selectedId) return;
    setNodes((ns) =>
      ns.map((n) =>
        n.id === selectedId
          ? { ...n, data: { ...(typeof n.data === "object" ? n.data : {}), ...patch } }
          : n,
      ),
    );
  };

  const deleteLink = async (linkId: string) => {
    if (!linksApiUrl) return;
    const url = `${linksApiUrl.replace(/\/$/, "")}/${linkId}/`;
    const r = await fetch(url, {
      method: "DELETE",
      credentials: "same-origin",
      headers: { "X-CSRFToken": csrfToken },
    });
    if (r.ok) void loadLinks();
  };

  const [linkForm, setLinkForm] = useState({
    app_label: "",
    model: "",
    object_id: "",
    role: "",
  });

  const addLink = async () => {
    if (!selectedId || !linksApiUrl) return;
    const r = await fetch(linksApiUrl, {
      method: "POST",
      credentials: "same-origin",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": csrfToken,
      },
      body: JSON.stringify({
        node_id: selectedId,
        app_label: linkForm.app_label.trim(),
        model: linkForm.model.trim(),
        object_id: linkForm.object_id.trim(),
        role: linkForm.role.trim(),
      }),
    });
    if (r.ok) {
      setLinkForm({ app_label: "", model: "", object_id: "", role: "" });
      void loadLinks();
    } else {
      let msg = `Link failed (${r.status})`;
      try {
        const j = (await r.json()) as { detail?: string };
        if (j.detail) msg = j.detail;
      } catch {
        /* ignore */
      }
      setStatus(msg);
    }
  };

  return (
    <div className="workflow-rf-shell flex min-h-0 flex-1 flex-col gap-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <span className="text-xs text-muted-foreground">{status}</span>
        <button
          type="button"
          className="rounded-md border border-border bg-secondary px-3 py-1.5 text-sm font-medium text-secondary-foreground hover:bg-secondary/80"
          onClick={() => void loadDefinition()}
        >
          Reload graph
        </button>
      </div>
      <div className="workflow-rf-canvas relative min-h-[min(52dvh,520px)] flex-1 rounded-xl border border-border bg-background">
        <ReactFlow
          key={flowKey}
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChangeWrapped}
          onEdgesChange={onEdgesChangeWrapped}
          onConnect={onConnect}
          nodeTypes={nodeTypesMap}
          fitView
          minZoom={0.2}
          maxZoom={2}
          defaultViewport={viewport}
          onSelectionChange={({ nodes: sel }) => {
            const n = sel[0];
            setSelectedId(n?.id ?? null);
          }}
        >
          <Background variant={BackgroundVariant.Dots} gap={22} size={0.55} color="var(--muted-foreground)" />
          <Controls />
          <MiniMap pannable zoomable className="!bg-card" />
          <AddNodePanel
            nodeTypes={nodeTypes}
            primaryNodeType={primaryNodeType}
            setNodes={setNodes}
            setSelectedId={setSelectedId}
            setStatus={setStatus}
          />
          <SavePanel
            definitionApiUrl={definitionApiUrl}
            csrfToken={csrfToken}
            category={category}
            meta={meta}
            nodes={nodes}
            edges={edges}
            onStatus={setStatus}
          />
        </ReactFlow>
      </div>
      {selected && (
        <div className="grid gap-3 rounded-xl border border-border bg-card/60 p-4 text-sm md:grid-cols-2">
          <div>
            <p className="text-xs font-medium text-muted-foreground">Inspector</p>
            <p className="mt-1 text-xs text-muted-foreground">
              Node {selected.id.slice(0, 8)}… · {String(selected.type)}
            </p>
            <label className="mt-2 block text-xs text-muted-foreground">Title</label>
            <input
              className="mt-1 w-full rounded-md border border-border bg-background px-2 py-1.5 text-sm"
              value={String((selected.data as Record<string, string>)?.title ?? "")}
              onChange={(e) => updateSelectedData({ title: e.target.value })}
            />
            <label className="mt-2 block text-xs text-muted-foreground">Subtitle</label>
            <textarea
              className="mt-1 w-full rounded-md border border-border bg-background px-2 py-1.5 text-sm"
              rows={2}
              value={String((selected.data as Record<string, string>)?.subtitle ?? "")}
              onChange={(e) => updateSelectedData({ subtitle: e.target.value })}
            />
            {selected.type === "humanGate" && (
              <>
                <label className="mt-2 block text-xs text-muted-foreground">Reviewer</label>
                <input
                  className="mt-1 w-full rounded-md border border-border bg-background px-2 py-1.5 text-sm"
                  value={String((selected.data as Record<string, string>)?.assignee ?? "")}
                  onChange={(e) => updateSelectedData({ assignee: e.target.value })}
                />
                <label className="mt-2 block text-xs text-muted-foreground">Decision</label>
                <input
                  className="mt-1 w-full rounded-md border border-border bg-background px-2 py-1.5 text-sm"
                  value={String((selected.data as Record<string, string>)?.decision ?? "")}
                  onChange={(e) => updateSelectedData({ decision: e.target.value })}
                />
              </>
            )}
            {selected.type === "junction" && (
              <>
                <label className="mt-2 block text-xs text-muted-foreground">Mode</label>
                <input
                  className="mt-1 w-full rounded-md border border-border bg-background px-2 py-1.5 text-sm"
                  value={String((selected.data as Record<string, string>)?.mode ?? "")}
                  onChange={(e) => updateSelectedData({ mode: e.target.value })}
                />
              </>
            )}
          </div>
          <div>
            <p className="text-xs font-medium text-muted-foreground">Knowledge links (GFK)</p>
            <p className="mt-1 text-xs text-muted-foreground">Attach a tenant object (app_label, model, object_id).</p>
            <div className="mt-2 grid gap-2">
              <input
                placeholder="app_label"
                className="rounded-md border border-border bg-background px-2 py-1 text-xs"
                value={linkForm.app_label}
                onChange={(e) => setLinkForm((f) => ({ ...f, app_label: e.target.value }))}
              />
              <input
                placeholder="model"
                className="rounded-md border border-border bg-background px-2 py-1 text-xs"
                value={linkForm.model}
                onChange={(e) => setLinkForm((f) => ({ ...f, model: e.target.value }))}
              />
              <input
                placeholder="object_id"
                className="rounded-md border border-border bg-background px-2 py-1 text-xs"
                value={linkForm.object_id}
                onChange={(e) => setLinkForm((f) => ({ ...f, object_id: e.target.value }))}
              />
              <input
                placeholder="role (optional)"
                className="rounded-md border border-border bg-background px-2 py-1 text-xs"
                value={linkForm.role}
                onChange={(e) => setLinkForm((f) => ({ ...f, role: e.target.value }))}
              />
              <button type="button" className="rounded-md bg-primary px-2 py-1 text-xs text-primary-foreground" onClick={() => void addLink()}>
                Add link to selected node
              </button>
            </div>
            <ul className="mt-3 max-h-40 space-y-1 overflow-auto text-xs">
              {links
                .filter((l) => l.node_id === selectedId)
                .map((l) => (
                  <li key={l.id} className="flex items-center justify-between gap-2 border-b border-border/50 py-1">
                    <span className="truncate">
                      {l.app_label}.{l.model} #{l.object_id}
                      {l.role ? ` (${l.role})` : ""}
                    </span>
                    <button type="button" className="shrink-0 text-destructive" onClick={() => void deleteLink(l.id)}>
                      Remove
                    </button>
                  </li>
                ))}
            </ul>
          </div>
        </div>
      )}
    </div>
  );
}

export function App(props: AppProps) {
  return (
    <ReactFlowProvider>
      <FlowEditor {...props} />
    </ReactFlowProvider>
  );
}
