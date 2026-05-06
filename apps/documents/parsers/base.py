"""Abstract base class for document parsers."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class BaseDocumentParser(ABC):
    """Uniform interface for document parsers.

    Subclasses implement `parse(file_path)` and return a dict with at least
    `success: bool`, `error: str | None`, and parser-specific result keys.
    """

    name: str = "base"

    @abstractmethod
    def parse(self, file_path: str) -> dict[str, Any]:
        """Parse a document at `file_path`. Must always return a dict."""

    def parse_text(self, raw_text: str) -> dict[str, Any]:
        """Optional shortcut for parsers that can operate on a pre-extracted text."""
        raise NotImplementedError(
            f"{self.__class__.__name__}.parse_text is not implemented"
        )
