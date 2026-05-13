"""Import a bank statement document into BankStatement + BankStatementLine rows."""
from __future__ import annotations

import logging
from decimal import Decimal
from typing import Iterable, Optional

from django.db import transaction as db_transaction

from apps.documents.models import DocumentFile
from apps.documents.parsers.bank_statement import BankStatementParser
from apps.documents.storage import document_absolute_path
from apps.money.models import Account, BankStatement, BankStatementLine

logger = logging.getLogger(__name__)


@db_transaction.atomic
def import_bank_statement(
    *,
    account: Account,
    document: Optional[DocumentFile] = None,
    file_path: Optional[str] = None,
    raw_text: Optional[str] = None,
) -> BankStatement:
    """Parse a bank statement source (file path, document, or raw text) and persist it.

    Exactly one of `document`/`file_path`/`raw_text` should be provided.
    """
    parser = BankStatementParser()
    if raw_text is not None:
        parsed = parser.parse_text(raw_text)
    elif file_path is not None:
        parsed = parser.parse(file_path)
    elif document is not None:
        parsed = parser.parse(document_absolute_path(document))
    else:
        raise ValueError("Provide one of: document, file_path, raw_text")

    if not parsed.get("success"):
        statement = BankStatement.objects.create(
            account=account,
            document=document,
            period_start=parsed.get("period_start") or _today(),
            period_end=parsed.get("period_end") or _today(),
            opening_balance=Decimal(parsed.get("opening_balance") or 0),
            closing_balance=Decimal(parsed.get("closing_balance") or 0),
            raw_text=parsed.get("raw_text", "") or "",
            parse_status=BankStatement.PARSE_ERROR,
            parse_error=parsed.get("error", "Unknown parse error"),
        )
        logger.warning("Bank statement parse error: %s", parsed.get("error"))
        return statement

    statement = BankStatement.objects.create(
        account=account,
        document=document,
        period_start=parsed["period_start"],
        period_end=parsed["period_end"],
        opening_balance=Decimal(parsed["opening_balance"]),
        closing_balance=Decimal(parsed["closing_balance"]),
        raw_text=parsed.get("raw_text", "") or "",
        parse_status=BankStatement.PARSE_PARSED,
    )
    _persist_lines(statement, parsed.get("lines") or [])
    return statement


def _persist_lines(statement: BankStatement, lines: Iterable[dict]) -> None:
    bulk = []
    for raw in lines:
        try:
            bulk.append(
                BankStatementLine(
                    statement=statement,
                    date=raw["date"],
                    direction=raw["direction"],
                    amount=Decimal(raw["amount"]),
                    description=raw.get("description", "") or "",
                    bank_reference=raw.get("bank_reference", "") or "",
                )
            )
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning("Skipping malformed bank statement line %r: %s", raw, exc)
    if bulk:
        BankStatementLine.objects.bulk_create(bulk)


def _today():
    from django.utils import timezone

    return timezone.localdate()
