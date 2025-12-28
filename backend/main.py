import asyncio
import json
import threading
import uuid
from typing import AsyncGenerator, Iterable, List

import ollama
from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from . import schemas
from .db import (
    delete_conversation,
    delete_document,
    ensure_conversation,
    ensure_sqlite_path,
    get_connection,
    init_db,
    insert_document,
    insert_message,
    list_conversations,
    list_documents,
    list_messages,
    rename_conversation,
    update_conversation_title_if_empty,
)
from .ollama_client import ping_ollama
from .rag import get_document_chunks, get_retriever, ingest_pdf
from .settings import settings
from .vectorstore import get_chroma_client

app = FastAPI(
    title="Offline PDF RAG Chatbot Backend",
    version="0.2.0",
)

# CORS for local dev (Vite on 5173)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_db():
    return app.state.db


@app.on_event("startup")
async def startup() -> None:
    """Initialize local resources on startup."""
    ensure_sqlite_path()
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    settings.docs_dir.mkdir(parents=True, exist_ok=True)
    app.state.db = get_connection()
    init_db(app.state.db)
    # Initialize Chroma in a thread to avoid blocking the event loop.
    app.state.chroma_client = await asyncio.to_thread(get_chroma_client)


@app.get("/health")
async def health() -> dict:
    """Basic health and config surface."""
    return {
        "status": "ok",
        "sqlite_path": str(settings.sqlite_path),
        "chroma_dir": str(settings.chroma_dir),
        "embedding_model": settings.embedding_model,
        "ollama_host": settings.ollama_host,
        "ollama_model": settings.ollama_model,
    }


@app.get("/debug/chroma")
async def debug_chroma() -> dict:
    """Debug: show what's in ChromaDB."""
    client = get_chroma_client()
    collection = client.get_or_create_collection(name="documents")
    all_data = collection.get(include=["metadatas"])
    
    items = []
    for i, meta in enumerate(all_data.get("metadatas", [])):
        items.append({
            "id": all_data["ids"][i] if all_data.get("ids") else None,
            "document_id": meta.get("document_id") if meta else None,
            "source": meta.get("source") if meta else None,
            "page": meta.get("page") if meta else None,
        })
    
    unique_doc_ids = list(set(m.get("document_id") for m in all_data.get("metadatas", []) if m))
    unique_sources = list(set(m.get("source") for m in all_data.get("metadatas", []) if m))
    
    return {
        "total_chunks": len(all_data.get("ids", [])),
        "unique_document_ids": unique_doc_ids,
        "unique_sources": unique_sources,
        "sample_items": items[:10],  # First 10 items
    }


async def _ollama_health_stream() -> AsyncGenerator[str, None]:
    """SSE generator for Ollama health and embedding readiness."""
    yield "data: {\"status\": \"initializing\"}\n\n"
    try:
        result = await asyncio.to_thread(ping_ollama, settings.embedding_model)
        payload = json.dumps({"status": "ok", **result})
        yield f"data: {payload}\n\n"
    except Exception as exc:  # noqa: BLE001
        error_payload = json.dumps({"status": "error", "message": str(exc)})
        yield f"data: {error_payload}\n\n"
    yield "data: {\"status\": \"done\"}\n\n"


@app.get("/health/ollama")
async def health_ollama() -> StreamingResponse:
    """
    Stream Ollama health info using SSE (text/event-stream).

    Suitable for frontend streaming consumption; falls back gracefully on errors.
    """
    return StreamingResponse(_ollama_health_stream(), media_type="text/event-stream")


@app.delete("/conversations/{conversation_id}", response_model=schemas.ConversationDeleteResponse)
async def delete_conversation_api(conversation_id: str, db=Depends(get_db)) -> schemas.ConversationDeleteResponse:
    """Delete a conversation and its messages."""
    removed = delete_conversation(db, conversation_id)
    if not removed:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return schemas.ConversationDeleteResponse(deleted=True)


