from rest_framework import viewsets, filters
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django_filters.rest_framework import DjangoFilterBackend
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.http import HttpResponse
from django.urls import reverse
from django_drf_filepond.models import TemporaryUpload
from apps.files.services.promote_upload import finalize_invoice_upload
from apps.documents.services.celery_task_result_lookup import fetch_task_result
from apps.documents.services.document_file_invoice_task import (
    mark_processing_with_task_id as document_file_mark_processing_with_task_id,
)
import json
from datetime import datetime
from apps.core.tenant import TenantSafeQuerysetMixin
from .models import Invoice, InvoiceExtraction
from .serializers import InvoiceSerializer, InvoiceExtractionSerializer
from .tasks import process_single_invoice
from apps.vendors.models import Vendor, PaymentMethod
from apps.customers.models import Customer
from apps.invoices.currency_lookup import resolve_invoice_currency
from apps.invoices.payment_transaction import (
    coerce_date as _coerce_payment_date,
    sync_invoice_payment_transaction,
)


def _apply_verify_payment_from_post(invoice, post_data) -> None:
    """Set ``payment_date`` / ``paid_override`` from the verify form (not saved)."""
    raw = (post_data.get("payment_date") or "").strip()
    paid_on = post_data.get("paid_override") == "on"
    if raw:
        d = _coerce_payment_date(raw)
        if d:
            invoice.payment_date = d
            invoice.paid_override = False
    elif paid_on:
        invoice.payment_date = None
        invoice.paid_override = True
    else:
        invoice.payment_date = None
        invoice.paid_override = False


class InvoiceViewSet(TenantSafeQuerysetMixin, viewsets.ModelViewSet):
    queryset = Invoice.objects.all()
    serializer_class = InvoiceSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'vendor', 'currency', 'payment_method']
    search_fields = ['invoice_number', 'vendor__name', 'original_filename']
    ordering_fields = ['invoice_date', 'due_date', 'total_amount', 'created_at']
    ordering = ['-invoice_date']

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .select_related("vendor", "customer", "payment_method", "currency")
        )


class InvoiceExtractionViewSet(TenantSafeQuerysetMixin, viewsets.ModelViewSet):
    queryset = InvoiceExtraction.objects.all()
    serializer_class = InvoiceExtractionSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['extraction_method', 'invoice']
    search_fields = ['invoice__invoice_number', 'invoice__vendor__name']
    ordering_fields = ['processed_at', 'confidence_score', 'created_at']
    ordering = ['-processed_at']


