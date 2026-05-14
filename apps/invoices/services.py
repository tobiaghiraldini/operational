"""
Services for invoice processing with company matching and validation.
"""
from datetime import date as date_cls
from decimal import Decimal
from typing import Dict, Optional, List, Tuple

from django.db import transaction as db_transaction
from thefuzz import fuzz

from apps.invoices.models import InvoiceTemplate, Invoice
from apps.organizations.models import Organization


def fuzzy_match_company(
    name: str, company_info: Optional[Organization], threshold: int = 85
) -> Tuple[bool, int]:
    """
    Perform fuzzy string matching between a name and company information.
    
    Args:
        name: Name to match against
        company_info: Organization (tenant company profile) instance
        threshold: Minimum similarity score (0-100) to consider a match
        
    Returns:
        Tuple of (is_match, similarity_score)
    """
    if not name or not company_info:
        return False, 0
    
    # Get all possible names for the company
    company_names = company_info.get_all_names()
    
    best_score = 0
    for company_name in company_names:
        if not company_name:
            continue
        
        # Use token_sort_ratio for better matching (handles word order differences)
        score = fuzz.token_sort_ratio(name.lower(), company_name.lower())
        if score > best_score:
            best_score = score
    
    is_match = best_score >= threshold
    return is_match, best_score


def match_company_entities(text: str, company_info: Optional[Organization]) -> Dict:
    """
    Extract and match company-like entities from text against company information.
    
    Args:
        text: Text to search for company entities
        company_info: Organization (tenant company profile) to match against (optional)
        
    Returns:
        Dictionary with matched entities and their positions
    """
    result = {
        'matched_entities': [],
        'potential_vendors': [],
        'user_company_found': False
    }
    
    if not company_info:
        return result
    
    # Simple extraction: look for company names, VAT IDs, addresses
    # This is a basic implementation - can be enhanced with NLP
    
    company_names = company_info.get_all_names()
    company_vat = company_info.vat_id
    
    # Check if any company name appears in text
    text_lower = text.lower()
    for name in company_names:
        if name and name.lower() in text_lower:
            result['user_company_found'] = True
            result['matched_entities'].append({
                'type': 'company_name',
                'value': name,
                'match_type': 'exact'
            })
    
    # Check VAT ID
    if company_vat and company_vat in text:
        result['user_company_found'] = True
        result['matched_entities'].append({
            'type': 'vat_id',
            'value': company_vat,
            'match_type': 'exact'
        })
    
    return result


def identify_issuer_receiver(
    extracted_data: Dict,
    company_info: Optional[Organization],
    spatial_hints: Optional[Dict] = None,
) -> Dict:
    """
    Identify invoice issuer and receiver using company information and spatial hints.
    
    Args:
        extracted_data: Data extracted from invoice (vendor_name, etc.)
        company_info: Organization (tenant company profile, optional)
        spatial_hints: Optional spatial information (top_left, top_right, etc.)
        
    Returns:
        Dictionary with issuer and receiver identification
    """
    result = {
        'issuer_name': None,
        'receiver_name': None,
        'confidence': 'low',
        'reasoning': []
    }
    
    vendor_name = extracted_data.get('vendor_name', '')
    customer_name = extracted_data.get('customer_name', '')
    
    if not company_info:
        # Without company info, assume vendor is issuer
        result['issuer_name'] = vendor_name
        result['receiver_name'] = customer_name
        result['reasoning'].append('No company information available, using default logic')
        return result
    
    # Check if vendor matches user's company
    vendor_matches, vendor_score = fuzzy_match_company(vendor_name, company_info)
    
    if vendor_matches:
        # Vendor matches user's company -> user is receiver, not issuer
        result['receiver_name'] = vendor_name
        result['issuer_name'] = customer_name or 'Unknown'
        result['confidence'] = 'high'
        result['reasoning'].append(
            f'Vendor name "{vendor_name}" matches user company (similarity: {vendor_score}%)'
        )
    else:
        # Vendor doesn't match -> vendor is issuer, user is receiver
        result['issuer_name'] = vendor_name
        result['receiver_name'] = customer_name or company_info.display_name
        result['confidence'] = 'medium'
        result['reasoning'].append(
            f'Vendor name "{vendor_name}" does not match user company (similarity: {vendor_score}%)'
        )
    
    # Use spatial hints if available
    if spatial_hints:
        top_left = spatial_hints.get('top_left', '')
        top_right = spatial_hints.get('top_right', '')
        
        # Check if company info appears in top-left (usually issuer)
        if company_info:
            for name in company_info.get_all_names():
                if name and name.lower() in top_left.lower():
                    result['reasoning'].append(
                        f'Company name found in top-left region (typically issuer position)'
                    )
                    # This might indicate user is issuer, but we prioritize vendor matching
                elif name and name.lower() in top_right.lower():
                    result['reasoning'].append(
                        f'Company name found in top-right region (typically receiver position)'
                    )
                    result['confidence'] = 'high'
    
    return result


