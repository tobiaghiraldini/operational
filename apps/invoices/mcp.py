from mcp_server import ModelQueryToolset, mcp_server as mcp
from apps.invoices.models import Invoice, InvoiceExtraction, InvoiceTemplate
from django.utils import timezone
from datetime import datetime, timedelta
from typing import Dict, Optional
from asgiref.sync import sync_to_async


class InvoiceMCP(ModelQueryToolset):
    model = Invoice
    
    # Expose common fields for querying
    allowed_filters = [
        'invoice_number', 'invoice_date', 'due_date', 'payment_date',
        'vendor', 'vendor__name', 'customer', 'customer__name',
        'status', 'currency', 'invoice_type',
        'total_amount', 'needs_manual_review'
    ]


class InvoiceExtractionMCP(ModelQueryToolset):
    model = InvoiceExtraction


class InvoiceTemplateMCP(ModelQueryToolset):
    model = InvoiceTemplate
    

# Module-level functions for invoice analysis tools
# These are defined outside the class to avoid 'self' parameter in tool schema
# Sync helper functions do the actual Django ORM work, async wrappers handle async context

def _do_get_contextual_info() -> Dict:
    """Sync helper function for get_contextual_info."""
    
    now = timezone.now()
    current_date = now.date()
    current_datetime = now
    
    # Calculate date ranges
    if current_date.month == 1:
        last_month = 12
        last_month_year = current_date.year - 1
    else:
        last_month = current_date.month - 1
        last_month_year = current_date.year
    
    # First and last day of current month
    from calendar import monthrange
    first_day_current = current_date.replace(day=1)
    _, last_day_current = monthrange(current_date.year, current_date.month)
    last_day_current_date = current_date.replace(day=last_day_current)
    
    # First and last day of last month
    first_day_last = datetime(last_month_year, last_month, 1).date()
    _, last_day_last = monthrange(last_month_year, last_month)
    last_day_last_date = datetime(last_month_year, last_month, last_day_last).date()
    
    return {
        'current_date': str(current_date),
        'current_datetime': current_datetime.isoformat(),
        'current_year': current_date.year,
        'current_month': current_date.month,
        'current_day': current_date.day,
        'timezone': str(timezone.get_current_timezone()),
        'date_ranges': {
            'current_month': {
                'year': current_date.year,
                'month': current_date.month,
                'start_date': str(first_day_current),
                'end_date': str(last_day_current_date)
            },
            'last_month': {
                'year': last_month_year,
                'month': last_month,
                'start_date': str(first_day_last),
                'end_date': str(last_day_last_date)
            },
            'current_year': {
                'year': current_date.year,
                'start_date': f"{current_date.year}-01-01",
                'end_date': f"{current_date.year}-12-31"
            },
            'last_year': {
                'year': current_date.year - 1,
                'start_date': f"{current_date.year - 1}-01-01",
                'end_date': f"{current_date.year - 1}-12-31"
            }
        },
        'relative_dates': {
            'today': str(current_date),
            'yesterday': str(current_date - timedelta(days=1)),
            'last_7_days_start': str(current_date - timedelta(days=7)),
            'last_30_days_start': str(current_date - timedelta(days=30)),
            'last_90_days_start': str(current_date - timedelta(days=90))
        }
    }


@mcp.tool()
async def get_contextual_info() -> Dict:
    """
    Get current contextual information including date, time, and useful date ranges.
    
    Use this tool when you need to know:
    - What is the current date?
    - What is "last month"?
    - What is "this month"?
    - Date ranges for reports
    
    Returns:
        Dictionary with current date, timezone, and pre-calculated date ranges
    """
    return await sync_to_async(_do_get_contextual_info)()

