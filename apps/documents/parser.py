"""
Document parsing utilities for extracting structured data from text.
"""
import re
from typing import Dict, List, Optional
from datetime import datetime
from decimal import Decimal


class DocumentParser:
    """
    Parse extracted text to identify structured data.
    """
    
    def __init__(self):
        self.patterns = self._initialize_patterns()
    
    def _initialize_patterns(self) -> Dict:
        """Initialize regex patterns for data extraction."""
        return {
            # Date patterns
            'date_iso': re.compile(r'\b(\d{4}[-/]\d{2}[-/]\d{2})\b'),
            'date_eu': re.compile(r'\b(\d{2}[-/]\d{2}[-/]\d{4})\b'),
            'date_us': re.compile(r'\b(\d{2}[-/]\d{2}[-/]\d{2,4})\b'),
            
            # Amount patterns
            'amount_euro': re.compile(r'€\s*(\d+[,.]?\d*[,.]?\d{2})'),
            'amount_dollar': re.compile(r'\$\s*(\d+[,.]?\d*[,.]?\d{2})'),
            'amount_generic': re.compile(r'\b(\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2}))\b'),
            
            # VAT patterns
            'vat_id': re.compile(r'\b(?:VAT|P\.IVA|IVA|VAT\sID)[:\s]*([A-Z]{2}[\dA-Z]{8,12})\b', re.IGNORECASE),
            'vat_rate': re.compile(r'(?:VAT|IVA)\s*(?:@|al)?\s*(\d{1,2})[%\s]', re.IGNORECASE),
            
            # Invoice patterns
            'invoice_number': re.compile(r'(?:Invoice|Fattura|Bill)\s*(?:No|N°|#)[:\s]*([A-Z0-9/-]+)', re.IGNORECASE),
            
            # Email patterns
            'email': re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'),
        }
    
    def extract_dates(self, text: str) -> List[str]:
        """Extract dates from text."""
        dates = []
        
        # Try ISO format first
        for match in self.patterns['date_iso'].finditer(text):
            dates.append(match.group(1))
        
        # Try European format
        for match in self.patterns['date_eu'].finditer(text):
            dates.append(match.group(1))
        
        return dates
    
    def extract_amounts(self, text: str) -> List[Dict]:
        """Extract monetary amounts from text."""
        amounts = []
        
        # Euro amounts
        for match in self.patterns['amount_euro'].finditer(text):
            amount_str = match.group(1).replace(',', '.')
            try:
                amounts.append({
                    'value': float(amount_str),
                    'currency': 'EUR',
                    'raw': match.group(0)
                })
            except ValueError:
                pass
        
        # Dollar amounts
        for match in self.patterns['amount_dollar'].finditer(text):
            amount_str = match.group(1).replace(',', '')
            try:
                amounts.append({
                    'value': float(amount_str),
                    'currency': 'USD',
                    'raw': match.group(0)
                })
            except ValueError:
                pass
        
        return amounts
    
    def extract_vat_info(self, text: str) -> Dict:
        """Extract VAT information from text."""
        vat_info = {
            'vat_ids': [],
            'vat_rates': []
        }
        
        # VAT IDs
        for match in self.patterns['vat_id'].finditer(text):
            vat_info['vat_ids'].append(match.group(1))
        
        # VAT rates
        for match in self.patterns['vat_rate'].finditer(text):
            try:
                rate = int(match.group(1))
                if rate not in vat_info['vat_rates']:
                    vat_info['vat_rates'].append(rate)
            except ValueError:
                pass
        
        return vat_info
    
    def extract_invoice_number(self, text: str) -> Optional[str]:
        """Extract invoice number from text."""
        match = self.patterns['invoice_number'].search(text)
        if match:
            return match.group(1).strip()
        return None
    
    def extract_emails(self, text: str) -> List[str]:
        """Extract email addresses from text."""
        return list(set(self.patterns['email'].findall(text)))
    
    def parse_invoice_data(self, text: str) -> Dict:
        """
        Parse invoice data from extracted text.
        
        Args:
            text: Extracted text from document
            
        Returns:
            Dictionary with parsed invoice data
        """
        data = {
            'invoice_number': None,
            'dates': [],
            'amounts': [],
            'vat_info': {},
            'emails': [],
            'raw_text': text
        }
        
        # Extract all data
        data['invoice_number'] = self.extract_invoice_number(text)
        data['dates'] = self.extract_dates(text)
        data['amounts'] = self.extract_amounts(text)
        data['vat_info'] = self.extract_vat_info(text)
        data['emails'] = self.extract_emails(text)
        
        # Try to identify key amounts
        if data['amounts']:
            # Assume largest amount is total
            amounts_sorted = sorted(data['amounts'], key=lambda x: x['value'], reverse=True)
            data['likely_total'] = amounts_sorted[0]
            
            # Try to identify VAT amount (typically around 20-22% of subtotal)
            if len(amounts_sorted) >= 2 and data['vat_info'].get('vat_rates'):
                for rate in data['vat_info']['vat_rates']:
                    expected_vat = amounts_sorted[0]['value'] * (rate / (100 + rate))
                    for amount in amounts_sorted[1:]:
                        if abs(amount['value'] - expected_vat) / expected_vat < 0.05:  # 5% tolerance
                            data['likely_vat_amount'] = amount
                            data['likely_vat_rate'] = rate
                            break
        
        # Try to identify key dates
        if data['dates']:
            # First date often is invoice date
            data['likely_invoice_date'] = data['dates'][0]
            if len(data['dates']) >= 2:
                # Last date might be due date
                data['likely_due_date'] = data['dates'][-1]
        
        return data
    
    def validate_invoice_data(self, data: Dict) -> Dict:
        """
        Validate parsed invoice data.
        
        Args:
            data: Parsed invoice data
            
        Returns:
            Dictionary with validation results
        """
        validation = {
            'is_valid': True,
            'missing_fields': [],
            'warnings': []
        }
        
        # Check required fields
        if not data.get('invoice_number'):
            validation['missing_fields'].append('invoice_number')
            validation['is_valid'] = False
        
        if not data.get('dates'):
            validation['missing_fields'].append('dates')
            validation['is_valid'] = False
        
        if not data.get('amounts'):
            validation['missing_fields'].append('amounts')
            validation['is_valid'] = False
        
        # Check for warnings
        if not data.get('vat_info', {}).get('vat_ids'):
            validation['warnings'].append('No VAT ID found')
        
        if not data.get('vat_info', {}).get('vat_rates'):
            validation['warnings'].append('No VAT rate found')
        
        if not data.get('emails'):
            validation['warnings'].append('No email addresses found')
        
        return validation

