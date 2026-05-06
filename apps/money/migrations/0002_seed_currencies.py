"""Seed the standard set of currencies used by the accounting MVP.

Runs as part of `migrate_schemas` for every existing and future tenant
because `apps.money` is in `TENANT_APPS`. Idempotent via `update_or_create`.
"""
from django.db import migrations


SEED_CURRENCIES = [
    {"code": "EUR", "name": "Euro", "symbol": "\u20ac", "decimal_places": 2},
    {"code": "USD", "name": "US Dollar", "symbol": "$", "decimal_places": 2},
    {"code": "GBP", "name": "Pound Sterling", "symbol": "\u00a3", "decimal_places": 2},
]


def seed_currencies(apps, schema_editor):
    Currency = apps.get_model("money", "Currency")
    for entry in SEED_CURRENCIES:
        Currency.objects.update_or_create(
            code=entry["code"],
            defaults={
                "name": entry["name"],
                "symbol": entry["symbol"],
                "decimal_places": entry["decimal_places"],
                "is_active": True,
            },
        )


def unseed_currencies(apps, schema_editor):
    Currency = apps.get_model("money", "Currency")
    Currency.objects.filter(code__in=[c["code"] for c in SEED_CURRENCIES]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("money", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed_currencies, unseed_currencies),
    ]
