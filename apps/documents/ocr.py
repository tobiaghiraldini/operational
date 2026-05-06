"""
OCR utilities for extracting text from images and PDFs.
Enhanced with layout-aware extraction for better invoice parsing.
"""
import os
from typing import Dict, Optional, List
from pathlib import Path

try:
    import pytesseract
    from PIL import Image
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False

try:
    import PyPDF2
    PYPDF2_AVAILABLE = True
except ImportError:
    PYPDF2_AVAILABLE = False

try:
    import pdfplumber
    PDFPLUMBER_AVAILABLE = True
except ImportError:
    PDFPLUMBER_AVAILABLE = False


class OCRProcessor:
    """
    Process documents to extract text using various methods.
    """
    
    def __init__(self):
        self.tesseract_available = TESSERACT_AVAILABLE
        self.pypdf2_available = PYPDF2_AVAILABLE
        self.pdfplumber_available = PDFPLUMBER_AVAILABLE
    
    def extract_text_from_pdf(self, file_path: str) -> Dict:
        """
        Extract text from PDF using available libraries.
        
        Args:
            file_path: Path to the PDF file
            
        Returns:
            Dictionary with extracted text and metadata
        """
        result = {
            'text': '',
            'method': None,
            'page_count': 0,
            'success': False,
            'error': None
        }
        
        # Try pdfplumber first (better for tables and layout)
        if self.pdfplumber_available:
            try:
                import pdfplumber
                with pdfplumber.open(file_path) as pdf:
                    text_parts = []
                    for page in pdf.pages:
                        text = page.extract_text()
                        if text:
                            text_parts.append(text)
                    
                    result['text'] = '\n\n'.join(text_parts)
                    result['method'] = 'pdfplumber'
                    result['page_count'] = len(pdf.pages)
                    result['success'] = True
                    return result
            except Exception as e:
                result['error'] = f"pdfplumber error: {str(e)}"
        
        # Fallback to PyPDF2
        if self.pypdf2_available and not result['success']:
            try:
                import PyPDF2
                with open(file_path, 'rb') as file:
                    reader = PyPDF2.PdfReader(file)
                    text_parts = []
                    
                    for page in reader.pages:
                        text = page.extract_text()
                        if text:
                            text_parts.append(text)
                    
                    result['text'] = '\n\n'.join(text_parts)
                    result['method'] = 'pypdf2'
                    result['page_count'] = len(reader.pages)
                    result['success'] = True
                    return result
            except Exception as e:
                result['error'] = f"pypdf2 error: {str(e)}"
        
        if not result['success']:
            result['error'] = result['error'] or "No PDF library available"
        
        return result
    
    def extract_text_from_image(self, file_path: str) -> Dict:
        """
        Extract text from image using Tesseract OCR.
        
        Args:
            file_path: Path to the image file
            
        Returns:
            Dictionary with extracted text and metadata
        """
        result = {
            'text': '',
            'method': None,
            'success': False,
            'error': None
        }
        
        if not self.tesseract_available:
            result['error'] = "Tesseract OCR not available"
            return result
        
        try:
            from PIL import Image
            import pytesseract
            
            image = Image.open(file_path)
            text = pytesseract.image_to_string(image)
            
            result['text'] = text
            result['method'] = 'tesseract'
            result['success'] = True
        except Exception as e:
            result['error'] = f"Tesseract error: {str(e)}"
        
        return result
    
    def process_file(self, file_path: str, file_type: Optional[str] = None) -> Dict:
        """
        Process a file and extract text.
        
        Args:
            file_path: Path to the file
            file_type: Optional file type hint
            
        Returns:
            Dictionary with extracted text and metadata
        """
        if not os.path.exists(file_path):
            return {
                'text': '',
                'success': False,
                'error': 'File not found'
            }
        
        # Determine file type from extension if not provided
        if not file_type:
            ext = Path(file_path).suffix.lower()
            if ext == '.pdf':
                file_type = 'pdf'
            elif ext in ['.jpg', '.jpeg', '.png', '.tif', '.tiff', '.bmp']:
                file_type = 'image'
        
        # Process based on file type
        if file_type == 'pdf':
            return self.extract_text_from_pdf(file_path)
        elif file_type == 'image':
            return self.extract_text_from_image(file_path)
        else:
            return {
                'text': '',
                'success': False,
                'error': f'Unsupported file type: {file_type}'
            }
    
    def get_capabilities(self) -> Dict:
        """
        Get information about available OCR capabilities.
        """
        return {
            'tesseract': self.tesseract_available,
            'pypdf2': self.pypdf2_available,
            'pdfplumber': self.pdfplumber_available,
            'supported_formats': self._get_supported_formats()
        }
    
    def _get_supported_formats(self) -> list:
        """Get list of supported file formats."""
        formats = []
        
        if self.pypdf2_available or self.pdfplumber_available:
            formats.append('pdf')
        
        if self.tesseract_available:
            formats.extend(['jpg', 'jpeg', 'png', 'tif', 'tiff', 'bmp'])
        
        return formats
    
    def extract_text_with_layout(self, file_path: str) -> Dict:
        """
        Extract text from PDF with layout information (spatial coordinates).
        This provides better context for identifying invoice sections.
        
        Args:
            file_path: Path to the PDF file
            
        Returns:
            Dictionary with text, layout data, regions, and tables
        """
        result = {
            'text': '',
            'method': None,
            'page_count': 0,
            'success': False,
            'error': None,
            'words': [],
            'chars': [],
            'tables': [],
            'regions': {}
        }
        
        if not self.pdfplumber_available:
            result['error'] = "pdfplumber not available for layout extraction"
            return result
        
        try:
            import pdfplumber
            with pdfplumber.open(file_path) as pdf:
                all_words = []
                all_chars = []
                all_tables = []
                text_parts = []
                page_regions = []
                
                for page_num, page in enumerate(pdf.pages):
                    # Extract basic text
                    page_text = page.extract_text()
                    if page_text:
                        text_parts.append(page_text)
                    
                    # Extract words with coordinates
                    page_words = page.extract_words()
                    if page_words:
                        # Add page number to each word
                        for word in page_words:
                            word['page'] = page_num + 1
                        all_words.extend(page_words)
                    
                    # Extract characters with coordinates
                    page_chars = page.chars
                    if page_chars:
                        for char in page_chars:
                            char['page'] = page_num + 1
                        all_chars.extend(page_chars)
                    
                    # Extract tables
                    page_tables = page.extract_tables()
                    if page_tables:
                        for table in page_tables:
                            all_tables.append({
                                'page': page_num + 1,
                                'data': table
                            })
                    
                    # Identify text regions for this page
                    page_regions.append(self._identify_text_regions(
                        page_words, 
                        page.width, 
                        page.height,
                        page_num + 1
                    ))
                
                result['text'] = '\n\n'.join(text_parts)
                result['words'] = all_words
                result['chars'] = all_chars
                result['tables'] = all_tables
                result['regions'] = {
                    'pages': page_regions,
                    'summary': self._summarize_regions(page_regions)
                }
                result['method'] = 'pdfplumber_layout'
                result['page_count'] = len(pdf.pages)
                result['success'] = True
                
        except Exception as e:
            result['error'] = f"Layout extraction error: {str(e)}"
        
        return result
    
    def _identify_text_regions(self, words: List[Dict], page_width: float, page_height: float, page_num: int) -> Dict:
        """
        Identify text regions based on spatial positioning.
        
        Args:
            words: List of word dictionaries with coordinates
            page_width: Width of the page
            page_height: Height of the page
            page_num: Page number
            
        Returns:
            Dictionary with identified regions
        """
        if not words:
            return {
                'page': page_num,
                'header': [],
                'footer': [],
                'left': [],
                'right': [],
                'center': []
            }
        
        # Define region boundaries
        header_threshold = page_height * 0.3  # Top 30%
        footer_threshold = page_height * 0.7   # Bottom 30%
        left_threshold = page_width * 0.5      # Left 50%
        
        regions = {
            'page': page_num,
            'header': [],
            'footer': [],
            'left': [],
            'right': [],
            'center': []
        }
        
        for word in words:
            top = word.get('top', 0)
            bottom = word.get('bottom', 0)
            left = word.get('x0', 0)
            right = word.get('x1', 0)
            center_y = (top + bottom) / 2
            center_x = (left + right) / 2
            
            # Classify by vertical position
            if center_y < header_threshold:
                regions['header'].append(word)
            elif center_y > footer_threshold:
                regions['footer'].append(word)
            else:
                # Classify by horizontal position (middle section)
                if center_x < left_threshold:
                    regions['left'].append(word)
                else:
                    regions['right'].append(word)
        
        return regions
    
    def _summarize_regions(self, page_regions: List[Dict]) -> Dict:
        """
        Summarize text content from different regions across all pages.
        
        Args:
            page_regions: List of region dictionaries for each page
            
        Returns:
            Summary dictionary with text from each region type
        """
        summary = {
            'header_text': '',
            'footer_text': '',
            'left_text': '',
            'right_text': ''
        }
        
        for page_region in page_regions:
            # Extract text from each region
            for region_type in ['header', 'footer', 'left', 'right']:
                words = page_region.get(region_type, [])
                if words:
                    # Sort words by position (top to bottom, left to right)
                    sorted_words = sorted(words, key=lambda w: (w.get('top', 0), w.get('x0', 0)))
                    text = ' '.join([w.get('text', '') for w in sorted_words if w.get('text')])
                    if text:
                        summary_key = f'{region_type}_text'
                        if summary[summary_key]:
                            summary[summary_key] += '\n' + text
                        else:
                            summary[summary_key] = text
        
        return summary
    
    def get_spatial_regions(self, file_path: str) -> Dict:
        """
        Get text organized by spatial regions (top-left, top-right, etc.).
        Useful for identifying invoice issuer (usually top-left) and receiver (usually top-right).
        
        Args:
            file_path: Path to the PDF file
            
        Returns:
            Dictionary with text organized by spatial regions
        """
        layout_data = self.extract_text_with_layout(file_path)
        
        if not layout_data['success']:
            return {
                'success': False,
                'error': layout_data.get('error', 'Unknown error')
            }
        
        # Extract text from regions
        regions_summary = layout_data.get('regions', {}).get('summary', {})
        
        return {
            'success': True,
            'top_left': regions_summary.get('left_text', '') + '\n' + regions_summary.get('header_text', ''),
            'top_right': regions_summary.get('right_text', '') + '\n' + regions_summary.get('header_text', ''),
            'left_column': regions_summary.get('left_text', ''),
            'right_column': regions_summary.get('right_text', ''),
            'header': regions_summary.get('header_text', ''),
            'footer': regions_summary.get('footer_text', ''),
            'tables': layout_data.get('tables', []),
            'full_text': layout_data.get('text', '')
        }

