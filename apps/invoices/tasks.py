import os
import json
import requests
import hashlib
from contextlib import nullcontext
from pathlib import Path
from celery import shared_task
from django.db import transaction
from django.utils import timezone
from django.conf import settings
from django_tenants.utils import schema_context
from pdfplumber import open as pdf_open
from apps.invoices.models import Invoice, InvoiceExtraction
from apps.vendors.models import Vendor, PaymentMethod
from apps.documents.models import DocumentFile
from apps.invoices.services import (
    get_user_company_info, 
    validate_vendor_extraction, 
    identify_issuer_receiver,
    find_invoice_template,
    get_template_spatial_hints,
    match_invoice_to_template
)
from apps.documents.ocr import OCRProcessor
from django.contrib.auth import get_user_model

User = get_user_model()


@shared_task(bind=True, max_retries=3)
def process_single_invoice(
    self,
    file_path,
    original_filename,
    vendor_id=None,
    user_id=None,
    document_file_id=None,
    schema_name=None,
):
    """
    Process a single invoice PDF file.
    
    Args:
        file_path: Path to the PDF file
        original_filename: Original filename
        vendor_id: Optional vendor ID
        user_id: Optional user ID for company information matching
        document_file_id: Optional DocumentFile ID to link the invoice to
    """
    print(f"[TASK DEBUG] Processing invoice: {original_filename}")
    print(f"[TASK DEBUG] File path: {file_path}")
    print(f"[TASK DEBUG] User ID: {user_id}")
    print(f"[TASK DEBUG] Document File ID: {document_file_id}")
    
    tenant_context = schema_context(schema_name) if schema_name else nullcontext()
    with tenant_context:
        return _process_single_invoice_impl(
            self,
            file_path=file_path,
            original_filename=original_filename,
            vendor_id=vendor_id,
            user_id=user_id,
            document_file_id=document_file_id,
        )