def _do_get_invoices_by_period(
    start_date: str,
    end_date: str,
    status: Optional[str] = None,
    vendor_name: Optional[str] = None
) -> Dict:
    """Sync helper function for get_invoices_by_period."""
    from django.db.models import Q
    
    # Build query
    query = Q(
        invoice_date__gte=start_date,
        invoice_date__lte=end_date
    )
    
    if status:
        query &= Q(status=status)
    
    if vendor_name:
        query &= Q(vendor__name__icontains=vendor_name)
    
    # Execute query
    invoices_list = list(Invoice.objects.filter(query).select_related('vendor', 'customer', 'payment_method').order_by('-total_amount'))
    
    # Calculate statistics
    total_amount = sum(inv.total_amount for inv in invoices_list)
    vat_amount = sum(inv.vat_amount or 0 for inv in invoices_list)
    
    paid_invoices = [inv for inv in invoices_list if inv.is_paid]
    unpaid_invoices = [inv for inv in invoices_list if not inv.is_paid]
    
    return {
        'count': len(invoices_list),
        'total_amount': float(total_amount),
        'total_vat': float(vat_amount),
        'paid_count': len(paid_invoices),
        'unpaid_count': len(unpaid_invoices),
        'paid_amount': float(sum(inv.total_amount for inv in paid_invoices)),
        'unpaid_amount': float(sum(inv.total_amount for inv in unpaid_invoices)),
        'invoices': [
            {
                'id': inv.id,
                'invoice_number': inv.invoice_number,
                'invoice_type': inv.invoice_type,
                'vendor': inv.vendor.name if inv.vendor else None,
                'customer': inv.customer.name if inv.customer else None,
                'date': str(inv.invoice_date),
                'due_date': str(inv.due_date),
                'amount': float(inv.total_amount),
                'currency': inv.currency,
                'status': inv.status,
                'is_paid': inv.is_paid,
                'payment_date': str(inv.payment_date) if inv.payment_date else None
            }
            for inv in invoices_list
        ]
    }


@mcp.tool()
async def get_invoices_by_period(
    start_date: str,
    end_date: str,
    status: Optional[str] = None,
    vendor_name: Optional[str] = None
) -> Dict:
    """
    Get invoices within a specific date range with optional filters.
    
    Args:
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format
        status: Optional status filter (pending, extracted, review, completed, error)
        vendor_name: Optional vendor name filter (partial match)
    
    Returns:
        Dictionary with invoice list and summary statistics
    """
    return await sync_to_async(_do_get_invoices_by_period)(start_date, end_date, status, vendor_name)


def _do_get_monthly_invoice_summary(year: int, month: int) -> Dict:
    """Sync helper function for get_monthly_invoice_summary."""
    from datetime import date
    from calendar import monthrange
    
    # Get date range for the month
    start_date = date(year, month, 1)
    _, last_day = monthrange(year, month)
    end_date = date(year, month, last_day)
    
    # Query invoices
    invoices_list = list(Invoice.objects.filter(
        invoice_date__gte=start_date,
        invoice_date__lte=end_date
    ).select_related('vendor', 'customer').order_by('invoice_date'))
    
    # Group by currency
    by_currency = {}
    for inv in invoices_list:
        curr = inv.currency
        if curr not in by_currency:
            by_currency[curr] = {
                'count': 0,
                'total_amount': 0,
                'taxable_amount': 0,
                'vat_amount': 0
            }
        
        by_currency[curr]['count'] += 1
        by_currency[curr]['total_amount'] += float(inv.total_amount)
        by_currency[curr]['taxable_amount'] += float(inv.taxable_amount or 0)
        by_currency[curr]['vat_amount'] += float(inv.vat_amount or 0)
    
    # Group by vendor/customer
    by_vendor = {}
    by_customer = {}
    for inv in invoices_list:
        if inv.vendor:
            vendor_name = inv.vendor.name
            if vendor_name not in by_vendor:
                by_vendor[vendor_name] = {
                    'count': 0,
                    'total_amount': 0
                }
            by_vendor[vendor_name]['count'] += 1
            by_vendor[vendor_name]['total_amount'] += float(inv.total_amount)
        elif inv.customer:
            customer_name = inv.customer.name
            if customer_name not in by_customer:
                by_customer[customer_name] = {
                    'count': 0,
                    'total_amount': 0
                }
            by_customer[customer_name]['count'] += 1
            by_customer[customer_name]['total_amount'] += float(inv.total_amount)
    
    # Payment status breakdown
    paid = [inv for inv in invoices_list if inv.is_paid]
    unpaid = [inv for inv in invoices_list if not inv.is_paid]
    overdue = [inv for inv in invoices_list if inv.days_overdue > 0]
    
    return {
        'period': f"{year}-{month:02d}",
        'total_invoices': len(invoices_list),
        'by_currency': by_currency,
        'by_vendor': by_vendor,
        'by_customer': by_customer,
        'payment_status': {
            'paid': len(paid),
            'unpaid': len(unpaid),
            'overdue': len(overdue)
        },
        'invoices': [
            {
                'invoice_number': inv.invoice_number,
                'invoice_type': inv.invoice_type,
                'vendor': inv.vendor.name if inv.vendor else None,
                'customer': inv.customer.name if inv.customer else None,
                'date': str(inv.invoice_date),
                'amount': float(inv.total_amount),
                'vat_amount': float(inv.vat_amount or 0),
                'taxable_amount': float(inv.taxable_amount or 0),
                'currency': inv.currency,
                'is_paid': inv.is_paid
            }
            for inv in invoices_list
        ]
    }


