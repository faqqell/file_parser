from textwrap import indent
import json
import sys
from src.parsers.docx_parser import parse_docx
from src.parsers.excel_parser import parse_excel
from src.core.detector import get_parser_for_file
import os
from src.services.chunker import Chunker
def main():
    if len(sys.argv) < 2:
        print("Ошибка: Укажи путь к файлу!")
        return
    test_file = os.path.expanduser(sys.argv[1])
    chunker = Chunker(chunk_size=1000, chunk_overlap=100)
    try:
        parser_func = get_parser_for_file(test_file)
        doc = parser_func(test_file)
        doc.chunks = chunker.split_units(doc.content_units, doc.doc_id)
        output_path = f"output_{doc.doc_id[:8]}.json"
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(doc.model_dump_json(indent=2))
        print(f"\n--- Результат также сохранен в {output_path} ---")

    except FileNotFoundError:
        print('file not found')
    except Exception as e:
        print('error: ', e)
        
if __name__=='__main__':
    main()