from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None
    visitor_id: Optional[str] = None
    visitor_email: Optional[str] = None
    visitor_name: Optional[str] = None


class SourceChunk(BaseModel):
    content: str
    score: float
    document_id: Optional[str] = None
    filename: Optional[str] = None


class ChatResponse(BaseModel):
    response: str
    conversation_id: str
    sources: list[SourceChunk] = []
    tokens_used: int = 0
    response_time_ms: int = 0


class MessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    role: str
    content: str
    sources: Optional[str] = None
    tokens_used: int
    response_time_ms: int
    created_at: datetime


class ConversationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    visitor_id: Optional[str] = None
    visitor_email: Optional[str] = None
    visitor_name: Optional[str] = None
    messages: list[MessageResponse] = []
    created_at: datetime
    updated_at: datetime


class ConversationList(BaseModel):
    items: list[ConversationResponse]
    total: int
    page: int
    pages: int


class EmbeddingRequest(BaseModel):
    text: str


class EmbeddingResponse(BaseModel):
    embedding: list[float]
    model: str
    dimensions: int