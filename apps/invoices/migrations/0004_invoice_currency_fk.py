# Generated manually for Invoice.currency -> ForeignKey(money.Currency)

import django.db.models.deletion
from django.db import migrations, models


def forwards_currency(apps, schema_editor):
    Invoice = apps.get_model("invoices", "Invoice")
    Currency = apps.get_model("money", "Currency")
    db_alias = schema_editor.connection.alias

    eur = Currency.objects.using(db_alias).filter(code="EUR").first()
    if eur is None:
        eur = Currency.objects.using(db_alias).create(
            code="EUR",
            name="Euro",
            symbol="€",
            decimal_places=2,
            is_active=True,
        )

    for inv in Invoice.objects.using(db_alias).iterator():
        raw = inv.currency
        code = str(raw or "EUR").strip().upper()[:3]
        if len(code) != 3:
            code = "EUR"
        cu = Currency.objects.using(db_alias).filter(code=code).first()
        if cu is None:
            cu = eur
        inv.currency_new_id = cu.pk
        inv.save(update_fields=["currency_new_id"])


def backwards_noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("money", "0001_initial"),
        ("invoices", "0003_alter_invoice_file_path_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="invoice",
            name="currency_new",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="+",
                to="money.currency",
            ),
        ),
        migrations.RunPython(forwards_currency, backwards_noop),
        migrations.RemoveField(
            model_name="invoice",
            name="currency",
        ),
        migrations.RenameField(
            model_name="invoice",
            old_name="currency_new",
            new_name="currency",
        ),
        migrations.AlterField(
            model_name="invoice",
            name="currency",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="invoices",
                to="money.currency",
                help_text="Invoice currency (ISO 4217 row in money.Currency).",
            ),
        ),
    ]
