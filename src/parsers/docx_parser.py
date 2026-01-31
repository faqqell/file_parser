import hashlib
import os
import datetime
from docx import Document
from docx.text.paragraph import Paragraph
from docx.table import Table
from docx.oxml.table import CT_Tbl
from docx.oxml.text.paragraph import CT_P
from langdetect import detect
from src.models.models import ContentUnit, ParsedDocument, SourceInfo
from src.services.table_serializer import TableSerializer
from src.services.normalizer import Normalizer

def parse_docx(file_path: str) -> ParsedDocument:
    doc = Document(file_path)
    units: list[ContentUnit] = []
    content_hasher = hashlib.md5()
    order_index = 0
    full_text_for_lang = ""

    def iter_block_items(parent):
        parent_elm = parent.element.body
        for child in parent_elm.iterchildren():
            if isinstance(child, CT_P):
                yield Paragraph(child, parent)
            elif isinstance(child, CT_Tbl):
                yield Table(child, parent)

    for block in iter_block_items(doc):
        if isinstance(block, Paragraph):
            cleaned_text = Normalizer.clean_text(block.text)
            if not cleaned_text:
                continue
            
            if len(full_text_for_lang) < 1000:
                full_text_for_lang += cleaned_text + " "
            
            unit_type = "text"
            if block.style.name.startswith('Heading'):
                unit_type = "heading" 

            content_hasher.update(cleaned_text.encode("utf-8"))
            units.append(ContentUnit(
                type=unit_type,
                text=cleaned_text,
                table=None,
                section_title=block.style.name if unit_type == "heading" else None,
                order_index=order_index,
                order_index_in_page=0
            ))
            order_index += 1

        elif isinstance(block, Table):
            table_data = []
            for row in block.rows:
                row_cells = []
                prev_tc = None
                for cell in row.cells:
                    if cell._tc == prev_tc:
                        row_cells.append("") 
                    else:
                        row_cells.append(Normalizer.clean_text(cell.text))
                    prev_tc = cell._tc
                table_data.append(row_cells)
            
            serialized_text = TableSerializer.to_row_kv_text(table_data)
            content_hasher.update(serialized_text.encode("utf-8"))
            
            units.append(ContentUnit(
                type="table",
                text=serialized_text,
                table={"rows": table_data},
                order_index=order_index,
                order_index_in_page=0 
            ))
            order_index += 1

    detected_lang = "unknown"
    try:
        if full_text_for_lang.strip():
            detected_lang = detect(full_text_for_lang)
    except:
        pass

    doc_id = content_hasher.hexdigest()

    source = SourceInfo(
            file_name=os.path.basename(file_path),
            file_path=os.path.abspath(file_path),
            file_size=os.path.getsize(file_path), 
            created_at=datetime.datetime.fromtimestamp(os.path.getctime(file_path)),
            updated_at=datetime.datetime.fromtimestamp(os.path.getmtime(file_path))
        )
    
    metadata = {
        "language": detected_lang,
        "author": doc.core_properties.author or None,
        "title": doc.core_properties.title or None,
        "pages_count": None,
        "warnings": [],
    }
    
    return ParsedDocument(
        doc_id=doc_id,
        source=source,
        content_units=units,
        metadata=metadata,
        chunks=[]
    )