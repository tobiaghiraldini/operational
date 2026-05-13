"""Default `DocumentFolder` for invoice PDFs arriving via upload (not folder scan)."""

from apps.documents.folder_paths import get_invoice_folder_for_invoice_type


def get_invoice_inbox_folder():
    """Legacy name: default folder for browser/API uploads (received invoices)."""
    folder, _created = get_invoice_folder_for_invoice_type(None)
    return folder, _created
