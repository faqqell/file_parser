from pydantic import BaseModel, Field
from typing import List
from enum import Enum

class ContentType(str, Enum):
    TEXT = "text"
    TABLE = "table"

class FileResponse(BaseModel):
    initial_links: List[str] = Field(description="Ссылки на оригиналы в S3")
    parsed_links: List[str] = Field(description="Ссылки на распарсенные Markdown/JSON в S3")
    content_types: List[ContentType] = Field(description="Тип: текст или таблица")