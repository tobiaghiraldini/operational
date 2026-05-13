from django.db import migrations, models


def set_credit_card_defer(apps, schema_editor):
    PaymentMethod = apps.get_model("vendors", "PaymentMethod")
    PaymentMethod.objects.filter(code="credit_card").update(defer_bank_transaction=True)


def noop_reverse(apps, schema_editor):
    PaymentMethod = apps.get_model("vendors", "PaymentMethod")
    PaymentMethod.objects.filter(code="credit_card").update(defer_bank_transaction=False)


class Migration(migrations.Migration):

    dependencies = [
        ("vendors", "0003_alter_paymentmethod_code"),
    ]

    operations = [
        migrations.AddField(
            model_name="paymentmethod",
            name="defer_bank_transaction",
            field=models.BooleanField(
                default=False,
                help_text="When true, automatic invoice payment posting skips creating a bank transaction until the statement line is booked (e.g. credit card batch settlement).",
            ),
        ),
        migrations.RunPython(set_credit_card_defer, noop_reverse),
    ]
