import json
import logging
from typing import Optional
from uuid import uuid4

from openai import AsyncOpenAI
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.models import Chatbot, DocumentChunk
from app.schemas.chat import SourceChunk

settings = get_settings()

logger = logging.getLogger(__name__)

client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)


class RAGService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_embedding(self, text: str) -> list[float]:
        response = await client.embeddings.create(
            model=settings.OPENAI_EMBEDDING_MODEL,
            input=text,
        )
        return response.data[0].embedding

    async def search_similar_chunks(
        self, chatbot_id: str, query_embedding: list[float], top_k: int = 5
    ) -> list[dict]:
        if settings.PINECONE_API_KEY:
            return await self._search_pinecone(chatbot_id, query_embedding, top_k)
        else:
            return await self._search_pgvector(chatbot_id, query_embedding, top_k)

    async def _search_pinecone(
        self, chatbot_id: str, query_embedding: list[float], top_k: int
    ) -> list[dict]:
        from pinecone import Pinecone

        pc = Pinecone(api_key=settings.PINECONE_API_KEY)
        index = pc.Index(settings.PINECONE_INDEX_NAME)

        results = index.query(
            vector=query_embedding,
            top_k=top_k,
            namespace=str(chatbot_id),
            include_metadata=True,
        )

        chunks = []
        for match in results.matches:
            chunks.append({
                "content": match.metadata.get("content", ""),
                "score": match.score,
                "document_id": match.metadata.get("document_id"),
                "filename": match.metadata.get("filename"),
            })
        return chunks

    async def _search_pgvector(
        self, chatbot_id: str, query_embedding: list[float], top_k: int
    ) -> list[dict]:
        try:
            from pgvector.sqlalchemy import Vector
            import numpy as np

            query = (
                select(
                    DocumentChunk,
                    DocumentChunk.content,
                    (DocumentChunk.embedding.cosine_distance(query_embedding)).label("distance"),
                )
                .join(DocumentChunk.document)
                .where(DocumentChunk.document.has(chatbot_id=chatbot_id))
                .order_by("distance")
                .limit(top_k)
            )
            result = await self.db.execute(query)
            rows = result.all()

            return [
                {
                    "content": row.content,
                    "score": 1 - row.distance,
                    "document_id": str(row.DocumentChunk.document_id),
                    "filename": None,
                }
                for row in rows
            ]
        except Exception as e:
            logger.warning(f"pgvector search failed: {e}")
            return []

    async def generate_response(
        self,
        chatbot: Chatbot,
        message: str,
        conversation_id: str,
        system_prompt: Optional[str] = None,
    ) -> tuple[str, list[SourceChunk], int]:
        query_embedding = await self.get_embedding(message)

        relevant_chunks = await self.search_similar_chunks(
            str(chatbot.id), query_embedding, top_k=5
        )

        context_parts = []
        sources = []
        for chunk in relevant_chunks:
            if chunk["score"] > 0.3:
                context_parts.append(chunk["content"])
                sources.append(SourceChunk(
                    content=chunk["content"][:200],
                    score=round(chunk["score"], 4),
                    document_id=chunk.get("document_id"),
                    filename=chunk.get("filename"),
                ))

        context_text = "\n\n---\n\n".join(context_parts) if context_parts else ""

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        if context_text:
            messages.append({
                "role": "system",
                "content": f"Use the following context to answer the question:\n\n{context_text}",
            })

        messages.append({"role": "user", "content": message})

        response = await client.chat.completions.create(
            model=chatbot.model,
            messages=messages,
            temperature=chatbot.temperature,
            max_tokens=chatbot.max_tokens,
        )

        return response.choices[0].message.content, sources, response.usage.total_tokens