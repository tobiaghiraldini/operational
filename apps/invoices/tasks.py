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
from apps.documents.storage import document_absolute_path
from apps.tenants.services.company_profile import fetch_tenant_company_profile_for_schema
from apps.invoices.services import (
    validate_vendor_extraction,
    identify_issuer_receiver,
    find_invoice_template,
    get_template_spatial_hints,
    match_invoice_to_template,
)
from apps.documents.ocr import OCRProcessor
from django.contrib.auth import get_user_model
from apps.invoices.currency_lookup import resolve_invoice_currency
from apps.invoices.extraction_validate import (
    EXTRACTION_PROMPT_VERSION,
    extraction_requires_manual_review,
    normalize_and_validate_extraction,
)

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
    classification_hints=None,
):
    """
    Process a single invoice PDF file.
    
    Args:
        file_path: Path to the PDF file
        original_filename: Original filename
        vendor_id: Optional vendor ID
        user_id: Optional user ID (upload attribution / emitted templates)
        document_file_id: Optional DocumentFile ID to link the invoice to
        schema_name: Tenant schema name (for tenant company profile lookup)
        classification_hints: Optional dict (invoice_type, vendor_id, document_kind, …)
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
            schema_name=schema_name,
            classification_hints=classification_hints,
        )


def _process_single_invoice_impl(
    self,
    file_path,
    original_filename,
    vendor_id=None,
    user_id=None,
    document_file_id=None,
    schema_name=None,
    classification_hints=None,
):
    # Try to find DocumentFile if not provided
    document_file = None
    if document_file_id:
        try:
            document_file = DocumentFile.objects.get(pk=document_file_id)
            print(f"[TASK DEBUG] Found DocumentFile: {document_file.filename}")
            resolved = document_absolute_path(document_file)
            if resolved and os.path.isfile(resolved):
                file_path = resolved
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
        
        company_info = fetch_tenant_company_profile_for_schema(schema_name)
        if company_info:
            print(f"[TASK DEBUG] Found tenant company profile: {company_info.display_name}")
        else:
            print(f"[TASK DEBUG] No tenant company profile for schema {schema_name!r}")
        
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

        classification_hints = classification_hints or {}
        extracted_data, validation_notes, field_confidence = normalize_and_validate_extraction(
            extracted_data
        )
        if validation_notes:
            extracted_data["validation_notes"] = validation_notes
        extracted_data["field_confidence"] = field_confidence

        hint_type = classification_hints.get("invoice_type")
        if hint_type in ("received", "emitted"):
            extracted_data["invoice_type"] = hint_type
            print(f"[TASK DEBUG] invoice_type overridden from hints: {hint_type}")

        hint_kind = classification_hints.get("document_kind")
        if hint_kind in dict(Invoice.DOCUMENT_KIND_CHOICES):
            extracted_data["document_kind"] = hint_kind

        needs_from_validation = extraction_requires_manual_review(
            False,
            field_confidence,
            validation_notes,
        )
        if needs_from_validation:
            extracted_data["_force_review"] = True
        
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
                document_file=document_file,
                classification_hints=classification_hints,
            )
            
            # Check if extraction already exists
            conf_score = calculate_confidence(extracted_data, field_confidence)
            extraction, created = InvoiceExtraction.objects.get_or_create(
                invoice=invoice,
                defaults={
                    'raw_text': text_content,
                    'raw_extracted_data': extracted_data,
                    'extraction_method': 'llm',
                    'confidence_score': conf_score,
                    'processed_at': timezone.now(),
                    'field_confidence': field_confidence,
                    'llm_model_name': getattr(settings, 'OLLAMA_MODEL', '')[:120],
                    'prompt_version': EXTRACTION_PROMPT_VERSION,
                    'validated_data': {'validation_notes': validation_notes},
                }
            )
            
            if not created:
                print(f"[TASK DEBUG] Updating existing extraction...")
                extraction.raw_text = text_content
                extraction.raw_extracted_data = extracted_data
                extraction.extraction_method = 'llm'
                extraction.confidence_score = conf_score
                extraction.processed_at = timezone.now()
                extraction.field_confidence = field_confidence
                extraction.llm_model_name = getattr(settings, 'OLLAMA_MODEL', '')[:120]
                extraction.prompt_version = EXTRACTION_PROMPT_VERSION
                extraction.validated_data = {'validation_notes': validation_notes}
                extraction.save()

            user_for_payment = None
            if user_id:
                try:
                    user_for_payment = User.objects.get(pk=user_id)
                except User.DoesNotExist:
                    pass
            from apps.invoices.payment_transaction import sync_invoice_payment_transaction

            sync_invoice_payment_transaction(invoice, created_by=user_for_payment)
        
        print(f"[TASK DEBUG] Processing completed successfully")
        vendor_label = invoice.vendor.name if invoice.vendor else ""
        return {
            'success': True,
            'invoice_id': invoice.id,
            'invoice_number': invoice.invoice_number,
            'vendor_name': vendor_label,
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
                    classification_hints=None,
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


def _parse_llm_json_response(raw_text: str) -> dict:
    """Parse JSON from Ollama response, stripping optional markdown fences."""
    text = (raw_text or "").strip()
    if text.startswith("```"):
        text = text.removeprefix("```json").removeprefix("```").strip()
        if "```" in text:
            text = text.split("```", 1)[0].strip()
    return json.loads(text)


def call_ollama_extraction(invoice_text, company_info=None, spatial_hints=None, template=None):
    """
    Call Ollama API to extract structured data from invoice text.
    
    Args:
        invoice_text: Extracted text from invoice
        company_info: Optional Organization (tenant company profile) for context
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
        aliases = company_info.trading_aliases or []
        alias_str = ", ".join(a for a in aliases if isinstance(a, str)) if aliases else "None"
        company_context = f"""
YOUR COMPANY INFORMATION (for reference - this is the RECEIVER, not the vendor):
- Company Name: {company_info.display_name}
- Legal Name: {company_info.legal_name or 'N/A'}
- VAT ID: {company_info.vat_id}
- Address: {company_info.formatted_address()}
- Alternative Names: {alias_str}

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
- document_kind (string: invoice, credit_note, proforma, other)
- payment_date (YYYY-MM-DD or null) — date payment was received/settled if shown on the document
- paid_in_full (boolean) — true if the invoice is explicitly marked paid in full / settled
- is_paid (boolean) — synonym for paid_in_full if the document only states "paid" without a date
- field_confidence (object mapping each of the above field names to a number between 0 and 1)

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
        extracted_json = _parse_llm_json_response(result['response'])
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


def save_extracted_data(
    extracted_data,
    file_path,
    original_filename,
    vendor_id=None,
    company_info=None,
    template=None,
    user_id=None,
    document_file=None,
    classification_hints=None,
):
    """
    Save extracted data to database models with validation.

    classification_hints: optional upload-time dict stored on the invoice row.
    """
    classification_hints = classification_hints or {}
    force_review = bool(extracted_data.get("_force_review"))

    from apps.invoices.payment_transaction import apply_extraction_payment_fields, coerce_date

    inv_date = coerce_date(extracted_data.get("invoice_date")) or coerce_date(
        extracted_data.get("due_date")
    ) or timezone.localdate()
    due_date = coerce_date(extracted_data.get("due_date")) or inv_date
    _pay = Invoice(invoice_date=inv_date)
    apply_extraction_payment_fields(_pay, extracted_data)

    vendor = None
    if classification_hints.get("vendor_id") is not None:
        try:
            vendor = Vendor.objects.get(pk=int(str(classification_hints["vendor_id"])))
        except (ValueError, Vendor.DoesNotExist):
            vendor = None

    vendor_name = extracted_data.get("vendor_name") or "Unknown Vendor"
    validation_result = validate_vendor_extraction(vendor_name, company_info)
    needs_review = bool(validation_result.get("needs_review")) or force_review
    validation_reason = validation_result.get("reason", "")

    validation_notes = extracted_data.get("validation_notes") or []
    if validation_notes:
        needs_review = True
        extra = "; ".join(str(n) for n in validation_notes)
        validation_reason = f"{validation_reason}; {extra}" if validation_reason else extra

    if needs_review:
        print(f"[SAVE DEBUG] Validation flag: {validation_reason}")

    vendor_vat_id = extracted_data.get("vendor_vat_id") or ""
    vendor_address = extracted_data.get("vendor_address") or ""

    if vendor is None:
        vendor, _created = Vendor.objects.get_or_create(
            name=vendor_name,
            defaults={
                "vat_id": vendor_vat_id,
                "address": vendor_address,
                "country_code": "IT",
            },
        )

    pm_raw = (extracted_data.get("payment_method") or "other").lower().replace(" ", "_")
    if pm_raw not in dict(PaymentMethod.PAYMENT_METHOD_CHOICES):
        pm_raw = "other"
    payment_method, _ = PaymentMethod.objects.get_or_create(
        code=pm_raw,
        defaults={
            "name": dict(PaymentMethod.PAYMENT_METHOD_CHOICES).get(pm_raw, pm_raw.title()),
            "description": "",
        },
    )

    invoice_number = extracted_data.get("invoice_number", "")
    invoice_type = extracted_data.get("invoice_type", "received")

    dk = extracted_data.get("document_kind") or classification_hints.get("document_kind") or "invoice"
    if dk not in dict(Invoice.DOCUMENT_KIND_CHOICES):
        dk = "invoice"

    currency_code = (
        extracted_data.get("currency")
        or classification_hints.get("currency")
        or "EUR"
    )
    currency_obj = resolve_invoice_currency(currency_code)

    existing_invoice = Invoice.objects.filter(
        invoice_number=invoice_number,
        vendor=vendor,
    ).first()

    invoice_status = "review" if needs_review else "extracted"

    if existing_invoice:
        print(f"[SAVE DEBUG] Invoice {invoice_number} from {vendor.name} already exists, updating...")
        existing_invoice.invoice_date = inv_date or existing_invoice.invoice_date
        existing_invoice.due_date = due_date or existing_invoice.due_date
        existing_invoice.total_amount = extracted_data.get("total_amount", existing_invoice.total_amount)
        existing_invoice.currency = currency_obj
        existing_invoice.vat_percentage = extracted_data.get("vat_percentage") or existing_invoice.vat_percentage
        existing_invoice.vat_amount = extracted_data.get("vat_amount") or existing_invoice.vat_amount
        existing_invoice.taxable_amount = extracted_data.get("taxable_amount") or existing_invoice.taxable_amount
        existing_invoice.payment_method = payment_method or existing_invoice.payment_method
        existing_invoice.status = invoice_status
        existing_invoice.needs_manual_review = needs_review
        existing_invoice.extraction_errors = validation_reason if needs_review else ""
        existing_invoice.invoice_type = invoice_type
        existing_invoice.document_kind = dk
        existing_invoice.classification_hints = dict(classification_hints)
        if document_file and not existing_invoice.document_file:
            existing_invoice.document_file = document_file
        if vendor_vat_id and invoice_type == "received":
            existing_invoice.supplier_vat_id = vendor_vat_id
        existing_invoice.payment_date = _pay.payment_date
        existing_invoice.paid_override = _pay.paid_override
        existing_invoice.save()
        return existing_invoice

    supplier_vat = vendor_vat_id if invoice_type == "received" else ""
    customer_vat = (extracted_data.get("customer_vat_id") or "") if invoice_type == "emitted" else ""

    try:
        invoice = Invoice.objects.create(
            invoice_number=invoice_number,
            invoice_date=inv_date,
            due_date=due_date,
            payment_date=_pay.payment_date,
            paid_override=_pay.paid_override,
            total_amount=extracted_data.get("total_amount", 0),
            currency=currency_obj,
            vat_percentage=extracted_data.get("vat_percentage"),
            vat_amount=extracted_data.get("vat_amount"),
            taxable_amount=extracted_data.get("taxable_amount"),
            vendor=vendor,
            payment_method=payment_method,
            original_filename=original_filename,
            file_path=file_path,
            file_size=os.path.getsize(file_path) if os.path.exists(file_path) else 0,
            status=invoice_status,
            needs_manual_review=needs_review,
            extraction_errors=validation_reason if needs_review else "",
            invoice_type=invoice_type,
            template=template,
            document_file=document_file,
            classification_hints=dict(classification_hints),
            document_kind=dk,
            supplier_vat_id=supplier_vat,
            customer_vat_id=customer_vat,
            uploaded_by_id=user_id if user_id else None,
        )

        if template:
            template.increment_usage()
        print(f"[SAVE DEBUG] Created new invoice {invoice_number} for {vendor.name}")
        return invoice

    except Exception as e:
        print(f"[SAVE DEBUG] Error creating invoice: {str(e)}")
        existing_invoice = Invoice.objects.filter(
            invoice_number=invoice_number,
            vendor=vendor,
        ).first()
        if existing_invoice:
            print(f"[SAVE DEBUG] Found existing invoice {existing_invoice.pk}, returning it")
            return existing_invoice
        raise e


def calculate_confidence(extracted_data, field_confidence=None):
    """
    Aggregate confidence (0–100) from field completeness and optional LLM per-field scores.
    """
    field_confidence = field_confidence or extracted_data.get("field_confidence") or {}
    required_fields = [
        "invoice_number",
        "invoice_date",
        "due_date",
        "total_amount",
        "vendor_name",
    ]

    present_fields = sum(1 for field in required_fields if extracted_data.get(field))
    base_score = (present_fields / len(required_fields)) * 100

    additional_fields = ["vat_percentage", "vendor_vat_id", "payment_method"]
    bonus = sum(5 for field in additional_fields if extracted_data.get(field))

    heuristic = min(100.0, base_score + bonus)

    scores = [float(v) for v in field_confidence.values() if isinstance(v, (int, float))]
    if scores:
        llm_avg = sum(scores) / len(scores) * 100.0
        return min(100.0, heuristic * 0.5 + llm_avg * 0.5)

    return min(100.0, heuristic)


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
                invoice.original_filename,
                classification_hints=None,
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