@app.post("/documents/upload", response_model=schemas.UploadDocumentResponse)
async def upload_document(file: UploadFile = File(...), db=Depends(get_db)) -> schemas.UploadDocumentResponse:
    """Upload a PDF, ingest into Chroma via LlamaIndex, and record in SQLite."""
    if file.content_type not in ("application/pdf", "application/octet-stream"):
        raise HTTPException(status_code=400, detail="Only PDF uploads are supported.")

    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    dest_path = settings.docs_dir / file.filename
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    dest_path.write_bytes(file_bytes)

    document_id = str(uuid.uuid4())
    try:
        await asyncio.to_thread(ingest_pdf, dest_path, file.filename, document_id)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {exc}") from exc

    insert_document(db, document_id=document_id, name=file.filename, path=str(dest_path))

    return schemas.UploadDocumentResponse(
        document_id=document_id,
        name=file.filename,
        path=str(dest_path),
    )


def _build_prompt(message: str, context: list) -> str:
    """Build a concise RAG prompt without citations."""
    context_lines = []
    for item in context:
        node = getattr(item, "node", item)
        meta = getattr(node, "metadata", {}) or {}
        src = meta.get("source", "doc")
        page = meta.get("page", "?")
        content = node.get_content().strip() if hasattr(node, "get_content") else ""
        context_lines.append(f"[{src} p{page}] {content}")
    context_block = "\n".join(context_lines) if context_lines else "No context available."
    instructions = (
        "You are an offline PDF assistant. Use only the provided context to answer directly. "
        "Avoid filler like 'the context contains'. If the context does not contain the answer, say you do not have enough information."
    )
    return f"{instructions}\n\nContext:\n{context_block}\n\nUser: {message}\nAnswer:"


def _build_prompt_from_chunks(message: str, chunks: list) -> str:
    """Build a RAG prompt from raw chunk dictionaries (text + metadata)."""
    context_lines = []
    for chunk in chunks:
        text = chunk.get("text", "").strip()
        meta = chunk.get("metadata", {}) or {}
        src = meta.get("source", "doc")
        page = meta.get("page", "?")
        if text:
            context_lines.append(f"[{src} p{page}] {text}")
    context_block = "\n".join(context_lines) if context_lines else "No context available."
    instructions = (
        "You are an offline PDF assistant. Use only the provided context to answer directly. "
        "Avoid filler like 'the context contains'. If the context does not contain the answer, say you do not have enough information."
    )
    return f"{instructions}\n\nContext:\n{context_block}\n\nUser: {message}\nAnswer:"


def _derive_title(message: str, max_len: int = 60) -> str:
    """Derive a lightweight title from the first user message."""
    text = (message or "").strip().replace("\n", " ")
    if len(text) > max_len:
        return text[: max_len - 1].rstrip() + "…"
    return text or "Conversation"


async def _chat_sse_stream(
    user_message: str,
    conversation_id: str,
    db,
    source_name: str | None = None,
    source_id: str | None = None,
) -> AsyncGenerator[str, None]:
    """Stream chat tokens via SSE while persisting messages."""
    print(f"[DEBUG] _chat_sse_stream called with source_id={source_id}, source_name={source_name}")
    context_chunks = []
    
    # If a specific document is attached, retrieve ALL its chunks directly (no vector search)
    # IMPORTANT: Use source_name (filename) as primary filter since document_id is per-chunk, not per-file
    if source_name:
        raw_chunks = await asyncio.to_thread(
            get_document_chunks, document_id=None, source_name=source_name
        )
        print(f"[DEBUG] get_document_chunks by source_name returned {len(raw_chunks)} chunks")
        context_chunks = raw_chunks
    elif source_id:
        # Fallback to document_id (will only return 1 chunk due to bug in data)
        raw_chunks = await asyncio.to_thread(
            get_document_chunks, document_id=source_id, source_name=None
        )
        print(f"[DEBUG] get_document_chunks by source_id returned {len(raw_chunks)} chunks")
        context_chunks = raw_chunks
    
    # If no attached doc or no chunks found, fallback to vector search
    if not context_chunks:
        retriever = get_retriever(top_k=8, document_id=source_id, source_name=source_name)
        context_nodes = await asyncio.to_thread(retriever.retrieve, user_message)
        context_chunks = [
            {"text": n.node.get_content() if hasattr(n, "node") else str(n), "metadata": getattr(getattr(n, "node", n), "metadata", {})}
            for n in context_nodes
        ]

    system_prompt = "You are a helpful assistant that answers using only provided context."
    context_prompt = _build_prompt_from_chunks(user_message, context_chunks)

    # Fetch conversation history for memory
    history_rows = list_messages(db, conversation_id)
    history_messages = []
    for row in history_rows:
        r = dict(row)
        # Skip the current user message (already added to DB before this call)
        if r["role"] == "user" and r["content"] == user_message:
            continue
        history_messages.append({"role": r["role"], "content": r["content"]})
    
    # Limit history to last 10 messages to avoid token overflow
    history_messages = history_messages[-10:]

    # Build full message list: system + history + current context prompt
    messages_to_send = [{"role": "system", "content": system_prompt}]
    messages_to_send.extend(history_messages)
    messages_to_send.append({"role": "user", "content": context_prompt})

    client = ollama.Client(host=settings.ollama_host)
    accumulated: list[str] = []
    queue: asyncio.Queue = asyncio.Queue()
    loop = asyncio.get_running_loop()

    def run_chat() -> None:
        try:
            for chunk in client.chat(
                model=settings.ollama_model,
                messages=messages_to_send,
                stream=True,
            ):
                token = chunk.get("message", {}).get("content", "")
                if token:
                    accumulated.append(token)
                    asyncio.run_coroutine_threadsafe(queue.put(token), loop)
        finally:
            asyncio.run_coroutine_threadsafe(queue.put(None), loop)

    thread = threading.Thread(target=run_chat, daemon=True)
    thread.start()

    # Yield SSE data as tokens arrive
    while True:
        token = await queue.get()
        if token is None:
            break
        payload = json.dumps({"token": token})
        yield f"data: {payload}\n\n"

    # Wait for the Ollama thread to fully complete before saving
    thread.join(timeout=5.0)
    
    assistant_text = "".join(accumulated)
    print(f"[DEBUG] Saving assistant message with {len(assistant_text)} chars")
    insert_message(db, str(uuid.uuid4()), conversation_id, "assistant", assistant_text)