def validate_vendor_extraction(
    vendor_name: str,
    company_info: Optional[Organization],
    threshold: int = 85,
) -> Dict:
    """
    Validate that extracted vendor is not actually the user's company.
    
    Args:
        vendor_name: Extracted vendor name
        company_info: Organization (tenant company profile, optional)
        threshold: Fuzzy matching threshold (0-100)
        
    Returns:
        Dictionary with validation results
    """
    if not vendor_name:
        return {
            'is_valid': False,
            'reason': 'Vendor name is empty',
            'needs_review': True,
            'confidence': 'low'
        }
    
    if not company_info:
        # Without company info, we can't validate
        return {
            'is_valid': True,
            'reason': 'No company information available for validation',
            'needs_review': False,
            'confidence': 'low'
        }
    
    # Check if vendor matches user's company
    is_match, similarity = fuzzy_match_company(vendor_name, company_info, threshold)
    
    if is_match:
        return {
            'is_valid': False,
            'reason': f'Vendor name "{vendor_name}" matches tenant company "{company_info.display_name}" (similarity: {similarity}%) - likely receiver, not vendor',
            'needs_review': True,
            'confidence': 'high',
            'similarity_score': similarity,
            'matched_company': company_info.display_name,
        }
    
    # Check VAT ID if available
    vendor_vat = None  # This would come from extracted_data in real usage
    if vendor_vat and company_info.vat_id and vendor_vat == company_info.vat_id:
        return {
            'is_valid': False,
            'reason': f'Vendor VAT ID matches user company VAT ID',
            'needs_review': True,
            'confidence': 'very_high'
        }
    
    return {
        'is_valid': True,
        'reason': f'Vendor name does not match user company (similarity: {similarity}%)',
        'needs_review': False,
        'confidence': 'medium' if similarity < 50 else 'high',
        'similarity_score': similarity
    }


def get_tenant_company_info(tenant) -> Optional[Organization]:
    """Return the optional Organization profile for this tenant (tenant schema)."""
    if tenant is None:
        return None
    from django.db import connection
    from django_tenants.utils import get_public_schema_name

    public = get_public_schema_name()
    previous = connection.schema_name
    try:
        connection.set_schema(tenant.schema_name, include_public=False)
        return Organization.objects.filter(tenant_id=tenant.pk).first()
    finally:
        if previous == public:
            connection.set_schema_to_public()
        else:
            connection.set_schema(previous, include_public=False)


def find_invoice_template(
    vendor=None,
    user=None,
    invoice_type='received',
    spatial_data=None
) -> Optional[InvoiceTemplate]:
    """
    Find matching invoice template for a vendor (received) or user (emitted).
    
    Args:
        vendor: Vendor instance (for received invoices)
        user: User instance (for emitted invoices)
        invoice_type: 'received' or 'emitted'
        spatial_data: Optional spatial data to match against template
        
    Returns:
        InvoiceTemplate instance or None
    """
    if invoice_type == 'received' and vendor:
        # Find template for received invoice (vendor template)
        templates = InvoiceTemplate.objects.filter(
            vendor=vendor,
            template_type='received',
            is_active=True
        ).order_by('-is_default', '-usage_count')
        
        if templates.exists():
            return templates.first()
    
    elif invoice_type == 'emitted' and user:
        # Find template for emitted invoice (user's template)
        templates = InvoiceTemplate.objects.filter(
            user=user,
            template_type='emitted',
            is_active=True
        ).order_by('-is_default', '-usage_count')
        
        if templates.exists():
            return templates.first()
    
    return None


def get_template_spatial_hints(template: Optional[InvoiceTemplate], spatial_regions: Dict) -> Dict:
    """
    Get spatial hints based on template's spatial data.
    If template has spatial data, use it to guide extraction.
    
    Args:
        template: InvoiceTemplate instance
        spatial_regions: Spatial regions from PDF extraction
        
    Returns:
        Dictionary with enhanced spatial hints based on template
    """
    if not template or not template.spatial_data:
        return spatial_regions
    
    # Merge template spatial data with extracted regions
    enhanced_hints = spatial_regions.copy()
    template_data = template.spatial_data
    
    # Template spatial_data format:
    # {
    #   'issuer_region': 'top_left',
    #   'receiver_region': 'top_right',
    #   'field_locations': {
    #     'invoice_number': {'region': 'header', 'x': 0.1, 'y': 0.05},
    #     'total_amount': {'region': 'footer', 'x': 0.8, 'y': 0.9}
    #   }
    # }
    
    if 'issuer_region' in template_data:
        issuer_region = template_data['issuer_region']
        if issuer_region in enhanced_hints:
            enhanced_hints['template_issuer_region'] = enhanced_hints.get(issuer_region, '')
    
    if 'receiver_region' in template_data:
        receiver_region = template_data['receiver_region']
        if receiver_region in enhanced_hints:
            enhanced_hints['template_receiver_region'] = enhanced_hints.get(receiver_region, '')
    
    # Add field-specific hints
    if 'field_locations' in template_data:
        enhanced_hints['template_fields'] = template_data['field_locations']
    
    enhanced_hints['template_name'] = template.name
    enhanced_hints['template_id'] = template.id
    
    return enhanced_hints