def _process_single_invoice_impl(self, file_path, original_filename, vendor_id=None, user_id=None, document_file_id=None):
    # Try to find DocumentFile if not provided
    document_file = None
    if document_file_id:
        try:
            document_file = DocumentFile.objects.get(pk=document_file_id)
            print(f"[TASK DEBUG] Found DocumentFile: {document_file.filename}")
        except DocumentFile.DoesNotExist:
            print(f"[TASK DEBUG] DocumentFile {document_file_id} not found, will try to find by file path/hash")
    
    # If not found by ID, try to find by file path or hash
    if not document_file and os.path.exists(file_path):
        file_hash = calculate_file_hash(file_path)
        if file_hash:
            # Try to find by hash first (most reliable)
            document_file = DocumentFile.objects.filter(file_hash=file_hash).first()
            if document_file:
                print(f"[TASK DEBUG] Found DocumentFile by hash: {document_file.filename}")
        
        # If still not found, try to find by file path
        if not document_file:
            document_file = DocumentFile.objects.filter(file_path=file_path).first()
            if document_file:
                print(f"[TASK DEBUG] Found DocumentFile by path: {document_file.filename}")
    
    try:
        # Check if file exists
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        
        # Get user's company information if user_id provided
        company_info = None
        if user_id:
            try:
                user = User.objects.get(pk=user_id)
                company_info = get_user_company_info(user)
                if company_info:
                    print(f"[TASK DEBUG] Found company info: {company_info.name}")
                else:
                    print(f"[TASK DEBUG] No company info found for user")
            except User.DoesNotExist:
                print(f"[TASK DEBUG] User {user_id} not found")
        
        # Extract text from PDF with layout information
        print(f"[TASK DEBUG] Extracting text from PDF...")
        ocr_processor = OCRProcessor()
        
        # Try layout-aware extraction first
        layout_data = ocr_processor.extract_text_with_layout(file_path)
        if layout_data.get('success'):
            text_content = layout_data.get('text', '')
            spatial_regions = ocr_processor.get_spatial_regions(file_path)
            print(f"[TASK DEBUG] Layout extraction successful, using enhanced extraction")
        else:
            # Fallback to basic extraction
            basic_result = ocr_processor.extract_text_from_pdf(file_path)
            text_content = basic_result.get('text', '')
            spatial_regions = None
            print(f"[TASK DEBUG] Using basic text extraction")
        
        if not text_content.strip():
            raise ValueError("No text extracted from PDF")
        
        print(f"[TASK DEBUG] Text extracted, length: {len(text_content)} characters")
        
        # Try to find matching template (before extraction, we need vendor name)
        # We'll do a quick extraction first to get vendor name, then match template
        # For now, we'll extract and then try to match template
        # In future, we could do a two-pass extraction
        
        # Call Ollama for initial data extraction
        print(f"[TASK DEBUG] Calling Ollama for initial data extraction...")
        extracted_data = call_ollama_extraction(text_content, company_info, spatial_regions)
        print(f"[TASK DEBUG] Initial extraction completed")
        
        # Determine invoice type and find template
        vendor_name = extracted_data.get('vendor_name', '')
        invoice_type = 'received'  # Default to received (expense)
        
        # Check if vendor matches user's company to determine invoice type
        if company_info and vendor_name:
            vendor_validation = validate_vendor_extraction(vendor_name, company_info)
            if vendor_validation.get('needs_review', False):
                # Vendor matches user's company -> this is an emitted invoice (income)
                invoice_type = 'emitted'
                print(f"[TASK DEBUG] Vendor matches user company -> Emitted invoice (income)")
            else:
                # Vendor doesn't match -> received invoice (expense)
                invoice_type = 'received'
                print(f"[TASK DEBUG] Vendor doesn't match user company -> Received invoice (expense)")
        
        # Try to find matching template
        template = None
        if invoice_type == 'received':
            # For received invoices, try to find vendor template
            if vendor_id:
                from apps.vendors.models import Vendor
                try:
                    vendor = Vendor.objects.get(pk=vendor_id)
                    template = find_invoice_template(vendor=vendor, invoice_type='received')
                except Vendor.DoesNotExist:
                    pass
            # Also try by vendor name
            if not template and vendor_name:
                template = match_invoice_to_template(
                    invoice_type='received',
                    extracted_vendor_name=vendor_name
                )
        else:
            # For emitted invoices, find user's template
            if user_id:
                try:
                    user = User.objects.get(pk=user_id)
                    template = find_invoice_template(user=user, invoice_type='emitted')
                except User.DoesNotExist:
                    pass
        
        if template:
            print(f"[TASK DEBUG] Found template: {template.name}")
            # Enhance spatial hints with template data
            if spatial_regions:
                spatial_hints = get_template_spatial_hints(template, spatial_regions)
            else:
                spatial_hints = None
            # Re-extract with template-enhanced hints
            print(f"[TASK DEBUG] Re-extracting with template-enhanced spatial hints...")
            extracted_data = call_ollama_extraction(text_content, company_info, spatial_hints, template)
        else:
            spatial_hints = spatial_regions
            print(f"[TASK DEBUG] No template found, using default extraction")
        
        # Set invoice type in extracted data
        extracted_data['invoice_type'] = invoice_type
        print(f"[TASK DEBUG] Invoice type determined: {invoice_type}")
        
        # Save extracted data to database with validation
        print(f"[TASK DEBUG] Saving to database...")
        with transaction.atomic():
            invoice = save_extracted_data(
                extracted_data, 
                file_path, 
                original_filename, 
                vendor_id, 
                company_info,
                template=template,
                user_id=user_id,
                document_file=document_file
            )
            
            # Check if extraction already exists
            extraction, created = InvoiceExtraction.objects.get_or_create(
                invoice=invoice,
                defaults={
                    'raw_text': text_content,
                    'raw_extracted_data': extracted_data,
                    'extraction_method': 'llm',
                    'confidence_score': calculate_confidence(extracted_data),
                    'processed_at': timezone.now()
                }
            )
            
            if not created:
                print(f"[TASK DEBUG] Updating existing extraction...")
                extraction.raw_text = text_content
                extraction.raw_extracted_data = extracted_data
                extraction.extraction_method = 'llm'
                extraction.confidence_score = calculate_confidence(extracted_data)
                extraction.processed_at = timezone.now()
                extraction.save()
        
        print(f"[TASK DEBUG] Processing completed successfully")
        return {
            'success': True, 
            'invoice_id': invoice.id, 
            'invoice_number': invoice.invoice_number,
            'vendor_name': invoice.vendor.name,
            'extraction_created': created
        }
        
    except Exception as e:
        print(f"[TASK DEBUG] Error processing invoice: {str(e)}")
        print(f"[TASK DEBUG] Retry count: {self.request.retries}")
        
        # Don't retry on certain errors
        if isinstance(e, (FileNotFoundError, ValueError)):
            print(f"[TASK DEBUG] Non-retryable error, not retrying")
            return {
                'success': False,
                'error': str(e),
                'file': original_filename
            }
        
        # Update retry count and error message
        if self.request.retries < self.max_retries:
            print(f"[TASK DEBUG] Retrying in {60 * pow(2, self.request.retries)} seconds...")
            self.retry(countdown=60 * pow(2, self.request.retries), exc=e)
        else:
            print(f"[TASK DEBUG] Max retries reached, giving up")
            return {
                'success': False,
                'error': str(e),
                'file': original_filename,
                'retries_exhausted': True
            }


