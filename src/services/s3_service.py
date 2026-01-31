import os
import shutil
from datetime import datetime

class LocalS3Service:
    """
    Заглушка для S3. Сохраняет файлы локально, 
    но имитирует поведение облачного хранилища.
    """
    def __init__(self, base_path: str = "local_storage"):
        self.base_path = base_path
        # Создаем папки для имитации бакета
        os.makedirs(os.path.join(base_path, "initial"), exist_ok=True)
        os.makedirs(os.path.join(base_path, "parsed"), exist_ok=True)

    async def upload_file(self, key: str, data: bytes, content_type: str = None):
        """Имитация загрузки файла в облако"""
        file_path = os.path.join(self.base_path, key)
        # Создаем подпапки, если их нет
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, "wb") as f:
            f.write(data)
            
        # Возвращаем структуру как у реального S3 ответа
        return {
            "status": 200,
            "url": f"http://localhost:8000/download/{key}" # Имитация ссылки
        }

    async def upload_fileobj(self, fileobj, key: str, **kwargs):
        """Имитация загрузки объекта (из памяти/временного файла)"""
        data = fileobj.read()
        if hasattr(fileobj, 'seek'):
            fileobj.seek(0)
        return await self.upload_file(key, data)

    async def get_url(self, key: str):
        """Имитация получения публичной ссылки"""
        return f"http://localhost:8000/download/{key}"