@login_required(login_url='/users/signin/')
def invoice_list(request):
    """List view for invoices with filtering and grouping."""
    invoices = Invoice.objects.select_related(
        "vendor", "payment_method", "currency"
    ).all()
    
    # Get filter parameters
    invoice_type_filter = request.GET.get('type')
    vendor_filter = request.GET.get('vendor')
    month_filter = request.GET.get('month')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    group_by = request.GET.get('group_by', 'month')  # month, date, type, vendor
    
    # Apply filters
    if invoice_type_filter:
        invoices = invoices.filter(invoice_type=invoice_type_filter)
    
    if vendor_filter:
        invoices = invoices.filter(vendor_id=vendor_filter)
    
    if month_filter:
        try:
            month_date = datetime.strptime(month_filter, '%Y-%m').date()
            invoices = invoices.filter(
                invoice_date__year=month_date.year,
                invoice_date__month=month_date.month
            )
        except ValueError:
            pass
    
    if date_from:
        try:
            invoices = invoices.filter(invoice_date__gte=date_from)
        except ValueError:
            pass
    
    if date_to:
        try:
            invoices = invoices.filter(invoice_date__lte=date_to)
        except ValueError:
            pass
    
    # Group invoices with formatted labels
    grouped_invoices = {}
    if group_by == 'month':
        # Group by year-month with formatted label
        for invoice in invoices:
            key = invoice.invoice_date.strftime('%Y-%m')
            label = invoice.invoice_date.strftime('%B %Y')  # "January 2024"
            if key not in grouped_invoices:
                grouped_invoices[key] = {'label': label, 'invoices': []}
            grouped_invoices[key]['invoices'].append(invoice)
    elif group_by == 'date':
        # Group by exact date with formatted label
        for invoice in invoices:
            key = invoice.invoice_date.isoformat()
            label = invoice.invoice_date.strftime('%B %d, %Y')  # "January 15, 2024"
            if key not in grouped_invoices:
                grouped_invoices[key] = {'label': label, 'invoices': []}
            grouped_invoices[key]['invoices'].append(invoice)
    elif group_by == 'type':
        # Group by invoice type
        for invoice in invoices:
            key = invoice.get_invoice_type_display()
            label = key  # "Received Invoice" or "Emitted Invoice"
            if key not in grouped_invoices:
                grouped_invoices[key] = {'label': label, 'invoices': []}
            grouped_invoices[key]['invoices'].append(invoice)
    elif group_by == 'vendor':
        # Group by vendor
        for invoice in invoices:
            key = invoice.vendor.name
            label = key  # Vendor name
            if key not in grouped_invoices:
                grouped_invoices[key] = {'label': label, 'invoices': []}
            grouped_invoices[key]['invoices'].append(invoice)
    else:
        # No grouping, just list all
        grouped_invoices['All'] = {'label': 'All Invoices', 'invoices': list(invoices)}
    
    # Sort groups and prepare for template
    if group_by == 'month':
        sorted_groups = sorted(grouped_invoices.items(), reverse=True)
    elif group_by == 'date':
        sorted_groups = sorted(grouped_invoices.items(), reverse=True)
    else:
        sorted_groups = sorted(grouped_invoices.items())
    
    # Convert to simple dict for template (group_name -> invoice_list)
    grouped_invoices_simple = {}
    for key, data in sorted_groups:
        grouped_invoices_simple[data['label']] = data['invoices']
    
    # Get vendors for filter dropdown
    vendors = Vendor.objects.all().order_by('name')
    
    context = {
        'segment': 'invoices',
        'grouped_invoices': grouped_invoices_simple,
        'group_by': group_by,
        'invoice_type_filter': invoice_type_filter,
        'vendor_filter': vendor_filter,
        'month_filter': month_filter,
        'date_from': date_from,
        'date_to': date_to,
        'vendors': vendors,
        'invoice_type_choices': Invoice.INVOICE_TYPE_CHOICES,
        'status_choices': Invoice.STATUS_CHOICES,
    }
    if request.headers.get('HX-Request'):
        return render(request, 'invoices/partials/list_content.html', context)
    return render(request, 'invoices/list.html', context)


@login_required(login_url='/users/signin/')
def invoice_upload(request):
    """Upload view for invoices using FilePond."""
    context = {
        'segment': 'invoices',
        'invoice_type_choices': Invoice.INVOICE_TYPE_CHOICES,
        'document_kind_choices': Invoice.DOCUMENT_KIND_CHOICES,
    }
    return render(request, 'invoices/upload.html', context)


@login_required(login_url='/users/signin/')
def invoice_pdf_view(request, pk):
    """Serve PDF file with proper headers."""
    from django.http import FileResponse, Http404
    from django.conf import settings
    import os
    
    invoice = get_object_or_404(Invoice, pk=pk)
    
    if not invoice.file_path:
        raise Http404("PDF file not found")
    
    # Get the actual file path
    file_path = invoice.file_path
    
    # If it's a relative path, make it absolute
    if not os.path.isabs(file_path):
        # Try MEDIA_ROOT first
        if hasattr(settings, 'MEDIA_ROOT'):
            file_path = os.path.join(settings.MEDIA_ROOT, file_path)
        else:
            raise Http404("PDF file not found")
    else:
        # Check if it's in DJANGO_DRF_FILEPOND_FILE_STORE_PATH
        if hasattr(settings, 'DJANGO_DRF_FILEPOND_FILE_STORE_PATH'):
            if file_path.startswith(settings.DJANGO_DRF_FILEPOND_FILE_STORE_PATH):
                # File is in filepond store, use it directly
                pass
            elif settings.MEDIA_ROOT in file_path:
                # File is in media root, use it directly
                pass
            else:
                # Try to find it in media/invoices
                filename = os.path.basename(file_path)
                potential_path = os.path.join(settings.MEDIA_ROOT, 'invoices', filename)
                if os.path.exists(potential_path):
                    file_path = potential_path
    
    # Check if file exists
    if not os.path.exists(file_path):
        raise Http404(f"PDF file not found at: {file_path}")
    
    # Serve the file with proper headers
    try:
        file_handle = open(file_path, 'rb')
        response = FileResponse(
            file_handle,
            content_type='application/pdf'
        )
        response['Content-Disposition'] = f'inline; filename="{invoice.original_filename}"'
        response['X-Content-Type-Options'] = 'nosniff'
        # Allow iframe embedding
        response['X-Frame-Options'] = 'SAMEORIGIN'
        return response
    except IOError:
        raise Http404("PDF file could not be opened")


