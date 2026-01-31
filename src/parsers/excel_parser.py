import pandas as pd
import hashlib, os, datetime, openpyxl
from typing import List, Any    
from src.models.models import ContentUnit, ParsedDocument, SourceInfo
from src.services.table_serializer import TableSerializer
from src.services.normalizer import Normalizer
from src.core.utils import create_source_info

def get_cell_value(sheet, cell):
    """
    Возвращает значение ячейки, учитывая объединенные области.
    Если ячейка объединена, берет значение из основной (верхней левой) ячейки.
    """
    for merged_range in sheet.merged_cells.ranges:
        if cell.coordinate in merged_range:
            return sheet.cell(merged_range.min_row, merged_range.min_col).value
    return cell.value
def parse_excel(file_path:str) -> ParsedDocument:
    wb = openpyxl.load_workbook(file_path, data_only=True)
    excel_data = pd.read_excel(file_path, sheet_name=None)
    content_hasher = hashlib.md5()
    units: List[ContentUnit] = []
    author = None
    try:
        author = wb.properties.creator
    except: 
        pass
    all_sheet_names = wb.sheetnames
    order_count = 0
    
    for sheet_name in all_sheet_names:
        sheet = wb[sheet_name]
        rows_data = []
        for row in sheet.iter_rows():
            row_values = []
            for cell in row:
                val = get_cell_value(sheet, cell)
                row_values.append(Normalizer.clean_text(str(val)) if val is not None else "")
            if any(row_values):
                rows_data.append(row_values)
        if not rows_data:
            continue
            
        headers = rows_data[0] if rows_data else []
        serialized_text = TableSerializer.to_row_kv_text(rows_data)
        content_hasher.update(serialized_text.encode('utf-8'))
        units.append(ContentUnit(
			type='table', 
            text=serialized_text,
			table={
       				'sheet_name': sheet_name,
					'headers': headers,
           			'rows': rows_data},
			sheet_name = sheet_name,
			section_title=sheet_name,
			order_index = order_count,
            order_index_in_page=0
		))
        order_count+=1
    
    doc_id = content_hasher.hexdigest()
    props = wb.properties
    source = create_source_info(file_path)
    
    metadata = {
		'language': None,
		'author': author,   
		'title': props.title,
		'pages_count': len(excel_data),
		'sheet_names': all_sheet_names,
		"warnings": []
	}
    
    return ParsedDocument(
		doc_id = doc_id, 
		source = source,
		content_units = units,
		metadata = metadata,
  		chunks = []
	)
