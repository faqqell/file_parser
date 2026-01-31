import os
import shutil
import tempfile
import asyncio
from src.core.detector import get_parser_for_file
from src.services.chunker import Chunker
from src.schemas import ContentType
from typing import List

class LocalFileService:
    def __init__(self, s3_service):
        self.s3 = s3_service
        self.chunker = Chunker(chunk_size=500, chunk_overlap=100)

    async def process_files(self, files: List, file_ids: List[str]):
        
        initial_links = []
        parsed_links = []
        content_types = []

        for file, f_id in zip(files, file_ids):
            # 1. Сохраняем во временный файл (т.к. твоим парсерам нужен путь)
            suffix = os.path.splitext(file.filename)[1].lower()
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                shutil.copyfileobj(file.file, tmp)
                tmp_path = tmp.name

            try:
                # 2. Загружаем оригинал в S3 (имитируем логику того сайта)
                init_key = f"initial/{f_id}{suffix}"
                with open(tmp_path, "rb") as f_data:
                    await self.s3.upload_fileobj(f_data, init_key)

                # 3. ЛОКАЛЬНЫЙ ПАРСИНГ (Твоя магия)
                parser_func = get_parser_for_file(file.filename)
                loop = asyncio.get_event_loop()
                # Запускаем в потоке, чтобы не вешать сервер
                doc = await loop.run_in_executor(None, parser_func, tmp_path)
                
                # Делаем чанки
                doc.chunks = await loop.run_in_executor(
                    None, self.chunker.split_units, doc.content_units, doc.doc_id
                )

                # 4. Сохраняем полный ParsedDocument с чанками в JSON
                parsed_key = f"parsed/{f_id}.json"
                res = await self.s3.upload_file(
                    parsed_key, 
                    doc.model_dump_json(indent=2).encode("utf-8")
                )

                # 6. Собираем ссылки
                initial_links.append(await self.s3.get_url(init_key))
                parsed_links.append(res["url"])
                content_types.append(ContentType.TABLE if suffix in ['.xlsx', '.csv'] else ContentType.TEXT)

            finally:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)

        return {
            "initial_links": initial_links,
            "parsed_links": parsed_links,
            "content_types": content_types
        }