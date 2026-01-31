from fastapi.testclient import TestClient
from api import app
from src.services.file_service import LocalFileService
from src.services.s3_service import LocalS3Service
import os

client = TestClient(app)

def test_parse_endpoint_no_file():
    response = client.post("/parse")
    assert response.status_code == 422 # Validation error

def test_download_endpoint_404():
    response = client.get("/download/nonexistent.txt")
    assert response.status_code == 404

def test_health_check_ish():
    # We validat that app starts and has endpoints
    assert "/parse" in [route.path for route in app.routes]
    assert "/download/{path:path}" in [route.path for route in app.routes]
