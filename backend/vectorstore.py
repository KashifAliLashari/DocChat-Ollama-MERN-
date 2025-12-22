from pathlib import Path
from typing import Optional

from chromadb import PersistentClient

from .settings import settings


def get_chroma_client(path: Optional[Path] = None) -> PersistentClient:
    """Return a persistent Chroma client, ensuring the storage path exists."""
    target = path or settings.chroma_dir
    target.mkdir(parents=True, exist_ok=True)
    return PersistentClient(path=str(target))

