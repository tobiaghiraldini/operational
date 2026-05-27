"""Default graph document for new workflows (@xyflow/react, schema v2)."""

from __future__ import annotations

from apps.workflows.services.workflow_categories import normalize_category


def default_workflow_definition(category: str | None = None) -> dict:
    cat = normalize_category(category)
    return {
        "schemaVersion": 2,
        "meta": {
            "category": cat,
            "nodePaletteVersion": 1,
            "engine": "react-flow",
        },
        "nodes": [
            {
                "id": "start-1",
                "type": "step",
                "position": {"x": 0, "y": 0},
                "data": {
                    "title": "Start",
                    "subtitle": "Describe the entry point for this workflow.",
                    "status": "new",
                    "status_label": "New",
                    "source_kind": "",
                    "source_label": "",
                    "account_label": "",
                    "account_name": "",
                    "tools_summary": "",
                },
            },
        ],
        "edges": [],
        "viewport": {"x": 0, "y": 0, "zoom": 1},
    }