@shared_task
def process_document_folder(folder_path, schema_name=None):
    """
    Process all PDF files in a specified folder.
    """
    tenant_context = schema_context(schema_name) if schema_name else nullcontext()
    with tenant_context:
        folder_path = Path(folder_path)
        if not folder_path.exists():
            raise ValueError(f"Folder {folder_path} does not exist")

        pdf_files = list(folder_path.glob('**/*.pdf'))
        results = []
        for pdf_file in pdf_files:
            try:
                file_hash = calculate_file_hash(str(pdf_file))
                if DocumentFile.objects.filter(file_hash=file_hash).exists():
                    continue

                result = process_single_invoice.delay(
                    str(pdf_file.absolute()),
                    pdf_file.name,
                    schema_name=schema_name,
                )
                results.append({'file': pdf_file.name, 'task_id': result.id, 'status': 'queued'})
            except Exception as e:
                results.append({'file': pdf_file.name, 'error': str(e), 'status': 'error'})

        return results


@shared_task
def test_ollama_connection():
    """
    Test Ollama connection from Celery worker.
    """
    print("=== Testing Ollama Connection from Celery ===")
    print(f"OLLAMA_URL: {settings.OLLAMA_URL}")
    print(f"OLLAMA_MODEL: {settings.OLLAMA_MODEL}")
    print(f"OLLAMA_TIMEOUT: {settings.OLLAMA_TIMEOUT}")
    
    payload = {
        "model": settings.OLLAMA_MODEL,
        "prompt": "Hello from Celery! Respond with 'Celery OK' if you can hear me.",
        "stream": False
    }
    
    try:
        print("Making request to Ollama...")
        response = requests.post(settings.OLLAMA_URL, json=payload, timeout=settings.OLLAMA_TIMEOUT)
        print(f"Response status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"Response: {result['response']}")
            return {"success": True, "response": result['response']}
        else:
            print(f"Error: {response.status_code}")
            print(f"Response text: {response.text}")
            return {"success": False, "error": f"HTTP {response.status_code}: {response.text}"}
            
    except Exception as e:
        print(f"Exception: {str(e)}")
        return {"success": False, "error": str(e)}


def extract_text_from_pdf(file_path):
    """
    Extract text content from PDF file.
    """
    try:
        with pdf_open(file_path) as pdf:
            text = ""
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
            return text.strip()
    except Exception as e:
        raise Exception(f"PDF extraction failed: {str(e)}")


def call_ollama_extraction(invoice_text, company_info=None, spatial_hints=None, template=None):
    """
    Call Ollama API to extract structured data from invoice text.
    
    Args:
        invoice_text: Extracted text from invoice
        company_info: Optional CompanyInformation instance for context
        spatial_hints: Optional spatial region information
    """
    ollama_url = settings.OLLAMA_URL
    model = settings.OLLAMA_MODEL
    timeout = settings.OLLAMA_TIMEOUT
    
    # Debug logging
    print(f"[OLLAMA DEBUG] URL: {ollama_url}")
    print(f"[OLLAMA DEBUG] Model: {model}")
    print(f"[OLLAMA DEBUG] Timeout: {timeout}")
    
    # Build company context section
    company_context = ""
    if company_info:
        company_context = f"""
YOUR COMPANY INFORMATION (for reference - this is the RECEIVER, not the vendor):
- Company Name: {company_info.name}
- Legal Name: {company_info.legal_name or 'N/A'}
- VAT ID: {company_info.vat_id}
- Address: {company_info.address}, {company_info.city}, {company_info.postal_code}, {company_info.country_code}
- Alternative Names: {', '.join(company_info.aliases) if company_info.aliases else 'None'}

IMPORTANT INSTRUCTIONS:
- The INVOICE ISSUER is the company that created/sent the invoice (usually in top-left or header section)
- The INVOICE RECEIVER is the company receiving the invoice (usually in top-right or "Bill To" section)
- If the extracted vendor_name matches your company information above, it is likely the RECEIVER, not the vendor
- Always return both issuer_name and receiver_name in the JSON response
- The vendor_name should be the ISSUER (the company sending the invoice)
"""
    
    # Build spatial hints section
    spatial_context = ""
    if spatial_hints and spatial_hints.get('success'):
        # If template is available, use template-specific regions
        if template and 'template_issuer_region' in spatial_hints:
            spatial_context = f"""
SPATIAL LAYOUT INFORMATION (from template: {template.name}):
- Issuer Region (from template): {spatial_hints.get('template_issuer_region', '')[:500]}
- Receiver Region (from template): {spatial_hints.get('template_receiver_region', '')[:500]}
- Top-Left Region: {spatial_hints.get('top_left', '')[:500]}
- Top-Right Region: {spatial_hints.get('top_right', '')[:500]}
- Header: {spatial_hints.get('header', '')[:300]}
"""
        else:
            spatial_context = f"""
SPATIAL LAYOUT INFORMATION:
- Top-Left Region (often contains issuer): {spatial_hints.get('top_left', '')[:500]}
- Top-Right Region (often contains receiver): {spatial_hints.get('top_right', '')[:500]}
- Header: {spatial_hints.get('header', '')[:300]}
"""
    
    prompt = f"""
Extract the following fields from this invoice in valid JSON format:
- invoice_number (string)
- invoice_date (YYYY-MM-DD)
- due_date (YYYY-MM-DD)
- total_amount (numeric)
- currency (3-letter code, default: EUR)
- vendor_name (string) - This is the INVOICE ISSUER (company that sent the invoice)
- issuer_name (string) - Same as vendor_name, the company that issued the invoice
- receiver_name (string) - The company receiving the invoice (may be your company)
- vendor_vat_id (string or null)
- vendor_address (string)
- payment_method (string: credit_card, bank_transfer, paypal, cash, check, other)
- vat_percentage (numeric or null)
- vat_amount (numeric or null)
- taxable_amount (numeric or null)

{company_context}

{spatial_context}

Return ONLY valid JSON, no other text.

Invoice Text:
{invoice_text[:4000]}
"""
    
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.1,  # Low temperature for consistent extraction
            "top_p": 0.9
        }
    }
    
    print(f"[OLLAMA DEBUG] Payload: {json.dumps(payload, indent=2)}")
    
    try:
        print(f"[OLLAMA DEBUG] Making request to {ollama_url}")
        response = requests.post(ollama_url, json=payload, timeout=timeout)
        print(f"[OLLAMA DEBUG] Response status: {response.status_code}")
        print(f"[OLLAMA DEBUG] Response headers: {dict(response.headers)}")
        
        if response.status_code != 200:
            print(f"[OLLAMA DEBUG] Error response: {response.text}")
            raise Exception(f"Ollama API returned {response.status_code}: {response.text}")
        
        result = response.json()
        print(f"[OLLAMA DEBUG] Response: {result}")
        
        # Parse the response
        extracted_json = json.loads(result['response'])
        print(f"[OLLAMA DEBUG] Extracted JSON: {extracted_json}")
        return extracted_json
        
    except json.JSONDecodeError as e:
        print(f"[OLLAMA DEBUG] JSON decode error: {str(e)}")
        print(f"[OLLAMA DEBUG] Raw response: {result if 'result' in locals() else 'No result'}")
        raise Exception(f"Invalid JSON response from Ollama: {str(e)}")
    except requests.RequestException as e:
        print(f"[OLLAMA DEBUG] Request error: {str(e)}")
        raise Exception(f"Ollama API call failed: {str(e)}")
    except Exception as e:
        print(f"[OLLAMA DEBUG] Unexpected error: {str(e)}")
        raise Exception(f"Unexpected error during extraction: {str(e)}")


