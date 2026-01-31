import os
import shutil
import uvicorn
import time
from fastapi import FastAPI, UploadFile, File, HTTPException, Query
from starlette.responses import FileResponse
from typing import List

# Import services from src package
from src.services.s3_service import LocalS3Service
from src.services.file_service import LocalFileService

app = FastAPI(title="Local RAG Parser API")

# Initialize services
s3_service = LocalS3Service(base_path="local_storage")
file_service = LocalFileService(s3_service=s3_service)

@app.post("/parse")
async def parse_file(
    file: UploadFile = File(...),
    ocr_enabled: bool = Query(True, description="Включить OCR для сканов"),
    max_pages: int = Query(None, description="Лимит страниц для обработки")
):
    """
    Парсит загруженный файл, сохраняет результат локально (как S3) 
    и возвращает ссылки на скачивание.
    """
    start_time = time.time()
    
    # Generate a unique file ID (simple timestamp based for now)
    file_id = str(int(time.time() * 1000))

    try:
        # Process the file using the service layer
        # Wrap single file in a list as the service expects a list
        result = await file_service.process_files(
            files=[file], 
            file_ids=[file_id]
        )
        
        # Return the first result since we only processed one file
        return {
            "initial_link": result["initial_links"][0],
            "parsed_link": result["parsed_links"][0],
            "content_type": result["content_types"][0],
            "parsing_time_sec": round(time.time() - start_time, 2)
        }

    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        # Log error here if logger was available
        raise HTTPException(status_code=500, detail=f"Internal Error: {e}")

@app.get("/download/{path:path}")
async def download_file(path: str):
    """
    Serve files from the local storage (imitating S3 public links).
    """
    file_path = os.path.join(s3_service.base_path, path)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(file_path)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)