@app.post("/chat/stream")
async def chat_stream(payload: schemas.ChatRequest, db=Depends(get_db)) -> StreamingResponse:
    """
    SSE streaming chat endpoint with RAG retrieval and SQLite persistence.
    - Creates a conversation if none is provided.
    - Stores user and assistant messages.
    """
    conv_id = payload.conversation_id or str(uuid.uuid4())
    ensure_conversation(db, conv_id)
    insert_message(db, str(uuid.uuid4()), conv_id, "user", payload.message)
    update_conversation_title_if_empty(db, conv_id, _derive_title(payload.message))

    async def generator():
        async for chunk in _chat_sse_stream(
            payload.message, conv_id, db, payload.source_name, payload.source_id
        ):
            yield chunk
        yield "data: {\"status\": \"done\"}\n\n"

    return StreamingResponse(generator(), media_type="text/event-stream")


@app.get("/documents", response_model=list[schemas.DocumentRecord])
async def get_documents(db=Depends(get_db)) -> list[schemas.DocumentRecord]:
    """List ingested documents."""
    rows = list_documents(db)
    return [schemas.DocumentRecord(**dict(r)) for r in rows]


@app.delete("/documents/{document_id}")
async def remove_document(document_id: str, db=Depends(get_db)) -> dict:
    """Delete a document by ID."""
    deleted = delete_document(db, document_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Document not found")
    return {"status": "deleted", "document_id": document_id}


@app.get("/conversations", response_model=list[schemas.ConversationRecord])
async def get_conversations(db=Depends(get_db)) -> list[schemas.ConversationRecord]:
    """List conversations."""
    rows = list_conversations(db)
    return [schemas.ConversationRecord(**dict(r)) for r in rows]


@app.patch("/conversations/{conversation_id}")
async def update_conversation(conversation_id: str, payload: schemas.RenameConversationRequest, db=Depends(get_db)) -> dict:
    """Rename a conversation."""
    updated = rename_conversation(db, conversation_id, payload.title)
    if not updated:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return {"status": "updated", "conversation_id": conversation_id, "title": payload.title}


@app.get("/conversations/{conversation_id}/messages", response_model=list[schemas.MessageRecord])
async def get_conversation_messages(conversation_id: str, db=Depends(get_db)) -> list[schemas.MessageRecord]:
    """List messages for a conversation."""
    rows = list_messages(db, conversation_id)
    return [schemas.MessageRecord(**dict(r)) for r in rows]


@app.delete("/conversations/{conversation_id}")
async def remove_conversation(conversation_id: str, db=Depends(get_db)) -> dict:
    """Delete a conversation and its messages."""
    deleted = delete_conversation(db, conversation_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return {"status": "deleted", "conversation_id": conversation_id}

