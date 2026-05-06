from django.urls import path

from apps.accounting import views

app_name = "accounting"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    # Setup wizard
    path("setup/", views.setup_intro, name="setup_intro"),
    path("setup/currency/", views.setup_currency, name="setup_currency"),
    path("setup/accounts/", views.setup_accounts, name="setup_accounts"),
    path("setup/review/", views.setup_review, name="setup_review"),
    # Period browsing
    path("periods/", views.period_list, name="period_list"),
    path(
        "periods/<int:year>-<int:month>/",
        views.period_detail,
        name="period_detail",
    ),
    path(
        "periods/<int:year>-<int:month>/daybook/",
        views.period_daybook,
        name="period_daybook",
    ),
    path(
        "periods/<int:year>-<int:month>/income/",
        views.period_income_statement,
        name="period_income_statement",
    ),
    path(
        "periods/<int:year>-<int:month>/balance/",
        views.period_balance,
        name="period_balance",
    ),
    path(
        "periods/<int:year>-<int:month>/balance/<int:account_id>/",
        views.set_ending_balance,
        name="set_ending_balance",
    ),
    path(
        "periods/<int:year>-<int:month>/close/",
        views.close_period_view,
        name="close_period",
    ),
    path(
        "periods/<int:year>-<int:month>/reopen/",
        views.reopen_period_view,
        name="reopen_period",
    ),
    path(
        "periods/<int:year>-<int:month>/export.xlsx",
        views.export_period,
        name="export_period",
    ),
    # Filterable Daybook (cross-period)
    path("daybook/", views.daybook, name="daybook"),
    # Imports
    path(
        "imports/bank-statement/",
        views.import_bank_statement_view,
        name="import_bank_statement",
    ),
]
