from typing import Optional

from pydantic import BaseModel, Field


class UploadDocumentResponse(BaseModel):
    document_id: str
    name: str
    path: str


class ChatRequest(BaseModel):
    message: str = Field(..., description="User message to send to the RAG pipeline.")
    conversation_id: Optional[str] = Field(
        None, description="Existing conversation to continue; if absent a new one is created."
    )
    source_name: Optional[str] = Field(
        None, description="Optional source/file name to scope retrieval to."
    )
    source_id: Optional[str] = Field(
        None, description="Optional document_id to scope retrieval to."
    )


class ConversationDeleteResponse(BaseModel):
    deleted: bool


class RenameConversationRequest(BaseModel):
    title: str = Field(..., description="New title for the conversation.")


class DocumentRecord(BaseModel):
    id: str
    name: str
    path: str
    created_at: str


class ConversationRecord(BaseModel):
    id: str
    title: str
    created_at: str


class MessageRecord(BaseModel):
    id: str
    conversation_id: str
    role: str
    content: str
    created_at: str


class Citation(BaseModel):
    source: str
    page: str | int
    document_id: Optional[str] = None
    score: Optional[float] = None
    excerpt: Optional[str] = None

