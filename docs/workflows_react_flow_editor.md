# Workflow editor (React Flow)

The tenant dashboard workflow **editor** route loads a small **React + Vite** bundle that talks to the existing session-authenticated JSON API.

## Build

From the project root:

- **Production bundle** (writes to `static/js/workflow-editor/`):

  ```bash
  npm run build:workflow-editor
  ```

- **Dev server** (Vite HMR; adjust `vite.config` if the Django origin differs):

  ```bash
  npm run watch:workflow-editor
  ```

After changing dashboard layout styles for the canvas, rebuild dashboard CSS:

```bash
npm run build:dashboard:css
```

## Architecture

- **Template:** `apps/workflows/templates/workflows/dashboard_editor.html` mounts `#workflow-editor-root` with `data-api-url`, `data-links-api-url`, `data-csrf-token`, category, primary node type, and a `json_script` for allowed node types.
- **Frontend:** `frontend/workflow-editor/` — `@xyflow/react` document in memory; **GET/PUT** `.../definition/`; **GET/POST** `.../links/` and **DELETE** `.../links/<uuid>/` for `WorkflowNodeLink` rows.
- **Persistence:** `Workflow.definition` is the canonical **schemaVersion 2** graph (`nodes`, `edges`, `viewport`, `meta.engine: react-flow`). Legacy v1 rows are upgraded by migration `0007_upgrade_workflow_definitions_v1_to_v2`.
