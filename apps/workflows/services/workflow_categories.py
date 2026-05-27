"""Workflow use-case categories (knowledge, automation, procedures, …).

Extend ``CATEGORY_NODE_EXTRAS`` when you add category-specific Alpine ``x-node``
``type`` strings and register matching templates in the editor partial.
"""

from __future__ import annotations

from typing import Final

# Values stored on ``Workflow.category`` and in ``definition["meta"]["category"]``.
CATEGORY_KNOWLEDGE: Final = "knowledge"
CATEGORY_AUTOMATION: Final = "automation"
CATEGORY_PROCEDURE: Final = "procedure"
CATEGORY_GENERAL: Final = "general"

CATEGORY_CHOICES: Final[tuple[tuple[str, str], ...]] = (
    (CATEGORY_KNOWLEDGE, "Knowledge mapping"),
    (CATEGORY_AUTOMATION, "Automation pipeline"),
    (CATEGORY_PROCEDURE, "Procedure / SOP"),
    (CATEGORY_GENERAL, "General"),
)

CATEGORY_LABELS: Final[dict[str, str]] = {k: v for k, v in CATEGORY_CHOICES}

# Optional extra node ``type`` names per category (Alpine x-node / AlpineFlow).
# Base types (step, junction, merge, humanGate) are always available; add only
# category-specific types here when you implement dedicated cards.
CATEGORY_NODE_EXTRAS: Final[dict[str, frozenset[str]]] = {
    CATEGORY_KNOWLEDGE: frozenset(),
    CATEGORY_AUTOMATION: frozenset(),
    CATEGORY_PROCEDURE: frozenset(),
    CATEGORY_GENERAL: frozenset(),
}

# Default ``x-node`` / AlpineFlow ``type`` for the generic “Add node” toolbar action.
# Category-specific cards (e.g. ``concept``) can override when implemented.
CATEGORY_PRIMARY_NODE_TYPE: Final[dict[str, str]] = {
    CATEGORY_KNOWLEDGE: "step",
    CATEGORY_AUTOMATION: "step",
    CATEGORY_PROCEDURE: "step",
    CATEGORY_GENERAL: "step",
}


def primary_node_type_for_category(category: str) -> str:
    return CATEGORY_PRIMARY_NODE_TYPE.get(category, "step")


def normalize_category(value: str | None) -> str:
    allowed = {c for c, _ in CATEGORY_CHOICES}
    if value in allowed:
        return value
    return CATEGORY_GENERAL
