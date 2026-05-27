import { Handle, Position, type NodeProps } from "@xyflow/react";

export function StepNode({ data }: NodeProps) {
  const d = (data || {}) as Record<string, string>;
  return (
    <div className="min-w-[16rem] rounded-xl border border-border bg-card p-3 text-left text-foreground shadow-sm">
      <Handle type="target" position={Position.Top} className="!bg-muted-foreground" />
      <p className="text-[10px] font-semibold uppercase tracking-wide text-muted-foreground">{d.source_kind || "Step"}</p>
      <p className="truncate text-sm font-semibold">{d.title || "Step"}</p>
      <p className="mt-0.5 line-clamp-2 text-xs text-muted-foreground">{d.subtitle}</p>
      <Handle type="source" position={Position.Bottom} className="!bg-muted-foreground" />
    </div>
  );
}
