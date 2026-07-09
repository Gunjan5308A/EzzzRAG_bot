from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class DocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    filename: str
    original_filename: str
    file_type: str
    file_size: int
    status: str
    chunk_count: int
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class DocumentUploadResponse(BaseModel):
    id: UUID
    filename: str
    status: str
    message: str


class CustomContextCreate(BaseModel):
    name: str
    content: str
    is_active: bool = True
    priority: int = 0


class CustomContextUpdate(BaseModel):
    name: Optional[str] = None
    content: Optional[str] = None
    is_active: Optional[bool] = None
    priority: Optional[int] = None


class CustomContextResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    content: str
    is_active: bool
    priority: int
    created_at: datetime
    updated_at: datetime