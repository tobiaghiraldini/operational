"""Resolve which node card ``type`` strings are valid for a workflow category.

AlpineFlow ``x-node`` templates register one ``type`` each. The editor includes
templates for all types in ``node_types_for_category`` so new nodes can render.
When you add a dedicated card (e.g. ``concept`` for knowledge), add it to
``ALLOWED_NODE_TYPES`` in ``definition_validate`` and list it under the right
key in ``apps.workflows.services.workflow_categories.CATEGORY_NODE_EXTRAS``.
"""

from __future__ import annotations

from apps.workflows.services.workflow_categories import CATEGORY_NODE_EXTRAS

# Shared card types (implemented in ``dashboard_editor.html``).
BASE_FLOW_NODE_TYPES: frozenset[str] = frozenset(
    {"step", "junction", "merge", "humanGate"}
)


def node_types_for_category(category: str) -> frozenset[str]:
    extras = CATEGORY_NODE_EXTRAS.get(category, frozenset())
    return BASE_FLOW_NODE_TYPES | extras
