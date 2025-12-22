import os
from pathlib import Path


class Settings:
    """Lightweight settings loader for local/offline defaults."""

    def __init__(self) -> None:
        self.data_dir: Path = Path(os.getenv("DATA_DIR", "data"))
        self.docs_dir: Path = Path(
            os.getenv("DOCS_DIR", self.data_dir / "docs")
        )
        self.sqlite_path: Path = Path(
            os.getenv("SQLITE_PATH", self.data_dir / "sqlite" / "app.db")
        )
        self.chroma_dir: Path = Path(
            os.getenv("CHROMA_DIR", self.data_dir / "chroma")
        )
        self.ollama_host: str = os.getenv(
            "OLLAMA_HOST", "http://127.0.0.1:11434"
        )
        # Default to a small model to avoid memory issues; override via env.
        self.ollama_model: str = os.getenv("OLLAMA_MODEL", "qwen2.5:0.5b")
        self.embedding_model: str = os.getenv(
            "OLLAMA_EMBED_MODEL", "nomic-embed-text"
        )


settings = Settings()

