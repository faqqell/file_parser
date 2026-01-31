from typing import List, Dict, Any
class TableSerializer:			
    @staticmethod
    def to_row_kv_text(rows:List[List[str]]) -> str:
        if not rows:
            return ""
        if len(rows) == 1:
            headers = [f"col_{i}" for i in range(len(rows[0]))]
            data_rows = rows
        else:
            headers = rows[0]
            data_rows = rows[1:]
        clean_headers = [h if h else f"col_{i}" for i, h in enumerate(headers)]
        schema_summary = f"Table Schema: Columns: {', '.join(clean_headers)} | Rows: {len(data_rows)}"

        result = [schema_summary]
        for i, row in enumerate(data_rows, 1):
            row_parts = []
            for j, cell in enumerate(row):
                header_name = clean_headers[j] if j<len(headers) else f'col{j}'
                val = str(cell).replace('"', "'")
                row_parts.append(f'{header_name}="{val}"')
            
            row_str = f"row {i}: {{{', '.join(row_parts)}}}"
            result.append(row_str)
            
        return "\n".join(result)
      
      

      