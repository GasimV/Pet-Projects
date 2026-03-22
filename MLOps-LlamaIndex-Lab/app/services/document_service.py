"""
Document management service.

Handles file upload, listing, and deletion — keeps the API layer thin.
"""

import shutil
from pathlib import Path
from typing import List

from fastapi import UploadFile

from app.core.config import settings
from app.core.logging import get_logger
from app.rag.ingestion import SUPPORTED_EXTENSIONS

logger = get_logger(__name__)


async def save_uploaded_file(file: UploadFile) -> Path:
    """
    Persist an uploaded file to the uploads directory.

    Returns the path where the file was saved.
    Raises ValueError for unsupported file types.
    """
    filename = file.filename or "unknown"
    ext = Path(filename).suffix.lower()

    if ext not in SUPPORTED_EXTENSIONS:
        raise ValueError(
            f"Unsupported file type '{ext}'. "
            f"Allowed: {', '.join(sorted(SUPPORTED_EXTENSIONS))}"
        )

    dest = settings.upload_path / filename
    logger.info("Saving uploaded file: %s", dest)

    with dest.open("wb") as f:
        shutil.copyfileobj(file.file, f)

    return dest


def list_uploaded_files() -> List[dict]:
    """Return metadata about every uploaded file."""
    files = []
    for p in sorted(settings.upload_path.iterdir()):
        if p.is_file() and p.suffix.lower() in SUPPORTED_EXTENSIONS:
            files.append({
                "name": p.name,
                "size_bytes": p.stat().st_size,
                "extension": p.suffix.lower(),
            })
    return files


def delete_uploaded_file(filename: str) -> bool:
    """Delete a single uploaded file. Returns True if it existed."""
    target = settings.upload_path / filename
    if target.is_file():
        target.unlink()
        logger.info("Deleted file: %s", target)
        return True
    return False
