"""Sanitize workflow definitions persisted for @xyflow/react (schemaVersion 2)."""

from __future__ import annotations

import uuid
from typing import Any


def _edge_id(raw: dict[str, Any], idx: int) -> str:
    eid = raw.get("id")
    if isinstance(eid, str) and eid.strip():
        return str(eid)
    return f"e-{idx}-{uuid.uuid4().hex[:12]}"


def sanitize_react_flow_definition(raw: dict[str, Any]) -> dict[str, Any]:
    """Return a minimal v2 document suitable for storage and validation."""
    vp = raw.get("viewport") if isinstance(raw.get("viewport"), dict) else {}
    viewport = {
        "x": float(vp.get("x", 0) or 0),
        "y": float(vp.get("y", 0) or 0),
        "zoom": float(vp.get("zoom", 1) or 1) if float(vp.get("zoom", 1) or 1) > 0 else 1.0,
    }
    meta = raw.get("meta")
    meta_out: dict[str, Any] = dict(meta) if isinstance(meta, dict) else {}
    meta_out.setdefault("engine", "react-flow")

    nodes_in = raw.get("nodes") if isinstance(raw.get("nodes"), list) else []
    nodes_out: list[dict[str, Any]] = []
    for n in nodes_in:
        if not isinstance(n, dict):
            continue
        nid = n.get("id")
        ntype = n.get("type")
        if not isinstance(nid, str) or not nid.strip():
            continue
        if not isinstance(ntype, str) or not ntype.strip():
            continue
        pos = n.get("position")
        position: dict[str, float] = {"x": 0.0, "y": 0.0}
        if isinstance(pos, dict):
            try:
                position = {"x": float(pos["x"]), "y": float(pos["y"])}
            except (KeyError, TypeError, ValueError):
                position = {"x": 0.0, "y": 0.0}
        data = n.get("data")
        data_out: dict[str, Any] = dict(data) if isinstance(data, dict) else {}
        nodes_out.append(
            {
                "id": str(nid).strip(),
                "type": str(ntype).strip(),
                "position": position,
                "data": data_out,
            }
        )

    node_ids = {n["id"] for n in nodes_out}
    edges_in = raw.get("edges") if isinstance(raw.get("edges"), list) else []
    edges_out: list[dict[str, Any]] = []
    for i, e in enumerate(edges_in):
        if not isinstance(e, dict):
            continue
        src, tgt = e.get("source"), e.get("target")
        if not isinstance(src, str) or not isinstance(tgt, str):
            continue
        if src not in node_ids or tgt not in node_ids:
            continue
        et = e.get("type")
        edge: dict[str, Any] = {
            "id": _edge_id(e, i),
            "source": str(src),
            "target": str(tgt),
            "type": str(et).strip() if isinstance(et, str) and et.strip() else "default",
        }
        if e.get("animated"):
            edge["animated"] = True
        if isinstance(e.get("data"), dict):
            edge["data"] = dict(e["data"])
        return_marker = e.get("markerEnd")
        if return_marker is not None:
            edge["markerEnd"] = return_marker
        edges_out.append(edge)

    return {
        "schemaVersion": 2,
        "meta": meta_out,
        "nodes": nodes_out,
        "edges": edges_out,
        "viewport": viewport,
    }
