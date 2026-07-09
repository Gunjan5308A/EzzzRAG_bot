import json
import time
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_db
from app.models.models import Chatbot, Conversation, CustomContext, Message
from app.schemas.chat import (
    ChatRequest,
    ChatResponse,
    ConversationList,
    ConversationResponse,
    MessageResponse,
    SourceChunk,
)
from app.api.deps import get_chatbot_by_slug
from app.services.rag_service import RAGService

settings = get_settings()

router = APIRouter(tags=["Chat"])


@router.post("/chat/{slug}", response_model=ChatResponse)
async def chat(
    slug: str,
    data: ChatRequest,
    db: AsyncSession = Depends(get_db),
):
    chatbot = await get_chatbot_by_slug(slug, db)
    if not chatbot.is_active:
        raise HTTPException(status_code=400, detail="Chatbot is not active")

    start_time = time.time()

    if data.conversation_id:
        result = await db.execute(
            select(Conversation).where(Conversation.id == data.conversation_id)
        )
        conversation = result.scalar_one_or_none()
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
    else:
        conversation = Conversation(
            chatbot_id=chatbot.id,
            visitor_id=data.visitor_id or str(uuid4()),
            visitor_email=data.visitor_email,
            visitor_name=data.visitor_name,
        )
        db.add(conversation)
        await db.flush()

    user_message = Message(
        conversation_id=conversation.id,
        role="user",
        content=data.message,
    )
    db.add(user_message)

    rag_service = RAGService(db)

    custom_contexts_result = await db.execute(
        select(CustomContext)
        .where(CustomContext.chatbot_id == chatbot.id, CustomContext.is_active == True)
        .order_by(CustomContext.priority.desc())
    )
    custom_contexts = custom_contexts_result.scalars().all()

    system_prompt_parts = []
    if chatbot.system_prompt:
        system_prompt_parts.append(chatbot.system_prompt)
    for ctx in custom_contexts:
        system_prompt_parts.append(f"[{ctx.name}]\n{ctx.content}")

    system_prompt = "\n\n".join(system_prompt_parts) if system_prompt_parts else None

    response_text, sources, tokens_used = await rag_service.generate_response(
        chatbot=chatbot,
        message=data.message,
        conversation_id=str(conversation.id),
        system_prompt=system_prompt,
    )

    response_time_ms = int((time.time() - start_time) * 1000)

    assistant_message = Message(
        conversation_id=conversation.id,
        role="assistant",
        content=response_text,
        sources=json.dumps([s.model_dump() for s in sources]) if sources else None,
        tokens_used=tokens_used,
        response_time_ms=response_time_ms,
    )
    db.add(assistant_message)
    await db.flush()

    return ChatResponse(
        response=response_text,
        conversation_id=str(conversation.id),
        sources=sources,
        tokens_used=tokens_used,
        response_time_ms=response_time_ms,
    )


@router.get("/chat/{slug}/conversations", response_model=ConversationList)
async def list_conversations(
    slug: str,
    page: int = 1,
    page_size: int = 20,
    db: AsyncSession = Depends(get_db),
):
    chatbot = await get_chatbot_by_slug(slug, db)
    from sqlalchemy import func

    count_query = (
        select(func.count()).select_from(Conversation).where(Conversation.chatbot_id == chatbot.id)
    )
    total = (await db.execute(count_query)).scalar()
    pages = max(1, -(-total // page_size))

    query = (
        select(Conversation)
        .where(Conversation.chatbot_id == chatbot.id)
        .order_by(Conversation.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    result = await db.execute(query)
    conversations = result.scalars().all()

    items = []
    for conv in conversations:
        msg_result = await db.execute(
            select(Message).where(Message.conversation_id == conv.id).order_by(Message.created_at)
        )
        messages = msg_result.scalars().all()
        items.append(ConversationResponse(
            **{k: v for k, v in conv.__dict__.items() if k in ConversationResponse.model_fields},
            messages=[MessageResponse.model_validate(m) for m in messages],
        ))

    return ConversationList(items=items, total=total, page=page, pages=pages)