@mcp.tool()
async def get_monthly_invoice_summary(year: int, month: int) -> Dict:
    """
    Get monthly summary of invoices including totals and tax breakdown.
    
    Args:
        year: Year (e.g., 2024)
        month: Month (1-12)
    
    Returns:
        Dictionary with monthly invoice summary and tax details
    """
    return await sync_to_async(_do_get_monthly_invoice_summary)(year, month)


def _do_get_income_outcome_analysis(
    start_date: str,
    end_date: str,
    group_by: str = 'month'
) -> Dict:
    """Sync helper function for get_income_outcome_analysis."""
    # Query invoices in date range
    invoices_list = list(Invoice.objects.filter(
        invoice_date__gte=start_date,
        invoice_date__lte=end_date
    ).select_related('vendor', 'customer').order_by('invoice_date'))
    
    # Group by period
    grouped = {}
    for inv in invoices_list:
        if group_by == 'month':
            period_key = inv.invoice_date.strftime('%Y-%m')
        elif group_by == 'quarter':
            quarter = (inv.invoice_date.month - 1) // 3 + 1
            period_key = f"{inv.invoice_date.year}-Q{quarter}"
        else:  # year
            period_key = str(inv.invoice_date.year)
        
        if period_key not in grouped:
            grouped[period_key] = {
                'total_amount': 0,
                'vat_amount': 0,
                'count': 0,
                'paid_amount': 0,
                'unpaid_amount': 0
            }
        
        grouped[period_key]['count'] += 1
        grouped[period_key]['total_amount'] += float(inv.total_amount)
        grouped[period_key]['vat_amount'] += float(inv.vat_amount or 0)
        
        if inv.is_paid:
            grouped[period_key]['paid_amount'] += float(inv.total_amount)
        else:
            grouped[period_key]['unpaid_amount'] += float(inv.total_amount)
    
    # Calculate totals
    total_amount = sum(float(inv.total_amount) for inv in invoices_list)
    total_vat = sum(float(inv.vat_amount or 0) for inv in invoices_list)
    
    return {
        'period': f"{start_date} to {end_date}",
        'group_by': group_by,
        'total_invoices': len(invoices_list),
        'total_amount': total_amount,
        'total_vat': total_vat,
        'total_taxable': total_amount - total_vat,
        'by_period': grouped,
        'average_invoice_amount': total_amount / len(invoices_list) if invoices_list else 0
    }