@login_required(login_url='/users/signin/')
def invoice_verify(request, pk):
    """Verification interface for reviewing extracted invoice data."""
    invoice = get_object_or_404(Invoice, pk=pk)
    
    # Handle form submission
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'approve':
            # Update invoice with verified data
            from datetime import datetime
            
            invoice.invoice_number = request.POST.get('extracted_invoice_number', invoice.invoice_number)
            
            # Parse dates
            invoice_date_str = request.POST.get('extracted_invoice_date')
            if invoice_date_str:
                try:
                    invoice.invoice_date = datetime.strptime(invoice_date_str, '%Y-%m-%d').date()
                except ValueError:
                    pass
            
            due_date_str = request.POST.get('extracted_due_date')
            if due_date_str:
                try:
                    invoice.due_date = datetime.strptime(due_date_str, '%Y-%m-%d').date()
                except ValueError:
                    pass
            
            # Parse amounts
            total_amount_str = request.POST.get('extracted_total_amount')
            if total_amount_str:
                try:
                    invoice.total_amount = float(total_amount_str)
                except ValueError:
                    pass
            
            if "extracted_currency" in request.POST:
                invoice.currency = resolve_invoice_currency(
                    request.POST.get("extracted_currency")
                )
            
            vat_percentage_str = request.POST.get('extracted_vat_percentage')
            if vat_percentage_str:
                try:
                    invoice.vat_percentage = float(vat_percentage_str)
                except ValueError:
                    pass
            
            vat_amount_str = request.POST.get('extracted_vat_amount')
            if vat_amount_str:
                try:
                    invoice.vat_amount = float(vat_amount_str)
                except ValueError:
                    pass
            
            taxable_amount_str = request.POST.get('extracted_taxable_amount')
            if taxable_amount_str:
                try:
                    invoice.taxable_amount = float(taxable_amount_str)
                except ValueError:
                    pass
            
            # Handle invoice type
            invoice_type = request.POST.get('invoice_type')
            if invoice_type in dict(Invoice.INVOICE_TYPE_CHOICES).keys():
                invoice.invoice_type = invoice_type
            
            # Handle vendor/customer relationships
            if invoice.invoice_type == 'received':
                vendor_id = request.POST.get('vendor_id')
                if vendor_id:
                    try:
                        invoice.vendor = Vendor.objects.get(pk=vendor_id)
                    except Vendor.DoesNotExist:
                        pass
                invoice.customer = None
            elif invoice.invoice_type == 'emitted':
                customer_id = request.POST.get('customer_id')
                if customer_id:
                    try:
                        invoice.customer = Customer.objects.get(pk=customer_id)
                    except Customer.DoesNotExist:
                        pass
                invoice.vendor = None
            
            # Handle payment method
            payment_method_id = request.POST.get('payment_method_id')
            if payment_method_id:
                try:
                    invoice.payment_method = PaymentMethod.objects.get(pk=payment_method_id)
                except PaymentMethod.DoesNotExist:
                    pass

            _apply_verify_payment_from_post(invoice, request.POST)

            invoice.status = 'completed'
            invoice.needs_manual_review = False
            invoice.save()
            sync_invoice_payment_transaction(invoice, created_by=request.user)

            return redirect('invoices:invoice_list')
        
        elif action == 'save':
            # Save changes without changing status to completed
            # Update invoice with verified data
            from datetime import datetime
            
            invoice.invoice_number = request.POST.get('extracted_invoice_number', invoice.invoice_number)
            
            # Parse dates
            invoice_date_str = request.POST.get('extracted_invoice_date')
            if invoice_date_str:
                try:
                    invoice.invoice_date = datetime.strptime(invoice_date_str, '%Y-%m-%d').date()
                except ValueError:
                    pass
            
            due_date_str = request.POST.get('extracted_due_date')
            if due_date_str:
                try:
                    invoice.due_date = datetime.strptime(due_date_str, '%Y-%m-%d').date()
                except ValueError:
                    pass
            
            # Parse amounts
            total_amount_str = request.POST.get('extracted_total_amount')
            if total_amount_str:
                try:
                    invoice.total_amount = float(total_amount_str)
                except ValueError:
                    pass
            
            if "extracted_currency" in request.POST:
                invoice.currency = resolve_invoice_currency(
                    request.POST.get("extracted_currency")
                )
            
            vat_percentage_str = request.POST.get('extracted_vat_percentage')
            if vat_percentage_str:
                try:
                    invoice.vat_percentage = float(vat_percentage_str)
                except ValueError:
                    pass
            
            vat_amount_str = request.POST.get('extracted_vat_amount')
            if vat_amount_str:
                try:
                    invoice.vat_amount = float(vat_amount_str)
                except ValueError:
                    pass
            
            taxable_amount_str = request.POST.get('extracted_taxable_amount')
            if taxable_amount_str:
                try:
                    invoice.taxable_amount = float(taxable_amount_str)
                except ValueError:
                    pass
            
            # Handle invoice type
            invoice_type = request.POST.get('invoice_type')
            if invoice_type in dict(Invoice.INVOICE_TYPE_CHOICES).keys():
                invoice.invoice_type = invoice_type
            
            # Handle vendor/customer relationships
            if invoice.invoice_type == 'received':
                vendor_id = request.POST.get('vendor_id')
                if vendor_id:
                    try:
                        invoice.vendor = Vendor.objects.get(pk=vendor_id)
                    except Vendor.DoesNotExist:
                        pass
                invoice.customer = None
            elif invoice.invoice_type == 'emitted':
                customer_id = request.POST.get('customer_id')
                if customer_id:
                    try:
                        invoice.customer = Customer.objects.get(pk=customer_id)
                    except Customer.DoesNotExist:
                        pass
                invoice.vendor = None
            
            # Handle payment method
            payment_method_id = request.POST.get('payment_method_id')
            if payment_method_id:
                try:
                    invoice.payment_method = PaymentMethod.objects.get(pk=payment_method_id)
                except PaymentMethod.DoesNotExist:
                    pass

            _apply_verify_payment_from_post(invoice, request.POST)

            # Keep status as is (don't change to completed)
            invoice.save()
            sync_invoice_payment_transaction(invoice, created_by=request.user)

            return redirect('invoices:invoice_verify', pk=invoice.pk)
    
    # Get extraction data if available
    extraction = None
    extracted_data = {}
    if hasattr(invoice, 'extraction'):
        extraction = invoice.extraction
        extracted_data = extraction.raw_extracted_data or {}
    
    # Prepare field mapping for side-by-side comparison
    field_mapping = {
        'invoice_number': ('Invoice Number', extracted_data.get('invoice_number', '')),
        'invoice_date': ('Invoice Date', extracted_data.get('invoice_date', '')),
        'due_date': ('Due Date', extracted_data.get('due_date', '')),
        'total_amount': ('Total Amount', extracted_data.get('total_amount', '')),
        'currency': ('Currency', extracted_data.get('currency', '')),
        'vendor_name': ('Vendor Name', extracted_data.get('vendor_name', '')),
        'customer_name': ('Customer Name', extracted_data.get('customer_name', '')),
        'vendor_vat_id': ('Vendor VAT ID', extracted_data.get('vendor_vat_id', '')),
        'vendor_address': ('Vendor Address', extracted_data.get('vendor_address', '')),
        'payment_method': ('Payment Method', extracted_data.get('payment_method', '')),
        'vat_percentage': ('VAT Percentage', extracted_data.get('vat_percentage', '')),
        'vat_amount': ('VAT Amount', extracted_data.get('vat_amount', '')),
        'taxable_amount': ('Taxable Amount', extracted_data.get('taxable_amount', '')),
    }
    
    # Get all vendors, customers, and payment methods for dropdowns
    vendors = Vendor.objects.filter(is_active=True).order_by('name')
    customers = Customer.objects.filter(is_active=True).order_by('name')
    payment_methods = PaymentMethod.objects.filter(is_active=True).order_by('name')
    
    context = {
        'segment': 'invoices',
        'invoice': invoice,
        'extraction': extraction,
        'extracted_data': extracted_data,
        'field_mapping': field_mapping,
        'vendors': vendors,
        'customers': customers,
        'payment_methods': payment_methods,
        'invoice_type_choices': Invoice.INVOICE_TYPE_CHOICES,
    }
    return render(request, 'invoices/verify.html', context)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_vendor_quick(request):
    """Quick create vendor endpoint for modal form (JSON API or HTMX form POST)."""
    data = request.POST if request.headers.get('HX-Request') else request.data
    try:
        name = (data.get('name') or '').strip()
        if not name:
            if request.headers.get('HX-Request'):
                resp = render(request, 'invoices/partials/create_vendor_form_partial.html', {'error': 'Name is required'})
                resp.status_code = 400
                return resp
            return Response({'error': 'Name is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        vendor = Vendor.objects.create(
            name=name,
            vat_id=(data.get('vat_id') or '').strip(),
            address=(data.get('address') or '').strip(),
            country_code=(data.get('country_code') or 'IT').strip(),
            email=(data.get('email') or '').strip(),
            phone=(data.get('phone') or '').strip(),
            is_active=True
        )
        
        if request.headers.get('HX-Request'):
            resp = render(request, 'invoices/partials/create_vendor_response.html', {'vendor': vendor})
            resp['HX-Trigger'] = 'closeVendorModal'
            return resp
        
        return Response({
            'id': vendor.id,
            'name': vendor.name,
            'vat_id': vendor.vat_id,
            'address': vendor.address,
            'country_code': vendor.country_code,
            'email': vendor.email,
            'phone': vendor.phone,
        }, status=status.HTTP_201_CREATED)
    except Exception as e:
        if request.headers.get('HX-Request'):
            resp = render(request, 'invoices/partials/create_vendor_form_partial.html', {'error': str(e)})
            resp.status_code = 400
            return resp
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_customer_quick(request):
    """Quick create customer endpoint for modal form (JSON API or HTMX form POST)."""
    data = request.POST if request.headers.get('HX-Request') else request.data
    try:
        name = (data.get('name') or '').strip()
        if not name:
            if request.headers.get('HX-Request'):
                resp = render(request, 'invoices/partials/create_customer_form_partial.html', {'error': 'Name is required'})
                resp.status_code = 400
                return resp
            return Response({'error': 'Name is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        customer = Customer.objects.create(
            name=name,
            vat_id=(data.get('vat_id') or '').strip(),
            address=(data.get('address') or '').strip(),
            country_code=(data.get('country_code') or 'IT').strip(),
            email=(data.get('email') or '').strip(),
            phone=(data.get('phone') or '').strip(),
            is_active=True
        )
        
        if request.headers.get('HX-Request'):
            resp = render(request, 'invoices/partials/create_customer_response.html', {'customer': customer})
            resp['HX-Trigger'] = 'closeCustomerModal'
            return resp
        
        return Response({
            'id': customer.id,
            'name': customer.name,
            'vat_id': customer.vat_id,
            'address': customer.address,
            'country_code': customer.country_code,
            'email': customer.email,
            'phone': customer.phone,
        }, status=status.HTTP_201_CREATED)
    except Exception as e:
        if request.headers.get('HX-Request'):
            resp = render(request, 'invoices/partials/create_customer_form_partial.html', {'error': str(e)})
            resp.status_code = 400
            return resp
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def process_upload(request):
    """API endpoint to process a FilePond temporary upload."""
    upload_id = request.data.get('upload_id')
    
    if not upload_id:
        return Response({'success': False, 'error': 'upload_id is required'}, status=400)
    
    try:
        classification_hints = request.data.get("classification_hints")
        if classification_hints is not None and not isinstance(classification_hints, dict):
            classification_hints = None
        classification_hints = dict(classification_hints or {})

        raw_invoice_type = classification_hints.get("invoice_type") or request.data.get(
            "invoice_type"
        )
        invoice_type_hint = None
        if isinstance(raw_invoice_type, str) and raw_invoice_type.strip().lower() in (
            "received",
            "emitted",
        ):
            invoice_type_hint = raw_invoice_type.strip().lower()

        promoted = finalize_invoice_upload(
            upload_id, invoice_type=invoice_type_hint
        )

        raw_vendor = request.data.get("vendor_id")
        vendor_id = None
        if raw_vendor not in (None, "", "null"):
            try:
                vendor_id = int(raw_vendor)
            except (TypeError, ValueError):
                vendor_id = None
        if vendor_id is not None:
            classification_hints["vendor_id"] = vendor_id

        result = process_single_invoice.delay(
            promoted.file_path,
            promoted.original_filename,
            vendor_id=vendor_id,
            user_id=request.user.id if request.user.is_authenticated else None,
            document_file_id=promoted.document_file.pk,
            schema_name=getattr(request.tenant, "schema_name", None),
            classification_hints=classification_hints,
        )
        document_file_mark_processing_with_task_id(
            promoted.document_file.pk, result.id
        )

        # Return task ID - frontend can poll for completion
        # The task will create the invoice and extraction records
        return Response({
            'success': True,
            'upload_id': upload_id,
            'task_id': result.id,
            'message': 'Processing started. Invoice will be created when processing completes.'
        })
        
    except TemporaryUpload.DoesNotExist:
        return Response({'success': False, 'error': 'Upload not found'}, status=404)
    except Exception as e:
        return Response({'success': False, 'error': str(e)}, status=500)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def upload_invoice_zip_batch(request):
    """Upload a ZIP of PDFs; each file becomes a ``DocumentFile`` and is queued for extraction."""
    from django.db import connection
    from django_tenants.utils import get_public_schema_name

    from apps.documents.models import DocumentFolder
    from apps.files.services.zip_invoice_batch import ingest_zip_invoice_pdfs

    zf = request.FILES.get("zip")
    if not zf:
        return Response({"success": False, "error": "zip file is required"}, status=status.HTTP_400_BAD_REQUEST)

    from django.conf import settings as dj_settings

    cap = getattr(dj_settings, "INVOICE_ZIP_MAX_BYTES", 50 * 1024 * 1024)
    size = getattr(zf, "size", None) or 0
    if size and size > cap:
        return Response(
            {"success": False, "error": f"ZIP exceeds maximum size ({cap} bytes)."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    folder = None
    raw_folder = request.POST.get("folder_id") or request.data.get("folder_id")
    if raw_folder not in (None, "", "null"):
        try:
            folder = DocumentFolder.objects.get(pk=int(raw_folder))
        except (ValueError, DocumentFolder.DoesNotExist):
            folder = None

    schema_name = None
    if connection.schema_name != get_public_schema_name():
        schema_name = connection.schema_name

    result = ingest_zip_invoice_pdfs(
        zf,
        folder=folder,
        user_id=request.user.id if request.user.is_authenticated else None,
        schema_name=schema_name,
    )
    if not result.get("success"):
        return Response(result, status=status.HTTP_400_BAD_REQUEST)
    return Response(result, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def check_task_status(request, task_id):
    """API endpoint to check Celery task status (JSON or HTML fragment for HTMX polling)."""
    try:
        task_result = fetch_task_result(task_id)
        if task_result is None:
            if request.headers.get('HX-Request'):
                return render(request, 'invoices/partials/task_status.html', {'status': 'PENDING', 'task_id': task_id})
            return Response({
                'status': 'PENDING',
                'task_id': task_id,
                'message': 'Task not found in database yet'
            })
        
        # Parse result if it's a string
        result_data = None
        if task_result.result:
            try:
                if isinstance(task_result.result, str):
                    result_data = json.loads(task_result.result)
                else:
                    result_data = task_result.result
            except (json.JSONDecodeError, TypeError):
                result_data = task_result.result
        
        if request.headers.get('HX-Request'):
            invoice_id = None
            if result_data and isinstance(result_data, dict) and result_data.get('invoice_id'):
                invoice_id = result_data['invoice_id']
            elif result_data and isinstance(result_data, str):
                try:
                    parsed = json.loads(result_data)
                    invoice_id = parsed.get('invoice_id') if isinstance(parsed, dict) else None
                except (json.JSONDecodeError, TypeError):
                    pass
            redirect_url = reverse('invoices:invoice_verify', args=[invoice_id]) if invoice_id else reverse('invoices:invoice_list')
            context = {
                'status': task_result.status,
                'task_id': task_id,
                'result_data': result_data,
                'redirect_url': redirect_url,
            }
            resp = render(request, 'invoices/partials/task_status.html', context)
            if task_result.status == 'SUCCESS':
                resp['HX-Redirect'] = redirect_url
            return resp
        
        return Response({
            'status': task_result.status,
            'task_id': task_result.task_id,
            'result': result_data,
            'date_created': task_result.date_created.isoformat() if task_result.date_created else None,
            'date_done': task_result.date_done.isoformat() if task_result.date_done else None,
        })
    except Exception as e:
        if request.headers.get('HX-Request'):
            return render(request, 'invoices/partials/task_status.html', {'status': 'FAILURE', 'error': str(e)}, status=500)
        return Response({'success': False, 'error': str(e)}, status=500)