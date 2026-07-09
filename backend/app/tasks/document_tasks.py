import logging
from app.tasks import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def process_document(self, document_id: str, chatbot_id: str):
    try:
        import asyncio
        from app.core.database import AsyncSessionLocal
        from app.services.document_service import DocumentService

        async def _process():
            async with AsyncSessionLocal() as db:
                service = DocumentService(db)
                await db.commit()

        asyncio.run(_process())
        logger.info(f"Document {document_id} processed successfully")
    except Exception as exc:
        logger.error(f"Error processing document {document_id}: {exc}")
        self.retry(exc=exc)


@celery_app.task
def delete_document_embeddings(document_id: str, chatbot_id: str):
    try:
        import asyncio
        from app.core.database import AsyncSessionLocal
        from app.services.document_service import DocumentService

        async def _delete():
            async with AsyncSessionLocal() as db:
                service = DocumentService(db)
                await service.delete_document(document_id, chatbot_id)
                await db.commit()

        asyncio.run(_delete())
        logger.info(f"Embeddings for document {document_id} deleted")
    except Exception as exc:
        logger.error(f"Error deleting embeddings for document {document_id}: {exc}")


@celery_app.task
def generate_chatbot_report(chatbot_id: str):
    logger.info(f"Generating report for chatbot {chatbot_id}")
    pass