def save_extracted_data(extracted_data, file_path, original_filename, vendor_id=None, company_info=None, template=None, user_id=None, document_file=None):
    """
    Save extracted data to database models with validation.
    
    Args:
        extracted_data: Extracted invoice data
        file_path: Path to invoice file
        original_filename: Original filename
        vendor_id: Optional vendor ID
        company_info: Optional CompanyInformation for validation
        template: Optional InvoiceTemplate used for extraction
        user_id: Optional user ID
        document_file: Optional DocumentFile instance to link the invoice to
    """
    # Validate vendor extraction
    vendor_name = extracted_data.get('vendor_name', 'Unknown Vendor')
    validation_result = validate_vendor_extraction(vendor_name, company_info)
    
    needs_review = validation_result.get('needs_review', False)
    validation_reason = validation_result.get('reason', '')
    
    if needs_review:
        print(f"[SAVE DEBUG] Validation flag: {validation_reason}")
    
    # Get or create vendor
    # Ensure vat_id and address are strings, not None (handle JSON null values)
    vendor_vat_id = extracted_data.get('vendor_vat_id') or ''
    vendor_address = extracted_data.get('vendor_address') or ''
    
    vendor, created = Vendor.objects.get_or_create(
        name=vendor_name,
        defaults={
            'vat_id': vendor_vat_id,
            'address': vendor_address,
            'country_code': 'IT'  # Default for Italian invoices
        }
    )
    
    # Get or create payment method
    payment_method_code = extracted_data.get('payment_method', 'other')
    payment_method, _ = PaymentMethod.objects.get_or_create(
        code=payment_method_code,
        defaults={
            'name': payment_method_code.replace('_', ' ').title(),
            'description': f'Payment method: {payment_method_code}'
        }
    )
    
    # Check if invoice already exists
    invoice_number = extracted_data.get('invoice_number', '')
    existing_invoice = Invoice.objects.filter(
        invoice_number=invoice_number,
        vendor=vendor
    ).first()
    
    if existing_invoice:
        print(f"[SAVE DEBUG] Invoice {invoice_number} from {vendor.name} already exists, updating...")
        # Update existing invoice with new data
        existing_invoice.invoice_date = extracted_data.get('invoice_date') or existing_invoice.invoice_date
        existing_invoice.due_date = extracted_data.get('due_date') or existing_invoice.due_date
        existing_invoice.total_amount = extracted_data.get('total_amount', existing_invoice.total_amount)
        existing_invoice.currency = extracted_data.get('currency', existing_invoice.currency)
        existing_invoice.vat_percentage = extracted_data.get('vat_percentage') or existing_invoice.vat_percentage
        existing_invoice.vat_amount = extracted_data.get('vat_amount') or existing_invoice.vat_amount
        existing_invoice.taxable_amount = extracted_data.get('taxable_amount') or existing_invoice.taxable_amount
        existing_invoice.payment_method = payment_method or existing_invoice.payment_method
        existing_invoice.status = 'extracted'
        existing_invoice.needs_manual_review = False
        existing_invoice.extraction_errors = ''
        # Update document_file if provided and not already set
        if document_file and not existing_invoice.document_file:
            existing_invoice.document_file = document_file
        existing_invoice.save()
        return existing_invoice
    
    # Create new invoice
    try:
        invoice = Invoice.objects.create(
            invoice_number=invoice_number,
            invoice_date=extracted_data.get('invoice_date'),
            due_date=extracted_data.get('due_date'),
            total_amount=extracted_data.get('total_amount', 0),
            currency=extracted_data.get('currency', 'EUR'),
            vat_percentage=extracted_data.get('vat_percentage'),
            vat_amount=extracted_data.get('vat_amount'),
            taxable_amount=extracted_data.get('taxable_amount'),
            vendor=vendor,
            payment_method=payment_method,
            original_filename=original_filename,
            file_path=file_path,
            file_size=os.path.getsize(file_path) if os.path.exists(file_path) else 0,
            status='extracted',
            needs_manual_review=needs_review,
            extraction_errors=validation_reason if needs_review else '',
            invoice_type=extracted_data.get('invoice_type', 'received'),
            template=template,
            document_file=document_file
        )
        
        # Increment template usage if template was used
        if template:
            template.increment_usage()
        print(f"[SAVE DEBUG] Created new invoice {invoice_number} for {vendor.name}")
        return invoice
        
    except Exception as e:
        print(f"[SAVE DEBUG] Error creating invoice: {str(e)}")
        # Try to find and return existing invoice if creation failed
        existing_invoice = Invoice.objects.filter(
            invoice_number=invoice_number,
            vendor=vendor
        ).first()
        if existing_invoice:
            print(f"[SAVE DEBUG] Found existing invoice {existing_invoice.number}, returning it")
            return existing_invoice
        else:
            raise e


