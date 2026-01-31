import os
import datetime
from src.models.models import SourceInfo

def create_source_info(file_path: str) -> SourceInfo:
    """
    Creates a SourceInfo object from a file path.
    """
    file_stats = os.stat(file_path)
    return SourceInfo(
        file_name=os.path.basename(file_path),
        file_path=os.path.abspath(file_path),
        file_size=file_stats.st_size,
        created_at=datetime.datetime.fromtimestamp(file_stats.st_ctime),
        updated_at=datetime.datetime.fromtimestamp(file_stats.st_mtime)
    )
