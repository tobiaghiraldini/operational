"""Upgrade legacy schemaVersion 1 definitions to v2 for @xyflow/react."""

from __future__ import annotations

import uuid
from typing import Any

from apps.workflows.services.react_flow_definition import sanitize_react_flow_definition


def upgrade_v1_document_to_v2(doc: dict[str, Any]) -> dict[str, Any]:
    if doc.get("schemaVersion") != 1:
        return doc
    meta = dict(doc.get("meta") or {})
    meta["engine"] = "react-flow"
    nodes_in = doc.get("nodes") if isinstance(doc.get("nodes"), list) else []
    nodes_out: list[dict[str, Any]] = []
    for i, n in enumerate(nodes_in):
        if not isinstance(n, dict):
            continue
        nid = n.get("id")
        ntype = n.get("type")
        if not isinstance(nid, str) or not isinstance(ntype, str):
            continue
        pos = n.get("position")
        if isinstance(pos, dict) and "x" in pos and "y" in pos:
            try:
                position = {"x": float(pos["x"]), "y": float(pos["y"])}
            except (TypeError, ValueError):
                position = {"x": float((i % 4) * 320), "y": float((i // 4) * 200)}
        else:
            position = {"x": float((i % 4) * 320), "y": float((i // 4) * 200)}
        data = n.get("data")
        data_out = dict(data) if isinstance(data, dict) else {}
        nodes_out.append(
            {
                "id": str(nid).strip(),
                "type": str(ntype).strip(),
                "position": position,
                "data": data_out,
            }
        )
    node_ids = {n["id"] for n in nodes_out}
    edges_in = doc.get("edges") if isinstance(doc.get("edges"), list) else []
    edges_out: list[dict[str, Any]] = []
    for i, e in enumerate(edges_in):
        if not isinstance(e, dict):
            continue
        src, tgt = e.get("source"), e.get("target")
        if not isinstance(src, str) or not isinstance(tgt, str):
            continue
        if src not in node_ids or tgt not in node_ids:
            continue
        eid = e.get("id")
        if not isinstance(eid, str) or not eid.strip():
            eid = f"e-{i}-{uuid.uuid4().hex[:10]}"
        edge: dict[str, Any] = {
            "id": str(eid).strip(),
            "source": str(src),
            "target": str(tgt),
            "type": "default",
        }
        if e.get("animated"):
            edge["animated"] = True
        edges_out.append(edge)
    vp = doc.get("viewport") if isinstance(doc.get("viewport"), dict) else {}
    viewport = {
        "x": float(vp.get("x", 0) or 0),
        "y": float(vp.get("y", 0) or 0),
        "zoom": float(vp.get("zoom", 1) or 1),
    }
    raw_v2 = {
        "schemaVersion": 2,
        "meta": meta,
        "nodes": nodes_out,
        "edges": edges_out,
        "viewport": viewport,
    }
    return sanitize_react_flow_definition(raw_v2)
