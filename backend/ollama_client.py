from typing import Dict, List, Optional

from .settings import settings


def ping_ollama(embedding_model: Optional[str] = None) -> Dict[str, object]:
    """
    Validate Ollama availability and embedding capability.

    This issues a lightweight embedding call to confirm the model is loaded.
    """
    import ollama  # Imported here to keep import-time light if Ollama is absent.

    model_name = embedding_model or settings.embedding_model
    info = ollama.list()
    _ = ollama.embeddings(model=model_name, prompt="ping")

    models: List[str] = []
    if isinstance(info, dict):
        models = [m.get("name") for m in info.get("models", []) if isinstance(m, dict)]

    return {
        "ok": True,
        "models": models,
        "embedding_model": model_name,
        "host": settings.ollama_host,
    }