def calculate_confidence(extracted_data):
    """
    Calculate confidence score based on extracted data completeness.
    """
    required_fields = [
        'invoice_number', 'invoice_date', 'due_date', 
        'total_amount', 'vendor_name'
    ]
    
    present_fields = sum(1 for field in required_fields if extracted_data.get(field))
    base_score = (present_fields / len(required_fields)) * 100
    
    # Bonus for additional fields
    additional_fields = ['vat_percentage', 'vendor_vat_id', 'payment_method']
    bonus = sum(5 for field in additional_fields if extracted_data.get(field))
    
    return min(100, base_score + bonus)


def calculate_file_hash(file_path):
    """
    Calculate SHA256 hash of file for duplicate detection.
    """
    hash_sha256 = hashlib.sha256()
    try:
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_sha256.update(chunk)
        return hash_sha256.hexdigest()
    except Exception:
        return ""


@shared_task
def cleanup_failed_extractions():
    """
    Clean up failed extractions and retry if needed.
    """
    failed_invoices = Invoice.objects.filter(
        status='error',
        created_at__lt=timezone.now() - timezone.timedelta(hours=1)
    )
    
    for invoice in failed_invoices:
        try:
            # Reset status and retry
            invoice.status = 'pending'
            invoice.extraction_errors = ''
            invoice.save()
            
            # Queue for retry
            process_single_invoice.delay(
                invoice.file_path,
                invoice.original_filename
            )
            
        except Exception as e:
            print(f"Failed to retry invoice {invoice.id}: {str(e)}")
    
    return f"Retried {failed_invoices.count()} failed extractions"


