import { Handle, Position, type NodeProps } from "@xyflow/react";

export function MergeNode({ data }: NodeProps) {
  const d = (data || {}) as Record<string, string>;
  return (
    <div className="min-w-[12rem] rounded-xl border border-border bg-secondary/30 p-3 text-left text-foreground">
      <Handle type="target" position={Position.Top} id="in1" className="!left-[35%] !bg-muted-foreground" />
      <Handle type="target" position={Position.Top} id="in2" className="!left-[65%] !bg-muted-foreground" />
      <p className="text-[10px] font-semibold uppercase tracking-wide text-muted-foreground">Merge</p>
      <p className="truncate text-sm font-semibold">{d.title || "Converge"}</p>
      <p className="truncate text-xs text-muted-foreground">{d.subtitle}</p>
      <Handle type="source" position={Position.Bottom} className="!bg-muted-foreground" />
    </div>
  );
}