@mcp.tool()
async def get_income_outcome_analysis(
    start_date: str,
    end_date: str,
    group_by: Optional[str] = None
) -> Dict:
    """
    Analyze income and outcome trends over a period.
    
    Args:
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format
        group_by: Grouping period ('month', 'quarter', or 'year'). Defaults to 'month' if not provided.
    
    Returns:
        Dictionary with income/outcome analysis
    """
    # Default to 'month' if group_by is None
    if group_by is None:
        group_by = 'month'
    return await sync_to_async(_do_get_income_outcome_analysis)(start_date, end_date, group_by)


def _do_get_vendor_analysis(start_date: str, end_date: str) -> Dict:
    """Sync helper function for get_vendor_analysis."""
    # Query invoices
    invoices_list = list(Invoice.objects.filter(
        invoice_date__gte=start_date,
        invoice_date__lte=end_date
    ).select_related('vendor', 'customer').order_by('-total_amount'))
    
    # Group by vendor
    by_vendor = {}
    for inv in invoices_list:
        if inv.vendor:
            vendor_name = inv.vendor.name
            vendor_id = inv.vendor.id
            
            if vendor_id not in by_vendor:
                by_vendor[vendor_id] = {
                    'vendor_id': vendor_id,
                    'vendor_name': vendor_name,
                    'invoice_count': 0,
                    'total_amount': 0,
                    'average_amount': 0,
                    'currencies': set()
                }
            
            by_vendor[vendor_id]['invoice_count'] += 1
            by_vendor[vendor_id]['total_amount'] += float(inv.total_amount)
            by_vendor[vendor_id]['currencies'].add(inv.currency)
    
    # Calculate averages and convert sets to lists
    vendor_list = []
    for vendor_data in by_vendor.values():
        vendor_data['average_amount'] = (
            vendor_data['total_amount'] / vendor_data['invoice_count']
        )
        vendor_data['currencies'] = list(vendor_data['currencies'])
        vendor_list.append(vendor_data)
    
    # Sort by total amount
    vendor_list.sort(key=lambda x: x['total_amount'], reverse=True)
    
    total_amount = sum(v['total_amount'] for v in vendor_list)
    
    return {
        'period': f"{start_date} to {end_date}",
        'vendor_count': len(vendor_list),
        'total_amount': total_amount,
        'vendors': vendor_list,
        'top_5_vendors': vendor_list[:5]
    }


@mcp.tool()
async def get_vendor_analysis(start_date: str, end_date: str) -> Dict:
    """
    Analyze spending by vendor within a date range.
    
    Args:
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format
    
    Returns:
        Dictionary with vendor spending analysis
    """
    return await sync_to_async(_do_get_vendor_analysis)(start_date, end_date)


def _do_get_overdue_invoices() -> Dict:
    """Sync helper function for get_overdue_invoices."""
    from django.utils import timezone
    
    today = timezone.now().date()
    
    # Query unpaid invoices with past due dates
    invoices_list = list(Invoice.objects.filter(
        payment_date__isnull=True,
        due_date__lt=today
    ).select_related('vendor', 'customer').order_by('due_date'))
    
    total_overdue = sum(float(inv.total_amount) for inv in invoices_list)
    
    return {
        'count': len(invoices_list),
        'total_amount': total_overdue,
        'invoices': [
            {
                'id': inv.id,
                'invoice_number': inv.invoice_number,
                'invoice_type': inv.invoice_type,
                'vendor': inv.vendor.name if inv.vendor else None,
                'customer': inv.customer.name if inv.customer else None,
                'date': str(inv.invoice_date),
                'due_date': str(inv.due_date),
                'days_overdue': inv.days_overdue,
                'amount': float(inv.total_amount),
                'currency': inv.currency
            }
            for inv in invoices_list
        ]
    }


@mcp.tool()
async def get_overdue_invoices() -> Dict:
    """
    Get all currently overdue unpaid invoices.
    
    Returns:
        Dictionary with overdue invoice details
    """
    return await sync_to_async(_do_get_overdue_invoices)()
