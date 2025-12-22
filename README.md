# Offline PDF RAG Chatbot (Backend Scaffold)

This project scaffolds the offline backend described in `RULE.md`, featuring FastAPI, SQLite, ChromaDB, Ollama embeddings, and SSE for streaming health checks.

## Quickstart
1. Create a virtualenv (Python 3.11+ recommended) and install deps:
   - `python -m venv .venv`
   - `.venv\\Scripts\\activate` (Windows) or `source .venv/bin/activate` (Unix)
   - `pip install -r requirements.txt`
2. Run the API:
   - `uvicorn backend.main:app --reload`

## Endpoints
- `GET /health` — basic health/config info.
- `GET /health/ollama` — SSE stream to validate Ollama and embedding model readiness.
- `POST /documents/upload` — upload a PDF (multipart), ingest into Chroma via LlamaIndex, and record in SQLite.
- `POST /chat/stream` — SSE chat with RAG retrieval and SQLite persistence (send JSON `{"message": "...", "conversation_id": "optional"}`).
- `GET /documents` — list ingested documents.
- `GET /conversations` — list conversations.
- `GET /conversations/{id}/messages` — list messages in a conversation.

## Configuration (env vars)
- `DATA_DIR` — base data directory (default: `data`).
- `SQLITE_PATH` — SQLite file path (default: `<DATA_DIR>/sqlite/app.db`).
- `CHROMA_DIR` — Chroma persistence path (default: `<DATA_DIR>/chroma`).
- `OLLAMA_HOST` — Ollama host URL (default: `http://127.0.0.1:11434`).
- `OLLAMA_MODEL` — LLM used for chat (default: `qwen2.5:0.5b` to minimize memory).
- `OLLAMA_EMBED_MODEL` — embedding model to probe (default: `nomic-embed-text`).
- `DOCS_DIR` — where uploaded PDFs are stored (default: `<DATA_DIR>/docs`).
- Frontend: `VITE_API_BASE` — backend URL (default: `http://127.0.0.1:8000`).
- See `env.example` for defaults; copy to `.env` as needed.

## Notes
- Chroma and SQLite paths are created on startup.
- The Ollama health endpoint performs a lightweight embedding call; ensure the model is pulled locally.
- Upload endpoint expects PDFs; ingestion parses with PyMuPDF and stores metadata for citations.
- Chat SSE stream emits a first event with `context` (citations) followed by token events and a final `status: done`.

## Scripts
- `scripts/ollama-start.ps1` — start Ollama serve.
- `scripts/dev-backend.ps1` — run uvicorn with defaults (requires venv activated once).
- `scripts/dev-frontend.ps1` — run Vite dev server on 5173.

