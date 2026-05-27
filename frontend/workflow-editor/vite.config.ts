import path from "node:path";
import { fileURLToPath } from "node:url";
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

const root = path.dirname(fileURLToPath(import.meta.url));

export default defineConfig({
  plugins: [react()],
  root,
  /** Browser IIFE has no `process`; React checks `process.env.NODE_ENV` in dev branches. */
  define: {
    "process.env.NODE_ENV": JSON.stringify("production"),
  },
  build: {
    lib: {
      entry: path.resolve(root, "src/main.tsx"),
      name: "WorkflowEditor",
      formats: ["iife"],
      fileName: () => "workflow-editor",
    },
    outDir: path.resolve(root, "../../static/js/workflow-editor"),
    emptyOutDir: true,
    rollupOptions: {
      output: {
        entryFileNames: "workflow-editor.js",
        assetFileNames: "workflow-editor.[ext]",
        inlineDynamicImports: true,
      },
    },
  },
});
