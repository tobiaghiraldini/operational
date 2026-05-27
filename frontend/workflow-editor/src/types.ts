import type { Node, Edge } from "@xyflow/react";

export type WorkflowDefinitionV2 = {
  schemaVersion: 2;
  meta: Record<string, unknown>;
  nodes: Node[];
  edges: Edge[];
  viewport: { x: number; y: number; zoom: number };
};
