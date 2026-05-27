"""Validate persisted workflow definitions before save (React Flow / schema v2)."""

from __future__ import annotations

from typing import Any

from apps.workflows.services.node_card_registry import node_types_for_category
from apps.workflows.services.workflow_categories import CATEGORY_LABELS


class DefinitionValidationError(ValueError):
    pass


def validate_workflow_definition(raw: Any, *, workflow_category: str) -> None:
    if not isinstance(raw, dict):
        raise DefinitionValidationError("definition must be a JSON object")
    version = raw.get("schemaVersion")
    if version != 2:
        raise DefinitionValidationError("schemaVersion must be 2")
    meta = raw.get("meta")
    if meta is not None:
        if not isinstance(meta, dict):
            raise DefinitionValidationError("meta must be an object")
        mc = meta.get("category")
        if mc is not None and mc not in CATEGORY_LABELS:
            raise DefinitionValidationError("meta.category must be a known category")
        npv = meta.get("nodePaletteVersion")
        if npv is not None and type(npv) is not int:
            raise DefinitionValidationError("meta.nodePaletteVersion must be an integer")
    nodes = raw.get("nodes")
    edges = raw.get("edges")
    viewport = raw.get("viewport")
    if not isinstance(nodes, list):
        raise DefinitionValidationError("nodes must be a list")
    if not isinstance(edges, list):
        raise DefinitionValidationError("edges must be a list")
    if not isinstance(viewport, dict):
        raise DefinitionValidationError("viewport must be an object")
    for key in ("x", "y", "zoom"):
        if key not in viewport:
            raise DefinitionValidationError(f"viewport missing key {key!r}")
    allowed_types = node_types_for_category(workflow_category)
    node_ids: set[str] = set()
    for i, node in enumerate(nodes):
        if not isinstance(node, dict):
            raise DefinitionValidationError(f"nodes[{i}] must be an object")
        nid = node.get("id")
        if not isinstance(nid, str) or not nid.strip():
            raise DefinitionValidationError(f"nodes[{i}].id must be a non-empty string")
        if nid in node_ids:
            raise DefinitionValidationError(f"duplicate node id {nid!r}")
        node_ids.add(str(nid))
        ntype = node.get("type")
        if ntype not in allowed_types:
            raise DefinitionValidationError(
                f"nodes[{i}].type must be one of {sorted(allowed_types)}"
            )
        data = node.get("data")
        if data is not None and not isinstance(data, dict):
            raise DefinitionValidationError(f"nodes[{i}].data must be an object")
        pos = node.get("position")
        if not isinstance(pos, dict) or not all(k in pos for k in ("x", "y")):
            raise DefinitionValidationError(f"nodes[{i}].position must have x and y")
        try:
            float(pos["x"])
            float(pos["y"])
        except (KeyError, TypeError, ValueError):
            raise DefinitionValidationError(f"nodes[{i}].position x and y must be numeric")
    for i, edge in enumerate(edges):
        if not isinstance(edge, dict):
            raise DefinitionValidationError(f"edges[{i}] must be an object")
        eid = edge.get("id")
        if not isinstance(eid, str) or not eid.strip():
            raise DefinitionValidationError(f"edges[{i}].id must be a non-empty string")
        src, tgt = edge.get("source"), edge.get("target")
        if not isinstance(src, str) or not isinstance(tgt, str):
            raise DefinitionValidationError(f"edges[{i}] needs string source and target")
        if src not in node_ids or tgt not in node_ids:
            raise DefinitionValidationError(f"edges[{i}] references unknown node")


def normalize_definition(raw: dict, *, workflow_category: str) -> dict:
    validate_workflow_definition(raw, workflow_category=workflow_category)
    out = dict(raw)
    prev = out.get("meta")
    prev_dict = prev if isinstance(prev, dict) else {}
    raw_npv = prev_dict.get("nodePaletteVersion")
    try:
        npv = int(raw_npv) if raw_npv is not None else 1
    except (TypeError, ValueError):
        npv = 1
    if npv < 1:
        npv = 1
    out["meta"] = {
        **prev_dict,
        "category": workflow_category,
        "nodePaletteVersion": npv,
        "engine": "react-flow",
    }
    out["schemaVersion"] = 2
    return out
