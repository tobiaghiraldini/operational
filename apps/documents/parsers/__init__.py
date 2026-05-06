"""Generic document parsers exposed by the documents app.

The base interface is `BaseDocumentParser`; specialized parsers (invoice,
bank statement, etc.) live in sibling modules and call into `apps.documents.ocr`
for raw text extraction.
"""
from .base import BaseDocumentParser

__all__ = ["BaseDocumentParser"]
