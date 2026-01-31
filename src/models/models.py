from datetime import datetime
from pydantic import BaseModel, Field
from typing import Optional, Dict, List, Any, Union

class Chunk(BaseModel):
    chunk_id: str
    doc_id: str
    text: str
    metadata: Dict[str, Any]

class ContentUnit(BaseModel):
    type:str = Field(..., description="text | table | image | figure")
    text: Optional[str] = None
    table: Optional[Dict[str, Any]] = None 
    #provenance
    page_number: Optional[int] = None
    sheet_name: Optional[str] = None
    bbox: Optional[List[float]] = None
    #hierarchy 
    section_title: Optional[str] = None
    order_index:int = Field(..., description='Block order in document')
    order_index_in_page: Optional[int] = Field(None, description='Block order in page')

class SourceInfo(BaseModel):
    file_name: str
    file_path: str
    file_size: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

class ParsedDocument(BaseModel):
    doc_id: str
    source: SourceInfo
    content_units: List[ContentUnit] 
    metadata: Dict[str, Any] = {
        'language': None,
        'author': None,
        'title': None, 
        'pages_count': None,
        'ocr_used': False,
        'warnings': []
    }
    chunks: List[Chunk] = []
    


    

 