from pathlib import Path
from typing import List, Optional
import uuid

import fitz  # PyMuPDF
from llama_index.core import Document, StorageContext, VectorStoreIndex
from llama_index.core.vector_stores.types import MetadataFilter, MetadataFilters
from llama_index.core.node_parser import SimpleNodeParser
from llama_index.embeddings.ollama import OllamaEmbedding
from llama_index.vector_stores.chroma import ChromaVectorStore

from .settings import settings
from .vectorstore import get_chroma_client


def get_embedding(model: Optional[str] = None) -> OllamaEmbedding:
    """Return Ollama embedding model configured for local host."""
    return OllamaEmbedding(
        model_name=model or settings.embedding_model,
        base_url=settings.ollama_host,
    )


def _chroma_vector_store(collection_name: str = "documents") -> ChromaVectorStore:
    """Create or reuse a Chroma collection wrapped for LlamaIndex."""
    client = get_chroma_client()
    collection = client.get_or_create_collection(name=collection_name)
    return ChromaVectorStore(chroma_collection=collection)


def _parse_pdf(path: Path, name: str, document_id: str) -> List[Document]:
    """Extract per-page documents with metadata for citations."""
    doc = fitz.open(path)
    documents: List[Document] = []
    for page in doc:
        page_text = page.get_text("text")
        text = f"Source: {name}\nPage: {page.number + 1}\n{page_text}"
        if not text.strip():
            continue
        documents.append(
            Document(
                text=text,
                metadata={
                    "document_id": document_id,
                    "source": name,
                    "page": page.number + 1,
                    "path": str(path),
                },
            )
        )
    doc.close()
    return documents


def ingest_pdf(path: Path, name: Optional[str] = None, document_id: Optional[str] = None) -> str:
    """Parse, chunk, and upsert a PDF into Chroma via LlamaIndex."""
    display_name = name or path.name
    doc_id = document_id or str(uuid.uuid4())
    documents = _parse_pdf(path, display_name, doc_id)
    if not documents:
        raise ValueError("No extractable text found in PDF.")

    parser = SimpleNodeParser.from_defaults()
    nodes = parser.get_nodes_from_documents(documents)

    vector_store = _chroma_vector_store()
    storage_context = StorageContext.from_defaults(vector_store=vector_store)
    index = VectorStoreIndex.from_documents(
        documents=[],
        storage_context=storage_context,
        embed_model=get_embedding(),
    )
    index.insert_nodes(nodes)

    return doc_id


def get_retriever(top_k: int = 4, document_id: str | None = None, source_name: str | None = None):
    """Build a retriever over the existing vector store with optional metadata filters."""
    vector_store = _chroma_vector_store()
    storage_context = StorageContext.from_defaults(vector_store=vector_store)
    index = VectorStoreIndex.from_vector_store(
        vector_store=vector_store,
        storage_context=storage_context,
        embed_model=get_embedding(),
    )
    filters = []
    if document_id:
        filters.append(MetadataFilter(key="document_id", value=document_id))
    elif source_name:
        filters.append(MetadataFilter(key="source", value=source_name))
    metadata_filters = MetadataFilters(filters=filters) if filters else None
    return index.as_retriever(similarity_top_k=top_k, filters=metadata_filters)


def get_document_chunks(document_id: str | None = None, source_name: str | None = None) -> list:
    """Retrieve all chunks for a specific document directly from ChromaDB (no vector search)."""
    client = get_chroma_client()
    collection = client.get_or_create_collection(name="documents")
    
    where_filter = None
    if document_id:
        where_filter = {"document_id": document_id}
    elif source_name:
        where_filter = {"source": source_name}
    
    if not where_filter:
        return []
    
    results = collection.get(where=where_filter, include=["documents", "metadatas"])
    
    chunks = []
    if results and results.get("documents"):
        for i, doc_text in enumerate(results["documents"]):
            meta = results["metadatas"][i] if results.get("metadatas") else {}
            chunks.append({
                "text": doc_text,
                "metadata": meta,
            })
    return chunks

