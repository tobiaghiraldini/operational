import { Handle, Position, type NodeProps } from "@xyflow/react";

export function JunctionNode({ data }: NodeProps) {
  const d = (data || {}) as Record<string, string>;
  return (
    <div className="min-w-[14rem] rounded-xl border border-dashed border-chart-1/50 bg-card/90 p-3 text-left text-foreground">
      <Handle type="target" position={Position.Top} className="!bg-chart-1" />
      <div className="flex items-center gap-2">
        <span className="flex size-8 items-center justify-center rounded-lg bg-chart-1/15 text-xs font-bold text-chart-1">IF</span>
        <div className="min-w-0">
          <p className="text-[10px] font-semibold uppercase tracking-wide text-muted-foreground">Junction</p>
          <p className="truncate text-sm font-semibold">{d.title || "Junction"}</p>
          <p className="truncate text-xs text-muted-foreground">{d.subtitle}</p>
        </div>
      </div>
      <Handle type="source" position={Position.Bottom} id="a" className="!left-[35%] !bg-chart-1" />
      <Handle type="source" position={Position.Bottom} id="b" className="!left-[65%] !bg-chart-1" />
    </div>
  );
}
