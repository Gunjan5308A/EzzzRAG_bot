import math
import re
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.models.models import Chatbot, Document, CustomContext, User
from app.schemas.chatbot import (
    ChatbotCreate,
    ChatbotList,
    ChatbotResponse,
    ChatbotUpdate,
)
from app.schemas.document import (
    CustomContextCreate,
    CustomContextResponse,
    CustomContextUpdate,
    DocumentResponse,
    DocumentUploadResponse,
)
from app.api.deps import get_current_user, get_user_chatbot
from app.services.document_service import DocumentService

router = APIRouter(prefix="/chatbots", tags=["Chatbots"])


def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_-]+", "-", text)
    text = re.sub(r"^-+|-+$", "", text)
    return text


@router.get("", response_model=ChatbotList)
async def list_chatbots(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=50),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    query = select(Chatbot).where(Chatbot.user_id == current_user.id)
    count_query = select(func.count()).select_from(Chatbot).where(Chatbot.user_id == current_user.id)

    total = (await db.execute(count_query)).scalar()
    pages = math.ceil(total / page_size) if total > 0 else 1

    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    chatbots = result.scalars().all()

    items = []
    for cb in chatbots:
        doc_count = (await db.execute(
            select(func.count()).select_from(Document).where(Document.chatbot_id == cb.id)
        )).scalar()
        ctx_count = (await db.execute(
            select(func.count()).select_from(CustomContext).where(CustomContext.chatbot_id == cb.id)
        )).scalar()
        items.append(ChatbotResponse(
            **{k: v for k, v in cb.__dict__.items() if k in ChatbotResponse.model_fields},
            document_count=doc_count,
            context_count=ctx_count,
        ))

    return ChatbotList(items=items, total=total, page=page, pages=pages)


@router.post("", response_model=ChatbotResponse, status_code=201)
async def create_chatbot(
    data: ChatbotCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    slug = slugify(data.name)
    existing = await db.execute(select(Chatbot).where(Chatbot.slug == slug))
    if existing.scalar_one_or_none():
        import uuid
        slug = f"{slug}-{uuid.uuid4().hex[:8]}"

    chatbot = Chatbot(
        user_id=current_user.id,
        slug=slug,
        **data.model_dump(),
    )
    db.add(chatbot)
    await db.flush()
    await db.refresh(chatbot)
    return ChatbotResponse.model_validate(chatbot)


@router.get("/{chatbot_id}", response_model=ChatbotResponse)
async def get_chatbot(
    chatbot_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    chatbot = await get_user_chatbot(chatbot_id, current_user, db)
    doc_count = (await db.execute(
        select(func.count()).select_from(Document).where(Document.chatbot_id == chatbot.id)
    )).scalar()
    ctx_count = (await db.execute(
        select(func.count()).select_from(CustomContext).where(CustomContext.chatbot_id == chatbot.id)
    )).scalar()
    return ChatbotResponse(
        **{k: v for k, v in chatbot.__dict__.items() if k in ChatbotResponse.model_fields},
        document_count=doc_count,
        context_count=ctx_count,
    )


@router.put("/{chatbot_id}", response_model=ChatbotResponse)
async def update_chatbot(
    chatbot_id: UUID,
    data: ChatbotUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    chatbot = await get_user_chatbot(chatbot_id, current_user, db)
    update_data = data.model_dump(exclude_unset=True)
    if update_data:
        for field, value in update_data.items():
            setattr(chatbot, field, value)
        if "name" in update_data:
            chatbot.slug = slugify(update_data["name"])
        await db.flush()
        await db.refresh(chatbot)
    return ChatbotResponse.model_validate(chatbot)


@router.delete("/{chatbot_id}", status_code=204)
async def delete_chatbot(
    chatbot_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    chatbot = await get_user_chatbot(chatbot_id, current_user, db)
    await db.delete(chatbot)
    return None


# Document endpoints
@router.get("/{chatbot_id}/documents", response_model=list[DocumentResponse])
async def list_documents(
    chatbot_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await get_user_chatbot(chatbot_id, current_user, db)
    result = await db.execute(
        select(Document).where(Document.chatbot_id == chatbot_id).order_by(Document.created_at.desc())
    )
    return [DocumentResponse.model_validate(d) for d in result.scalars().all()]


@router.post("/{chatbot_id}/documents", response_model=DocumentUploadResponse, status_code=201)
async def upload_document(
    chatbot_id: UUID,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await get_user_chatbot(chatbot_id, current_user, db)

    allowed_types = {
        "application/pdf": "pdf",
        "text/plain": "txt",
        "text/markdown": "md",
        "text/csv": "csv",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
    }

    if file.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail=f"File type '{file.content_type}' not supported")

    doc_service = DocumentService(db)
    doc = await doc_service.upload_and_process(
        chatbot_id=chatbot_id,
        file=file,
        file_type=allowed_types[file.content_type],
    )

    return DocumentUploadResponse(
        id=doc.id,
        filename=doc.filename,
        status=doc.status,
        message="Document uploaded and processing started",
    )


@router.delete("/{chatbot_id}/documents/{document_id}", status_code=204)
async def delete_document(
    chatbot_id: UUID,
    document_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await get_user_chatbot(chatbot_id, current_user, db)
    result = await db.execute(
        select(Document).where(Document.id == document_id, Document.chatbot_id == chatbot_id)
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    await db.delete(doc)
    return None


# Custom Context endpoints
@router.get("/{chatbot_id}/contexts", response_model=list[CustomContextResponse])
async def list_contexts(
    chatbot_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await get_user_chatbot(chatbot_id, current_user, db)
    result = await db.execute(
        select(CustomContext)
        .where(CustomContext.chatbot_id == chatbot_id)
        .order_by(CustomContext.priority.desc())
    )
    return [CustomContextResponse.model_validate(c) for c in result.scalars().all()]


@router.post("/{chatbot_id}/contexts", response_model=CustomContextResponse, status_code=201)
async def create_context(
    chatbot_id: UUID,
    data: CustomContextCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await get_user_chatbot(chatbot_id, current_user, db)
    context = CustomContext(chatbot_id=chatbot_id, **data.model_dump())
    db.add(context)
    await db.flush()
    await db.refresh(context)
    return CustomContextResponse.model_validate(context)


@router.put("/{chatbot_id}/contexts/{context_id}", response_model=CustomContextResponse)
async def update_context(
    chatbot_id: UUID,
    context_id: UUID,
    data: CustomContextUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await get_user_chatbot(chatbot_id, current_user, db)
    result = await db.execute(
        select(CustomContext).where(
            CustomContext.id == context_id, CustomContext.chatbot_id == chatbot_id
        )
    )
    context = result.scalar_one_or_none()
    if not context:
        raise HTTPException(status_code=404, detail="Context not found")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(context, field, value)
    await db.flush()
    await db.refresh(context)
    return CustomContextResponse.model_validate(context)


@router.delete("/{chatbot_id}/contexts/{context_id}", status_code=204)
async def delete_context(
    chatbot_id: UUID,
    context_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await get_user_chatbot(chatbot_id, current_user, db)
    result = await db.execute(
        select(CustomContext).where(
            CustomContext.id == context_id, CustomContext.chatbot_id == chatbot_id
        )
    )
    context = result.scalar_one_or_none()
    if not context:
        raise HTTPException(status_code=404, detail="Context not found")
    await db.delete(context)
    return None