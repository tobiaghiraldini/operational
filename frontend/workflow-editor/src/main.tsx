import "@xyflow/react/dist/style.css";
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { App } from "./App";

function readDataset(el: HTMLElement, name: string): string {
  return el.dataset[name] ?? "";
}

const mount = document.getElementById("workflow-editor-root");
if (mount) {
  const apiUrl = readDataset(mount, "apiUrl");
  const linksApiUrl = readDataset(mount, "linksApiUrl");
  const csrfToken = readDataset(mount, "csrfToken");
  const category = readDataset(mount, "category");
  const primaryNodeType = readDataset(mount, "primaryNodeType");
  let nodeTypes: string[] = [];
  const ntEl = document.getElementById("workflow-editor-node-types");
  try {
    nodeTypes = ntEl ? JSON.parse(ntEl.textContent || "[]") : [];
  } catch {
    nodeTypes = [];
  }
  createRoot(mount).render(
    <StrictMode>
      <App
        definitionApiUrl={apiUrl}
        linksApiUrl={linksApiUrl}
        csrfToken={csrfToken}
        category={category}
        nodeTypes={nodeTypes}
        primaryNodeType={primaryNodeType || "step"}
      />
    </StrictMode>,
  );
}
