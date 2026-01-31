import os
import re
import hashlib
import datetime
from typing import List, Tuple
import pdfplumber
from langdetect import detect
from src.models.models import ContentUnit, ParsedDocument, SourceInfo
from src.services.normalizer import Normalizer
from src.services.ocr_service import get_ocr_service
from src.core.utils import create_source_info
from src.services.table_serializer import TableSerializer

OCR_FIXES = {
    "morelless": "more/less", "rvn": "run", "eqwal": "equal", 
    "yow": "you", "vvith": "with", "vvas": "was", "tlie": "the",
    "n i m p r o vement": "improvement", "rvnning": "running"
}

FIX_RE = re.compile(r'\b(' + '|'.join(map(re.escape, OCR_FIXES.keys())) + r')\b', re.IGNORECASE)
SPACING_RE = re.compile(r'(?<=\b\w)\s+(?=\w\b)')

def super_clean_text(text: str) -> str:
    if not text: return ""
    text = SPACING_RE.sub('', text)
    text = FIX_RE.sub(lambda m: OCR_FIXES.get(m.group(0).lower(), m.group(0)), text)
    return " ".join(text.split()).strip()


def is_prose_header(row: List[str], threshold: int = 50) -> bool:
    """
    Detect if a table row is likely prose rather than a proper header.
    Returns True if average cell length exceeds threshold.
    """
    if not row:
        return False
    
    non_empty_cells = [cell for cell in row if cell.strip()]
    if not non_empty_cells:
        return False
    
    avg_length = sum(len(cell) for cell in non_empty_cells) / len(non_empty_cells)
    return avg_length > threshold


def forward_fill_table(table_data: List[List[str]]) -> List[List[str]]:
    """
    Forward-fill empty cells in a table by copying values from the previous row
    in the same column. Useful for category/trend columns.
    """
    if not table_data or len(table_data) < 2:
        return table_data
    
    filled_table = [table_data[0][:]]  # Copy first row as-is
    
    for row_idx in range(1, len(table_data)):
        new_row = []
        for col_idx, cell in enumerate(table_data[row_idx]):
            if not cell.strip() and col_idx < len(filled_table[row_idx - 1]):
                # Copy from previous row if current cell is empty
                new_row.append(filled_table[row_idx - 1][col_idx])
            else:
                new_row.append(cell)
        filled_table.append(new_row)
    
    return filled_table


def extract_text_excluding_tables(page, table_bboxes: List[Tuple]) -> str:
    """
    Extract text from page while excluding content that overlaps with tables.
    """
    if not table_bboxes:
        return page.extract_text() or ""
    
    def not_inside_tables(obj):
        """Check if a text object is outside all table bboxes."""
        obj_x = (obj['x0'] + obj['x1']) / 2
        obj_y = (obj['top'] + obj['bottom']) / 2
        
        for bbox in table_bboxes:
            tx0, ttop, tx1, tbottom = bbox
            
            # Add small margin to avoid edge cases
            margin = 5
            if (tx0 - margin <= obj_x <= tx1 + margin) and (ttop - margin <= obj_y <= tbottom + margin):
                return False
        return True
    
    filtered_page = page.filter(not_inside_tables)
    return filtered_page.extract_text() or ""


def parse_pdf(file_path: str, use_ocr: bool = True) -> ParsedDocument:
    units: List[ContentUnit] = []
    hasher = hashlib.md5()
    order_index = 0
    warnings = []
    full_text_for_lang = ""
    ocr_actually_used = False
    file_stats = os.stat(file_path)
    
    with pdfplumber.open(file_path) as pdf:
        pages_count = len(pdf.pages)
        pdf_meta = pdf.metadata
        
        for page_number, page in enumerate(pdf.pages, start=1):
            found_tables = page.find_tables()
            table_bboxes = []
            order_index_in_page = 0
            
            # Process tables first
            if found_tables:
                for table in found_tables:
                    table_bboxes.append(table.bbox)
                    table_data = table.extract()
                    cleaned_table = []
                    
                    if table_data:
                        for row in table_data:
                            cleaned_row = [super_clean_text(Normalizer.clean_text(str(cell) if cell else "")) for cell in row]
                            if any(cleaned_row):
                                cleaned_table.append(cleaned_row)
                    
                    if cleaned_table:
                        # Apply forward-fill for empty cells
                        cleaned_table = forward_fill_table(cleaned_table)
                        
                        # Check if first row is prose (not a proper header)
                        if is_prose_header(cleaned_table[0]):
                            # Treat all rows as data, use generic column names
                            warnings.append(f"Page {page_number}: Table header detected as prose, using generic column names")
                        
                        serialized = TableSerializer.to_row_kv_text(cleaned_table)
                        hasher.update(serialized.encode("utf-8"))
                        units.append(ContentUnit(
                            type="table",
                            text=serialized,
                            table={"rows": cleaned_table},
                            page_number=page_number,
                            bbox=list(table.bbox),
                            order_index=order_index,
                            order_index_in_page=order_index_in_page
                        ))
                        order_index += 1
                        order_index_in_page += 1

            text = extract_text_excluding_tables(page, table_bboxes)
            cleaned_text = Normalizer.clean_text(text)
            
            if len(cleaned_text) < 50 and use_ocr:
                try:
                    im = page.to_image(resolution=300).original
                    ocr_text = get_ocr_service().extract_text(im)
                    cleaned_text = Normalizer.clean_text(ocr_text)
                    if cleaned_text:
                        ocr_actually_used = True
                except Exception as e:
                    warnings.append(f"OCR failed on page {page_number}: {e}")
            cleaned_text = Normalizer.dehyphenate(cleaned_text)
            cleaned_text = super_clean_text(cleaned_text)
            if cleaned_text:
                if len(full_text_for_lang) < 1000:
                    full_text_for_lang += cleaned_text + " "
                blocks = [b.strip() for b in cleaned_text.split('\n\n') if b.strip()]
                
                for block in blocks:
                    section_title = None
                    if len(block) < 100 and not block.endswith('.'):
                        section_title = block
                        
                    hasher.update(block.encode('utf-8'))
                    units.append(ContentUnit(
                        type="text",
                        text=block,
                        page_number=page_number,
                        section_title=section_title,
                        order_index=order_index,
                        order_index_in_page=order_index_in_page
                    ))
                    order_index += 1
                    order_index_in_page += 1

    # Detect language
    lang = None
    if full_text_for_lang.strip():
        try:
            lang = detect(full_text_for_lang)
        except:
            pass
            
    if ocr_actually_used:
        warnings.append("Document was processed using OCR fallback.")
    
    doc_id = hasher.hexdigest()
    source = create_source_info(file_path)
    
    metadata = {
        'language': lang, 
        'author': pdf_meta.get('Author') if pdf_meta else None,
        'title': pdf_meta.get('Title') if pdf_meta else None,
        'pages_count': pages_count,
        'warnings': warnings,
        'ocr_enabled': use_ocr
    }

    return ParsedDocument(
        doc_id=doc_id,
        source=source,
        content_units=units,
        metadata=metadata,
        chunks=[]
    )
