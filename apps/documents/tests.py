"""Tests for document storage paths and ``DocumentFile`` metadata."""

from __future__ import annotations

import os
import shutil
import tempfile

from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase, override_settings
from django_tenants.test.cases import FastTenantTestCase

from apps.documents.folder_paths import (
    INVOICES_RECEIVED,
    normalize_folder_path_for_storage,
    sanitize_upload_filename,
)
from apps.documents.forms import DocumentFileAdminForm
from apps.documents.models import DocumentFile, DocumentFolder
from apps.documents.storage import document_absolute_path, document_upload_to


class FolderPathsHelpersTests(SimpleTestCase):
    def test_sanitize_strips_path_segments(self):
        self.assertEqual(sanitize_upload_filename("../../x.pdf"), "x.pdf")

    def test_sanitize_replaces_unsafe_chars(self):
        s = sanitize_upload_filename("inv (copy) #1.pdf")
        self.assertTrue(s.endswith(".pdf"))
        self.assertNotIn("(", s)

    def test_normalize_folder_path_rejects_traversal(self):
        self.assertEqual(
            normalize_folder_path_for_storage("a/../../etc/passwd"),
            "a/etc/passwd",
        )

    def test_document_upload_to_prefixes_with_folder_path(self):
        folder = DocumentFolder(path="invoices/received", name="Received")
        doc = DocumentFile(folder=folder, filename="doc.pdf")
        rel = document_upload_to(doc, "weird name!.pdf")
        self.assertTrue(rel.startswith("invoices/received/"))
        self.assertIn("_", rel)
        self.assertTrue(rel.endswith(".pdf"))


@override_settings(
    MEDIA_ROOT=tempfile.mkdtemp(),
)
class DocumentAbsolutePathTests(FastTenantTestCase):
    """Resolve filesystem paths for ``FileField`` and legacy ``file_path``."""

    @classmethod
    def setup_tenant(cls, tenant):
        from apps.users.models import TenantUser

        owner, _ = TenantUser.objects.get_or_create(
            email="documents-test@example.com",
            defaults={"is_active": True},
        )
        tenant.name = "Documents Test Tenant"
        tenant.slug = "documents-test"
        tenant.owner = owner

    @classmethod
    def tearDownClass(cls):
        mr = getattr(settings, "MEDIA_ROOT", "")
        if mr and os.path.isdir(str(mr)):
            shutil.rmtree(str(mr), ignore_errors=True)
        super().tearDownClass()

    def setUp(self):
        super().setUp()
        self.folder = DocumentFolder.objects.create(path="test-fold", name="Fold")

    def test_prefers_file_field_storage(self):
        pdf = SimpleUploadedFile(
            "doc.pdf",
            b"%PDF-1.4 minimal test bytes",
            content_type="application/pdf",
        )
        doc = DocumentFile(
            folder=self.folder,
            filename="doc.pdf",
            file_path="",
            file_size=0,
            status="pending",
        )
        doc.file.save("doc.pdf", pdf, save=False)
        doc.save()
        resolved = document_absolute_path(doc)
        expected = os.path.normpath(
            os.path.join(str(settings.MEDIA_ROOT), doc.file.name.lstrip("/"))
        )
        self.assertEqual(os.path.normpath(resolved), expected)
        self.assertTrue(os.path.isfile(resolved))

    def test_legacy_media_relative_file_path(self):
        rel = "legacy/sub/hello.pdf"
        abs_expected = os.path.join(str(settings.MEDIA_ROOT), rel)
        os.makedirs(os.path.dirname(abs_expected), exist_ok=True)
        with open(abs_expected, "wb") as fh:
            fh.write(b"hello")

        doc = DocumentFile.objects.create(
            folder=self.folder,
            filename="hello.pdf",
            file_path=rel,
            file_size=5,
            status="pending",
        )
        self.assertEqual(document_absolute_path(doc), abs_expected)

    def test_recompute_file_metadata_sets_hash_and_size(self):
        pdf = SimpleUploadedFile(
            "x.pdf",
            b"%PDF-1.4 xyz",
            content_type="application/pdf",
        )
        doc = DocumentFile(
            folder=self.folder,
            filename="x.pdf",
            file_path="",
            file_size=0,
            file_hash="",
            status="pending",
        )
        doc.file.save("x.pdf", pdf, save=False)
        doc.save()
        doc.recompute_file_metadata()
        self.assertGreater(doc.file_size, 0)
        self.assertEqual(len(doc.file_hash), 64)

    def test_admin_form_sets_received_folder_and_filename_from_upload(self):
        pdf = SimpleUploadedFile(
            "My Invoice #1.pdf",
            b"%PDF-1.4 x",
            content_type="application/pdf",
        )
        form = DocumentFileAdminForm(
            data={
                "invoice_storage_kind": "received",
                "file_type": "pdf",
                "status": "pending",
            },
            files={"file": pdf},
        )
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data["folder"].path, INVOICES_RECEIVED)
        self.assertTrue(form.cleaned_data["filename"].endswith(".pdf"))