@shared_task
def cleanup_duplicate_invoices():
    """
    Clean up duplicate invoices by keeping the most recent one.
    """
    from django.db.models import Count
    
    print("[CLEANUP DEBUG] Starting duplicate invoice cleanup...")
    
    # Find invoices with duplicate invoice_number + vendor combinations
    duplicates = Invoice.objects.values('invoice_number', 'vendor').annotate(
        count=Count('id')
    ).filter(count__gt=1)
    
    cleaned_count = 0
    
    for duplicate in duplicates:
        invoice_number = duplicate['invoice_number']
        vendor_id = duplicate['vendor']
        
        # Get all invoices with this combination
        invoices = Invoice.objects.filter(
            invoice_number=invoice_number,
            vendor_id=vendor_id
        ).order_by('-created_at')
        
        # Keep the most recent one, delete the rest
        to_keep = invoices.first()
        to_delete = invoices[1:]
        
        print(f"[CLEANUP DEBUG] Found {len(to_delete)} duplicates for {invoice_number}")
        
        for invoice in to_delete:
            print(f"[CLEANUP DEBUG] Deleting duplicate invoice {invoice.id}")
            invoice.delete()
            cleaned_count += 1
    
    print(f"[CLEANUP DEBUG] Cleanup completed. Removed {cleaned_count} duplicate invoices.")
    return f"Removed {cleaned_count} duplicate invoices"