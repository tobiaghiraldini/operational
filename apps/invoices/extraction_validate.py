"""Normalize LLM invoice JSON, cross-field checks, and manual-review rules."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

EXTRACTION_PROMPT_VERSION = "invoice_extraction_v2"
REVIEW_CONFIDENCE_THRESHOLD = 0.75


class InvoiceExtractionShape(BaseModel):
    """Subset of fields we coerce; unknown keys are preserved via ``extra``."""

    model_config = ConfigDict(extra="allow")

    invoice_number: str = ""
    invoice_date: str | None = None
    due_date: str | None = None
    total_amount: Any = None
    currency: str = "EUR"
    vendor_name: str = ""
    issuer_name: str | None = None
    receiver_name: str | None = None
    vendor_vat_id: str | None = None
    customer_name: str | None = None
    vendor_address: str | None = None
    payment_method: str | None = None
    vat_percentage: Any = None
    vat_amount: Any = None
    taxable_amount: Any = None
    invoice_type: str | None = None
    document_kind: str | None = None
    payment_date: str | None = None
    paid_in_full: bool | None = None
    is_paid: bool | None = None
    field_confidence: dict[str, float] = Field(default_factory=dict)

    @field_validator("field_confidence", mode="before")
    @classmethod
    def coerce_field_confidence(cls, v: Any) -> dict[str, float]:
        if not isinstance(v, dict):
            return {}
        out: dict[str, float] = {}
        for key, val in v.items():
            try:
                out[str(key)] = float(val)
            except (TypeError, ValueError):
                continue
        return out


def normalize_and_validate_extraction(
    raw: dict[str, Any] | None,
) -> tuple[dict[str, Any], list[str], dict[str, float]]:
    """Return merged payload, validation notes, and per-field confidence scores."""
    if not isinstance(raw, dict):
        return {}, ["invalid_or_empty_payload"], {}

    try:
        parsed = InvoiceExtractionShape.model_validate(raw)
    except Exception as exc:  # noqa: BLE001
        merged = dict(raw)
        return merged, [f"schema: {exc}"], _coerce_conf_map(raw.get("field_confidence"))

    out = dict(raw)
    for name in InvoiceExtractionShape.model_fields:
        out[name] = getattr(parsed, name)
    extra = getattr(parsed, "model_extra", None) or {}
    out.update(extra)

    field_confidence = out.get("field_confidence") or {}
    if not isinstance(field_confidence, dict):
        field_confidence = {}

    notes: list[str] = []
    try:
        total = Decimal(str(out.get("total_amount") or 0))
        vat = Decimal(str(out.get("vat_amount") or 0))
        net = Decimal(str(out.get("taxable_amount") or 0))
        if net > 0 and vat >= 0 and total > 0:
            if abs(net + vat - total) > Decimal("0.02"):
                notes.append("net_plus_vat_differs_from_total")
    except (InvalidOperation, TypeError, ValueError):
        notes.append("amount_cross_check_skipped")

    out["field_confidence"] = field_confidence
    return out, notes, field_confidence


def _coerce_conf_map(raw: Any) -> dict[str, float]:
    if not isinstance(raw, dict):
        return {}
    out: dict[str, float] = {}
    for key, val in raw.items():
        try:
            out[str(key)] = float(val)
        except (TypeError, ValueError):
            continue
    return out


def extraction_requires_manual_review(
    base_flag: bool,
    field_confidence: dict[str, float],
    validation_notes: list[str],
) -> bool:
    if base_flag:
        return True
    if validation_notes:
        return True
    scores = [v for v in field_confidence.values() if isinstance(v, (int, float))]
    if not scores:
        return False
    avg = sum(scores) / len(scores)
    return avg < REVIEW_CONFIDENCE_THRESHOLD
