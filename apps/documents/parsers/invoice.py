"""Invoice parser wrapping the existing OCR + regex extraction.

The actual extraction logic lives in :mod:`apps.documents.ocr` and
:mod:`apps.documents.parser`; this module exposes them under a uniform
:class:`BaseDocumentParser` interface so accounting/invoices code can swap
parsers without depending on internals.
"""
from __future__ import annotations

from typing import Any

from apps.documents.ocr import OCRProcessor
from apps.documents.parser import DocumentParser

from .base import BaseDocumentParser


class InvoiceParser(BaseDocumentParser):
    name = "invoice"

    def __init__(self) -> None:
        self.ocr = OCRProcessor()
        self.parser = DocumentParser()

    def parse(self, file_path: str) -> dict[str, Any]:
        ocr_result = self.ocr.process_file(file_path)
        if not ocr_result.get("success"):
            return {
                "success": False,
                "error": ocr_result.get("error") or "OCR failed",
                "raw_text": "",
            }
        text = ocr_result.get("text", "") or ""
        data = self.parser.parse_invoice_data(text)
        validation = self.parser.validate_invoice_data(data)
        return {
            "success": True,
            "error": None,
            "raw_text": text,
            "data": data,
            "validation": validation,
            "method": ocr_result.get("method"),
        }

    def parse_text(self, raw_text: str) -> dict[str, Any]:
        data = self.parser.parse_invoice_data(raw_text)
        validation = self.parser.validate_invoice_data(data)
        return {
            "success": True,
            "error": None,
            "raw_text": raw_text,
            "data": data,
            "validation": validation,
        }
