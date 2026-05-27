import { Handle, Position, type NodeProps } from "@xyflow/react";

export function HumanGateNode({ data }: NodeProps) {
  const d = (data || {}) as Record<string, string>;
  return (
    <div className="min-w-[16rem] rounded-xl border border-amber-500/30 bg-card p-3 text-left text-foreground">
      <Handle type="target" position={Position.Top} className="!bg-amber-500" />
      <div className="flex items-start gap-2">
        <span className="flex size-8 shrink-0 items-center justify-center rounded-lg bg-amber-500/15 text-[10px] font-bold text-amber-600">
          HR
        </span>
        <div className="min-w-0">
          <p className="text-[10px] font-semibold uppercase tracking-wide text-muted-foreground">Gate</p>
          <p className="truncate text-sm font-semibold">{d.title || "Human review"}</p>
          <p className="mt-0.5 text-xs text-muted-foreground">{d.subtitle}</p>
          <p className="mt-2 text-xs">
            <span className="text-muted-foreground">Reviewer</span> · {d.assignee}
          </p>
        </div>
      </div>
      <Handle type="source" position={Position.Bottom} className="!bg-amber-500" />
    </div>
  );
}
