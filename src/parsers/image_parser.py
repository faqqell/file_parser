from PIL import Image
import hashlib
import os
import datetime
import re
from typing import List, Optional
from src.models.models import ContentUnit, ParsedDocument, SourceInfo
from src.services.normalizer import Normalizer
from src.services.ocr_service import get_ocr_service
from src.services.table_serializer import TableSerializer


def parse_table_from_ocr_text(text: str) -> Optional[List[List[str]]]:
    """
    Try to parse table structure from OCR text using heuristics.
    Looks for patterns like aligned columns, repeated delimiters, etc.
    """
    if not text or len(text) < 20:
        return None
    
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    
    # Heuristic: If we have many lines with numbers at the end, it's likely a table
    lines_with_numbers = sum(1 for line in lines if re.search(r'\d+\s*$', line))
    
    if lines_with_numbers < 3:  # Not enough rows to be a table
        return None
    
    # Try to split each line into columns
    # Common patterns: multiple spaces, tabs, or pipe characters
    table_data = []
    
    for line in lines:
        # Try splitting by multiple spaces (2+)
        parts = re.split(r'\s{2,}', line)
        
        # If we got multiple parts, it might be a table row
        if len(parts) >= 2:
            cleaned_parts = [Normalizer.clean_text(p) for p in parts if p.strip()]
            if cleaned_parts:
                table_data.append(cleaned_parts)
    
    # Validate: should have at least 3 rows and consistent column count
    if len(table_data) < 3:
        return None
    
    # Check if column counts are relatively consistent
    col_counts = [len(row) for row in table_data]
    avg_cols = sum(col_counts) / len(col_counts)
    
    # If most rows have similar column count (within ±1), it's likely a table
    consistent_rows = sum(1 for c in col_counts if abs(c - avg_cols) <= 1)
    
    if consistent_rows / len(table_data) >= 0.7:  # 70% consistency
        return table_data
    
    return None


def parse_image(file_path: str) -> ParsedDocument:
    """
    Parse image file with table detection support.
    Uses existing OCR service and heuristic table detection.
    """
    ocr_service = get_ocr_service()
    img = Image.open(file_path)
    
    units: List[ContentUnit] = []
    hasher = hashlib.md5()
    order_index = 0
    warnings = []
    
    # Extract text using existing OCR service
    text = ocr_service.extract_text(img)
    cleaned_text = Normalizer.clean_text(text)
    
    # Try to detect table structure
    table_data = parse_table_from_ocr_text(text)
    
    if table_data:
        # Found table structure - create table unit
        serialized = TableSerializer.to_row_kv_text(table_data)
        hasher.update(serialized.encode('utf-8'))
        
        units.append(ContentUnit(
            type="table",
            text=serialized,
            table={"rows": table_data},
            order_index=order_index,
            order_index_in_page=0
        ))
        
        warnings.append(f"Table detected with {len(table_data)} rows")
    else:
        # No table structure found - extract as plain text
        hasher.update(cleaned_text.encode('utf-8'))
        
        units.append(ContentUnit(
            type="text",
            text=cleaned_text,
            order_index=0,
            order_index_in_page=0
        ))
        
        warnings.append("No table structure detected, extracted as plain text")
    
    doc_id = hasher.hexdigest()
    
    source = SourceInfo(
        file_name=os.path.basename(file_path),
        file_path=os.path.abspath(file_path),
        file_size=os.path.getsize(file_path),
        created_at=datetime.datetime.fromtimestamp(os.path.getctime(file_path)),
        updated_at=datetime.datetime.fromtimestamp(os.path.getmtime(file_path))
    )
    
    return ParsedDocument(
        doc_id=doc_id,
        source=source,
        content_units=units,
        metadata={
            'type': 'image',
            'table_detected': table_data is not None,
            'warnings': warnings
        },
        chunks=[]
    )