"""Bank statement parser.

Strategy:
1. Run OCR on the source PDF (`apps.documents.ocr.OCRProcessor`).
2. Walk the text line-by-line with regex heuristics common to Italian bank
   layouts (Intesa, UniCredit, BPER, ...) to extract:
   - the statement period
   - opening and closing balances
   - one transaction per line (date / direction / amount / description)
3. If the regex pass produces too little data the caller can retry with a
   richer extractor (LLM via `apps.ai`) -- not wired in by default to keep
   the MVP self-contained.

The output dict shape:

```
{
    "success": bool,
    "error": str | None,
    "raw_text": str,
    "period_start": date | None,
    "period_end": date | None,
    "opening_balance": Decimal | None,
    "closing_balance": Decimal | None,
    "lines": [
        {"date": date, "direction": "in"|"out", "amount": Decimal,
         "description": str, "bank_reference": str},
        ...
    ],
}
```
"""
from __future__ import annotations

import logging
import re
from datetime import date as date_cls, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from apps.documents.ocr import OCRProcessor

from .base import BaseDocumentParser

logger = logging.getLogger(__name__)

DATE_RE = re.compile(r"\b(\d{2})[/\-](\d{2})[/\-](\d{2,4})\b")
AMOUNT_RE = re.compile(r"([+-]?)\s*(\d{1,3}(?:[.,]\d{3})*[.,]\d{2})")
PERIOD_RE = re.compile(
    r"(?:dal|from)\s+(\d{2}[/\-]\d{2}[/\-]\d{2,4})\s+(?:al|to)\s+(\d{2}[/\-]\d{2}[/\-]\d{2,4})",
    re.IGNORECASE,
)
OPENING_RE = re.compile(
    r"(?:saldo\s+iniziale|opening\s+balance)[^\d\-+]*([+-]?\s*\d{1,3}(?:[.,]\d{3})*[.,]\d{2})",
    re.IGNORECASE,
)
CLOSING_RE = re.compile(
    r"(?:saldo\s+finale|closing\s+balance)[^\d\-+]*([+-]?\s*\d{1,3}(?:[.,]\d{3})*[.,]\d{2})",
    re.IGNORECASE,
)


class BankStatementParser(BaseDocumentParser):
    name = "bank_statement"

    def __init__(self) -> None:
        self.ocr = OCRProcessor()

    def parse(self, file_path: str) -> dict[str, Any]:
        ocr_result = self.ocr.process_file(file_path)
        if not ocr_result.get("success"):
            return {
                "success": False,
                "error": ocr_result.get("error") or "OCR failed",
                "raw_text": "",
            }
        return self.parse_text(ocr_result.get("text", "") or "")

    def parse_text(self, raw_text: str) -> dict[str, Any]:
        period_start, period_end = self._extract_period(raw_text)
        opening = self._extract_balance(OPENING_RE, raw_text)
        closing = self._extract_balance(CLOSING_RE, raw_text)
        lines = self._extract_lines(raw_text)

        success = bool(lines) and period_start is not None and period_end is not None
        return {
            "success": success,
            "error": None if success else "Could not extract a coherent statement",
            "raw_text": raw_text,
            "period_start": period_start,
            "period_end": period_end,
            "opening_balance": opening,
            "closing_balance": closing,
            "lines": lines,
        }

    def _extract_period(self, text: str) -> tuple[date_cls | None, date_cls | None]:
        match = PERIOD_RE.search(text)
        if not match:
            return None, None
        return _parse_date(match.group(1)), _parse_date(match.group(2))

    def _extract_balance(self, pattern: re.Pattern, text: str) -> Decimal | None:
        match = pattern.search(text)
        if not match:
            return None
        return _parse_amount(match.group(1))

    def _extract_lines(self, text: str) -> list[dict]:
        lines: list[dict] = []
        for raw in text.splitlines():
            stripped = raw.strip()
            if not stripped:
                continue
            date_match = DATE_RE.search(stripped)
            if not date_match:
                continue
            line_date = _parse_date(date_match.group(0))
            if not line_date:
                continue

            amounts = AMOUNT_RE.findall(stripped)
            if not amounts:
                continue
            sign, amount_text = amounts[-1]
            amount = _parse_amount(amount_text)
            if amount is None or amount == 0:
                continue

            direction = "out" if sign == "-" or _looks_like_outflow(stripped) else "in"
            description = _strip_to_description(
                stripped, date_match.group(0), amount_text
            )
            lines.append(
                {
                    "date": line_date,
                    "direction": direction,
                    "amount": abs(amount),
                    "description": description,
                    "bank_reference": "",
                }
            )
        return lines


def _parse_date(value: str) -> date_cls | None:
    if not value:
        return None
    for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%d/%m/%y", "%d-%m-%y"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    return None


def _parse_amount(value: str) -> Decimal | None:
    if not value:
        return None
    cleaned = value.replace(" ", "").replace("\u00a0", "")
    sign = ""
    if cleaned.startswith(("+", "-")):
        sign, cleaned = cleaned[0], cleaned[1:]
    if "," in cleaned and "." in cleaned:
        if cleaned.rfind(",") > cleaned.rfind("."):
            cleaned = cleaned.replace(".", "").replace(",", ".")
        else:
            cleaned = cleaned.replace(",", "")
    elif "," in cleaned:
        cleaned = cleaned.replace(".", "").replace(",", ".")
    try:
        return Decimal(sign + cleaned)
    except InvalidOperation:
        return None


_OUTFLOW_HINTS = ("addebito", "uscita", "pagamento", "prelievo", "bonifico uscente")


def _looks_like_outflow(text: str) -> bool:
    lower = text.lower()
    return any(hint in lower for hint in _OUTFLOW_HINTS)


def _strip_to_description(stripped: str, date_token: str, amount_token: str) -> str:
    description = stripped.replace(date_token, "", 1)
    description = description.replace(amount_token, "", 1)
    description = re.sub(r"\s+", " ", description).strip(" -|\t")
    return description
