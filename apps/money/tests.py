"""Tests for invoice settlement allocations and credit-card deferral."""
from __future__ import annotations

import datetime as dt
from decimal import Decimal

from django.forms.models import inlineformset_factory
from django_tenants.test.cases import FastTenantTestCase

from apps.accounting.services.period import get_or_create_period
from apps.accounting.services.period_feed import build_period_feed
from apps.invoices.models import Invoice
from apps.invoices.payment_transaction import sync_invoice_payment_transaction
from apps.money.forms.invoice_settlement_allocation_admin import (
    InvoiceSettlementAllocationAdminForm,
)
from apps.money.forms.transaction_settlement_allocation_formset import (
    TransactionSettlementAllocationFormSet,
)
from apps.money.models import (
    Account,
    Currency,
    ExchangeRate,
    InvoiceSettlementAllocation,
    Transaction,
)
from apps.money.services.invoice_document_label import transaction_invoice_document_label
from apps.vendors.models import PaymentMethod


class InvoiceSettlementTests(FastTenantTestCase):
    @classmethod
    def setup_tenant(cls, tenant):
        from apps.users.models import TenantUser

        owner, _ = TenantUser.objects.get_or_create(
            email="money-settlement-test@example.com",
            defaults={"is_active": True},
        )
        tenant.name = "Money Settlement Test"
        tenant.slug = "money-settlement-test"
        tenant.owner = owner

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._eur = Currency.objects.get(code="EUR")

    def setUp(self):
        super().setUp()
        InvoiceSettlementAllocation.objects.all().delete()
        Transaction.objects.all().delete()
        Invoice.objects.all().delete()
        ExchangeRate.objects.all().delete()
        Account.objects.all().delete()

        self.account = Account.objects.create(
            name="Main bank",
            kind=Account.KIND_BANK,
            currency=self._eur,
            opening_balance=Decimal("1000.00"),
            opening_date=dt.date(2026, 4, 30),
            is_default=True,
        )
        self.pm_card, _ = PaymentMethod.objects.update_or_create(
            code="credit_card",
            defaults={
                "name": "Credit Card",
                "defer_bank_transaction": True,
            },
        )
        self.pm_bank, _ = PaymentMethod.objects.update_or_create(
            code="bank_transfer",
            defaults={
                "name": "Bank Transfer",
                "defer_bank_transaction": False,
            },
        )

    def _invoice(self, *, number: str, amount: str, day: int = 4) -> Invoice:
        return Invoice.objects.create(
            invoice_number=number,
            invoice_date=dt.date(2026, 5, day),
            due_date=dt.date(2026, 5, 30),
            total_amount=Decimal(amount),
            currency=self._eur,
            original_filename=f"{number}.pdf",
            file_path=f"invoices/{number}.pdf",
        )

    def test_payments_total_sums_amount_invoice(self):
        inv = self._invoice(number="M-1", amount="100")
        tx = Transaction.objects.create(
            date=dt.date(2026, 5, 10),
            direction=Transaction.DIRECTION_OUT,
            amount=Decimal("40"),
            currency=self._eur,
            account=self.account,
        )
        InvoiceSettlementAllocation.objects.create(
            transaction=tx,
            invoice=inv,
            amount_settlement=Decimal("40"),
            amount_invoice=Decimal("40"),
        )
        self.assertEqual(inv.payments_total, Decimal("40"))

    def test_sync_skips_transaction_when_payment_method_defers_bank(self):
        inv = self._invoice(number="CARD-1", amount="50")
        inv.payment_method = self.pm_card
        inv.payment_date = dt.date(2026, 5, 5)
        inv.save(update_fields=["payment_method", "payment_date", "updated_at"])

        result = sync_invoice_payment_transaction(inv)
        self.assertIsNone(result)
        self.assertEqual(inv.settlement_allocations.count(), 0)

    def test_period_feed_fee_only_allocation_does_not_mark_invoice_paid(self):
        """Fee rows have no invoice_id; they must not pollute paid_invoice_ids."""
        period = get_or_create_period(2026, 5)
        inv = self._invoice(number="FEE-ONLY", amount="100", day=4)
        tx = Transaction.objects.create(
            date=dt.date(2026, 5, 15),
            direction=Transaction.DIRECTION_OUT,
            amount=Decimal("100"),
            currency=self._eur,
            account=self.account,
        )
        InvoiceSettlementAllocation.objects.create(
            transaction=tx,
            invoice=None,
            amount_settlement=Decimal("100"),
            amount_invoice=None,
        )

        feed = build_period_feed(period)
        self.assertEqual(feed.totals["unpaid_invoice_count"], Decimal("1"))
        doc_nos = [e["doc_no"] for e in feed.entries if e["kind"] == "invoice"]
        self.assertIn(inv.invoice_number, doc_nos)

    def test_period_feed_excludes_two_invoices_settled_by_one_transaction(self):
        period = get_or_create_period(2026, 5)
        inv1 = self._invoice(number="A", amount="500", day=4)
        inv2 = self._invoice(number="B", amount="400", day=6)
        tx = Transaction.objects.create(
            date=dt.date(2026, 5, 15),
            direction=Transaction.DIRECTION_OUT,
            amount=Decimal("900"),
            currency=self._eur,
            account=self.account,
            reference="CARD-STMT-05",
        )
        InvoiceSettlementAllocation.objects.create(
            transaction=tx,
            invoice=inv1,
            amount_settlement=Decimal("500"),
            amount_invoice=Decimal("500"),
        )
        InvoiceSettlementAllocation.objects.create(
            transaction=tx,
            invoice=inv2,
            amount_settlement=Decimal("400"),
            amount_invoice=Decimal("400"),
        )

        feed = build_period_feed(period)
        self.assertEqual(feed.totals["unpaid_invoice_count"], Decimal("0"))
        tx_entries = [e for e in feed.entries if e["kind"] == "transaction"]
        self.assertEqual(len(tx_entries), 1)
        self.assertEqual(tx_entries[0]["doc_no"], "CARD-STMT-05")

    def test_transaction_invoice_document_label_composite(self):
        inv1 = self._invoice(number="I-1", amount="10", day=1)
        inv2 = self._invoice(number="I-2", amount="20", day=2)
        tx = Transaction.objects.create(
            date=dt.date(2026, 5, 20),
            direction=Transaction.DIRECTION_OUT,
            amount=Decimal("30"),
            currency=self._eur,
            account=self.account,
        )
        InvoiceSettlementAllocation.objects.create(
            transaction=tx,
            invoice=inv1,
            amount_settlement=Decimal("10"),
            amount_invoice=Decimal("10"),
        )
        InvoiceSettlementAllocation.objects.create(
            transaction=tx,
            invoice=inv2,
            amount_settlement=Decimal("20"),
            amount_invoice=Decimal("20"),
        )
        self.assertEqual(transaction_invoice_document_label(tx), "I-1 +1")

    def test_settlement_admin_form_defaults_blank_amounts_same_currency(self):
        inv = self._invoice(number="AUTO-1", amount="100.00")
        tx = Transaction.objects.create(
            date=dt.date(2026, 5, 1),
            direction=Transaction.DIRECTION_OUT,
            amount=Decimal("100.00"),
            currency=self._eur,
            account=self.account,
        )
        form = InvoiceSettlementAllocationAdminForm(
            data={
                "invoice": inv.pk,
                "transaction": tx.pk,
                "amount_invoice": "",
                "amount_settlement": "",
            }
        )
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data["amount_invoice"], Decimal("100.00"))
        self.assertEqual(form.cleaned_data["amount_settlement"], Decimal("100.00"))

    def test_settlement_admin_form_defaults_cross_currency_prefers_exchange_rate(self):
        usd, _ = Currency.objects.get_or_create(
            code="USD", defaults={"name": "US Dollar", "symbol": "$"}
        )
        ExchangeRate.objects.create(
            from_currency=usd,
            to_currency=self._eur,
            rate=Decimal("0.92"),
            valid_from=dt.date(2026, 1, 1),
            source=ExchangeRate.SOURCE_MANUAL,
        )
        inv = self._invoice(number="AUTO-2", amount="10.00")
        inv.currency = usd
        inv.converted_amount = Decimal("99.99")
        inv.save(update_fields=["currency", "converted_amount", "updated_at"])
        tx = Transaction.objects.create(
            date=dt.date(2026, 5, 1),
            direction=Transaction.DIRECTION_OUT,
            amount=Decimal("29.06"),
            currency=self._eur,
            account=self.account,
        )
        form = InvoiceSettlementAllocationAdminForm(
            data={
                "invoice": inv.pk,
                "transaction": tx.pk,
                "amount_invoice": "",
                "amount_settlement": "",
            }
        )
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data["amount_invoice"], Decimal("10.00"))
        self.assertEqual(form.cleaned_data["amount_settlement"], Decimal("9.20"))

    def test_settlement_admin_form_defaults_cross_currency_fallback_to_converted(self):
        usd, _ = Currency.objects.get_or_create(
            code="USD", defaults={"name": "US Dollar", "symbol": "$"}
        )
        inv = self._invoice(number="AUTO-3", amount="10.00")
        inv.currency = usd
        inv.converted_amount = Decimal("9.20")
        inv.save(update_fields=["currency", "converted_amount", "updated_at"])
        tx = Transaction.objects.create(
            date=dt.date(2026, 5, 1),
            direction=Transaction.DIRECTION_OUT,
            amount=Decimal("29.06"),
            currency=self._eur,
            account=self.account,
        )
        form = InvoiceSettlementAllocationAdminForm(
            data={
                "invoice": inv.pk,
                "transaction": tx.pk,
                "amount_invoice": "",
                "amount_settlement": "",
            }
        )
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data["amount_invoice"], Decimal("10.00"))
        self.assertEqual(form.cleaned_data["amount_settlement"], Decimal("9.20"))

    def test_transaction_settlement_formset_fills_single_fee_remainder(self):
        tx = Transaction.objects.create(
            date=dt.date(2026, 5, 1),
            direction=Transaction.DIRECTION_OUT,
            amount=Decimal("103.00"),
            currency=self._eur,
            account=self.account,
        )
        inv = self._invoice(number="LINE", amount="100.00")
        FS = inlineformset_factory(
            Transaction,
            InvoiceSettlementAllocation,
            form=InvoiceSettlementAllocationAdminForm,
            formset=TransactionSettlementAllocationFormSet,
            extra=2,
            validate_min=False,
        )
        prefix = "alloc"
        data = {
            f"{prefix}-TOTAL_FORMS": "2",
            f"{prefix}-INITIAL_FORMS": "0",
            f"{prefix}-MIN_NUM_FORMS": "0",
            f"{prefix}-MAX_NUM_FORMS": "1000",
            f"{prefix}-0-transaction": str(tx.pk),
            f"{prefix}-0-invoice": str(inv.pk),
            f"{prefix}-0-amount_invoice": "",
            f"{prefix}-0-amount_settlement": "",
            f"{prefix}-0-fx_rate": "",
            f"{prefix}-0-notes": "",
            f"{prefix}-0-DELETE": "",
            f"{prefix}-1-transaction": str(tx.pk),
            f"{prefix}-1-invoice": "",
            f"{prefix}-1-amount_invoice": "",
            f"{prefix}-1-amount_settlement": "",
            f"{prefix}-1-fx_rate": "",
            f"{prefix}-1-notes": "",
            f"{prefix}-1-DELETE": "",
        }
        formset = FS(data=data, instance=tx, prefix=prefix)
        self.assertTrue(formset.is_valid(), formset.errors)
        self.assertEqual(
            formset.forms[0].cleaned_data["amount_settlement"], Decimal("100.00")
        )
        self.assertEqual(formset.forms[1].cleaned_data["amount_settlement"], Decimal("3.00"))
        self.assertIsNone(formset.forms[1].cleaned_data["invoice"])

    def test_settlement_allocation_gap_ignores_unallocated_portion(self):
        tx = Transaction.objects.create(
            date=dt.date(2026, 5, 1),
            direction=Transaction.DIRECTION_OUT,
            amount=Decimal("1000"),
            currency=self._eur,
            account=self.account,
        )
        inv = self._invoice(number="GAP", amount="1000", day=1)
        InvoiceSettlementAllocation.objects.create(
            transaction=tx,
            invoice=inv,
            amount_settlement=Decimal("990"),
            amount_invoice=Decimal("990"),
        )
        self.assertEqual(tx.settlement_allocation_gap(), Decimal("10"))
