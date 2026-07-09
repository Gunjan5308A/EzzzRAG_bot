from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ChatbotCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    system_prompt: Optional[str] = None
    model: str = "gpt-4o-mini"
    temperature: float = Field(default=0.7, ge=0, le=2)
    max_tokens: int = Field(default=2000, ge=100, le=8000)
    welcome_message: str = "Hello! How can I help you today?"
    theme_color: str = "#3B82F6"
    widget_position: str = "bottom-right"
    is_public: bool = False


class ChatbotUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    system_prompt: Optional[str] = None
    model: Optional[str] = None
    temperature: Optional[float] = Field(None, ge=0, le=2)
    max_tokens: Optional[int] = Field(None, ge=100, le=8000)
    welcome_message: Optional[str] = None
    theme_color: Optional[str] = None
    widget_position: Optional[str] = None
    is_active: Optional[bool] = None
    is_public: Optional[bool] = None


class ChatbotResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    slug: str
    description: Optional[str] = None
    system_prompt: Optional[str] = None
    model: str
    temperature: float
    max_tokens: int
    is_active: bool
    is_public: bool
    welcome_message: str
    theme_color: str
    widget_position: str
    document_count: int = 0
    context_count: int = 0
    created_at: datetime
    updated_at: datetime


class ChatbotList(BaseModel):
    items: list[ChatbotResponse]
    total: int
    page: int
    pages: int