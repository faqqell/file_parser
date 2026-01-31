import os
from src.parsers.excel_parser import parse_excel
from src.parsers.docx_parser import parse_docx
from src.parsers.pdf_parser import parse_pdf
from src.parsers.image_parser import parse_image

def get_parser_for_file(file_path: str):
    ext = file_path.lower().split('.')[-1]
    if ext =='docx':
        return parse_docx
    elif ext in ['xlsx', 'xls']:
        return parse_excel
    elif ext == 'pdf':
        return lambda path: parse_pdf(path, use_ocr=True)
    elif ext in ['png', 'jpg', 'jpeg']:
        return parse_image
    else:       
        raise ValueError(f'{ext} format does not supported yet')