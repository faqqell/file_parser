import easyocr
import torch
import numpy as np
from PIL import Image

class OCRService:
    def __init__(self, languages=['ru', 'en']):
        self.use_gpu = torch.cuda.is_available()
        self.reader = easyocr.Reader(languages, gpu=self.use_gpu)
        print(f"OCR Service initialized. GPU: {self.use_gpu}")

    def extract_text(self, pil_image: Image.Image) -> str:
        img_array = np.array(pil_image)
        results = self.reader.readtext(img_array, detail=0)
        return " ".join(results)

_ocr_instance = None

def get_ocr_service():
    global _ocr_instance
    if _ocr_instance is None:
        _ocr_instance = OCRService()
    return _ocr_instance