def create_template_from_invoice(
    invoice: Invoice,
    spatial_data: Dict,
    template_name: Optional[str] = None
) -> InvoiceTemplate:
    """
    Create an invoice template from a processed invoice.
    This allows learning from successfully processed invoices.
    
    Args:
        invoice: Invoice instance
        spatial_data: Spatial data extracted from the invoice
        template_name: Optional template name (auto-generated if not provided)
        
    Returns:
        Created InvoiceTemplate instance
    """
    from django.utils import timezone
    
    # Determine template type and owner
    if invoice.invoice_type == 'received':
        vendor = invoice.vendor
        user = None
        template_type = 'received'
        if not template_name:
            template_name = f"{vendor.name} Template" if vendor else "Received Invoice Template"
    else:
        vendor = None
        user = invoice.vendor  # For emitted, we'd need to track user differently
        # Actually, for emitted invoices, we need the user who created it
        # This might need to be added to Invoice model or extracted differently
        template_type = 'emitted'
        if not template_name:
            template_name = "Emitted Invoice Template"
    
    # Create template
    template = InvoiceTemplate.objects.create(
        name=template_name,
        template_type=template_type,
        vendor=vendor,
        user=user,
        spatial_data=spatial_data,
        sample_invoice=invoice,
        is_active=True,
        is_default=False
    )
    
    return template


@db_transaction.atomic
def record_payment(
    invoice: Invoice,
    *,
    account,
    date: Optional[date_cls] = None,
    amount: Optional[Decimal] = None,
    description: str = "",
    reference: str = "",
    created_by=None,
):
    """Record a payment for `invoice` as a `money.Transaction` linked back.

    - `account` is a `money.Account`.
    - `date` defaults to today.
    - `amount` defaults to the invoice's outstanding amount.
    - For received invoices the transaction is an `out` flow; emitted invoices
      produce an `in` flow.

    Returns the created Transaction. The invoice's legacy `payment_date` is
    set the first time it becomes fully paid (kept for backward compatibility
    with downstream code that still reads it).
    """
    from django.utils import timezone

    from apps.money.models import InvoiceSettlementAllocation, Transaction

    payment_date = date or timezone.localdate()
    payment_amount = (
        Decimal(amount) if amount is not None else invoice.outstanding_amount
    )
    if payment_amount <= 0:
        raise ValueError("Payment amount must be greater than zero.")

    currency = invoice.currency or account.currency
    direction = (
        Transaction.DIRECTION_IN
        if invoice.invoice_type == "emitted"
        else Transaction.DIRECTION_OUT
    )
    counterparty = ""
    if invoice.invoice_type == "emitted" and invoice.customer:
        counterparty = invoice.customer.name
    elif invoice.invoice_type == "received" and invoice.vendor:
        counterparty = invoice.vendor.name

    transaction = Transaction.objects.create(
        date=payment_date,
        direction=direction,
        amount=payment_amount,
        currency=currency,
        account=account,
        customer=invoice.customer,
        vendor=invoice.vendor,
        document=invoice.document_file,
        counterparty=counterparty,
        description=description or f"Payment for invoice {invoice.invoice_number}",
        reference=reference or invoice.invoice_number,
        created_by=created_by,
    )

    InvoiceSettlementAllocation.objects.create(
        transaction=transaction,
        invoice=invoice,
        amount_settlement=payment_amount,
        amount_invoice=payment_amount,
    )

    if not invoice.payment_date:
        total = invoice._coerce_decimal(invoice.total_amount)
        if total is not None and invoice.payments_total >= total:
            invoice.payment_date = payment_date
            invoice.save(update_fields=["payment_date", "updated_at"])

    return transaction


def match_invoice_to_template(
    invoice_type: str,
    vendor=None,
    user=None,
    extracted_vendor_name: Optional[str] = None
) -> Optional[InvoiceTemplate]:
    """
    Match an invoice to an existing template based on vendor/user and invoice type.
    
    Args:
        invoice_type: 'received' or 'emitted'
        vendor: Vendor instance (for received invoices)
        user: User instance (for emitted invoices)
        extracted_vendor_name: Extracted vendor name (for received invoices)
        
    Returns:
        Matching InvoiceTemplate or None
    """
    if invoice_type == 'received':
        if vendor:
            # Try to find template by vendor
            template = find_invoice_template(vendor=vendor, invoice_type='received')
            if template:
                return template
        
        # If vendor not found but we have vendor name, try to find vendor first
        if extracted_vendor_name and not vendor:
            from apps.vendors.models import Vendor
            try:
                vendor = Vendor.objects.filter(name__icontains=extracted_vendor_name).first()
                if vendor:
                    return find_invoice_template(vendor=vendor, invoice_type='received')
            except Exception:
                pass
    
    elif invoice_type == 'emitted':
        if user:
            return find_invoice_template(user=user, invoice_type='emitted')
    
    return None

