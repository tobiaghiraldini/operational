"""Tests for workflow definition validation, upgrade, and URL wiring."""

from __future__ import annotations

from django.test import SimpleTestCase
from django.urls import NoReverseMatch, reverse

from apps.workflows.services.default_definition import default_workflow_definition
from apps.workflows.services.definition_validate import (
    DefinitionValidationError,
    normalize_definition,
    validate_workflow_definition,
)
from apps.workflows.services.react_flow_definition import sanitize_react_flow_definition
from apps.workflows.services.upgrade_definition_v1_to_v2 import upgrade_v1_document_to_v2
from apps.workflows.services.workflow_categories import (
    CATEGORY_AUTOMATION,
    CATEGORY_GENERAL,
    CATEGORY_PROCEDURE,
    primary_node_type_for_category,
)


class WorkflowDefinitionValidateTests(SimpleTestCase):
    def test_default_definition_validates(self):
        d = default_workflow_definition()
        validate_workflow_definition(d, workflow_category=CATEGORY_GENERAL)

    def test_default_has_meta_category(self):
        d = default_workflow_definition("knowledge")
        self.assertEqual(d["meta"]["category"], "knowledge")
        validate_workflow_definition(d, workflow_category="knowledge")

    def test_rejects_bad_schema_version(self):
        d = default_workflow_definition()
        d["schemaVersion"] = 99
        with self.assertRaises(DefinitionValidationError):
            validate_workflow_definition(d, workflow_category=CATEGORY_GENERAL)

    def test_rejects_unknown_node_type(self):
        d = default_workflow_definition()
        d["nodes"][0]["type"] = "unknown"
        with self.assertRaises(DefinitionValidationError):
            validate_workflow_definition(d, workflow_category=CATEGORY_GENERAL)

    def test_rejects_bad_meta_category(self):
        d = default_workflow_definition()
        d["meta"] = {"category": "not-a-category"}
        with self.assertRaises(DefinitionValidationError):
            validate_workflow_definition(d, workflow_category=CATEGORY_GENERAL)

    def test_normalize_sets_category_from_workflow(self):
        d = default_workflow_definition("automation")
        d["meta"]["category"] = "knowledge"
        out = normalize_definition(d, workflow_category=CATEGORY_AUTOMATION)
        self.assertEqual(out["meta"]["category"], CATEGORY_AUTOMATION)


class ReactFlowSanitizeTests(SimpleTestCase):
    def test_sanitize_clamps_non_positive_zoom(self):
        raw = default_workflow_definition()
        raw["viewport"]["zoom"] = 0
        out = sanitize_react_flow_definition(raw)
        self.assertEqual(out["viewport"]["zoom"], 1.0)

    def test_sanitize_assigns_edge_ids(self):
        raw = default_workflow_definition()
        raw["edges"] = [{"source": "start-1", "target": "start-1"}]
        out = sanitize_react_flow_definition(raw)
        self.assertEqual(len(out["edges"]), 1)
        self.assertTrue(out["edges"][0]["id"])


class UpgradeV1ToV2Tests(SimpleTestCase):
    def test_upgrade_assigns_positions_and_schema_two(self):
        v1 = {
            "schemaVersion": 1,
            "meta": {"category": "general"},
            "nodes": [
                {"id": "n1", "type": "step", "data": {"title": "A"}},
                {"id": "n2", "type": "step", "data": {}},
            ],
            "edges": [{"source": "n1", "target": "n2"}],
            "viewport": {"x": 0, "y": 0, "zoom": 1},
        }
        v2 = upgrade_v1_document_to_v2(v1)
        self.assertEqual(v2["schemaVersion"], 2)
        self.assertEqual(len(v2["nodes"]), 2)
        for n in v2["nodes"]:
            self.assertIn("position", n)
            self.assertIn("x", n["position"])
        self.assertEqual(len(v2["edges"]), 1)
        self.assertIsInstance(v2["edges"][0].get("id"), str)
        validate_workflow_definition(v2, workflow_category=CATEGORY_GENERAL)

    def test_non_v1_unchanged(self):
        d = default_workflow_definition()
        self.assertIs(upgrade_v1_document_to_v2(d), d)


class WorkflowCategoryPrimaryNodeTests(SimpleTestCase):
    def test_primary_node_defaults_to_step(self):
        self.assertEqual(primary_node_type_for_category(CATEGORY_PROCEDURE), "step")
        self.assertEqual(primary_node_type_for_category(CATEGORY_AUTOMATION), "step")


class WorkflowUrlTests(SimpleTestCase):
    def test_named_routes_resolve(self):
        self.assertEqual(reverse("dashboard:workflows:list"), "/dashboard/workflows/")
        self.assertEqual(reverse("dashboard:workflows:create"), "/dashboard/workflows/new/")
        pk = "00000000-0000-4000-8000-000000000001"
        self.assertEqual(
            reverse("dashboard:workflows:editor", kwargs={"pk": pk}),
            f"/dashboard/workflows/{pk}/edit/",
        )
        self.assertEqual(
            reverse("dashboard:workflows_api:definition", kwargs={"pk": pk}),
            f"/dashboard/workflows/api/{pk}/definition/",
        )
        self.assertEqual(
            reverse("dashboard:workflows_api:node_links", kwargs={"pk": pk}),
            f"/dashboard/workflows/api/{pk}/links/",
        )
        link_id = "00000000-0000-4000-8000-000000000002"
        self.assertEqual(
            reverse(
                "dashboard:workflows_api:node_link_detail",
                kwargs={"pk": pk, "link_id": link_id},
            ),
            f"/dashboard/workflows/api/{pk}/links/{link_id}/",
        )

    def test_invalid_uuid_does_not_reverse_editor(self):
        with self.assertRaises(NoReverseMatch):
            reverse("dashboard:workflows:editor", kwargs={"pk": "not-a-uuid"})
