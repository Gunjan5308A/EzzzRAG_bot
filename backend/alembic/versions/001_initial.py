"""Initial migration

Revision ID: 001
Revises:
Create Date: 2024-01-01 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "users",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(255), unique=True, nullable=False, index=True),
        sa.Column("name", sa.String(255), nullable=True),
        sa.Column("hashed_password", sa.String(255), nullable=True),
        sa.Column("avatar_url", sa.Text, nullable=True),
        sa.Column("oauth_provider", sa.String(50), nullable=True),
        sa.Column("oauth_id", sa.String(255), nullable=True),
        sa.Column("is_active", sa.Boolean, default=True),
        sa.Column("is_verified", sa.Boolean, default=False),
        sa.Column("is_pro", sa.Boolean, default=False),
        sa.Column("credits", sa.Integer, default=100),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
        ),
    )

    op.create_table(
        "chatbots",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(255), unique=True, nullable=False, index=True),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("system_prompt", sa.Text, nullable=True),
        sa.Column("model", sa.String(50), default="gpt-4o-mini"),
        sa.Column("temperature", sa.Float, default=0.7),
        sa.Column("max_tokens", sa.Integer, default=2000),
        sa.Column("is_active", sa.Boolean, default=True),
        sa.Column("is_public", sa.Boolean, default=False),
        sa.Column("welcome_message", sa.String(500), default="Hello! How can I help you today?"),
        sa.Column("theme_color", sa.String(7), default="#3B82F6"),
        sa.Column("widget_position", sa.String(20), default="bottom-right"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
        ),
    )

    op.create_table(
        "documents",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "chatbot_id",
            UUID(as_uuid=True),
            sa.ForeignKey("chatbots.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("filename", sa.String(500), nullable=False),
        sa.Column("original_filename", sa.String(500), nullable=False),
        sa.Column("file_type", sa.String(50), nullable=False),
        sa.Column("file_size", sa.Integer, nullable=False),
        sa.Column("s3_key", sa.Text, nullable=True),
        sa.Column("status", sa.String(20), default="pending"),
        sa.Column("chunk_count", sa.Integer, default=0),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
        ),
    )

    op.create_table(
        "document_chunks",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "document_id",
            UUID(as_uuid=True),
            sa.ForeignKey("documents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("chunk_index", sa.Integer, nullable=False),
        sa.Column("token_count", sa.Integer, nullable=False),
        sa.Column("pinecone_id", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "custom_contexts",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "chatbot_id",
            UUID(as_uuid=True),
            sa.ForeignKey("chatbots.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("is_active", sa.Boolean, default=True),
        sa.Column("priority", sa.Integer, default=0),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
        ),
    )

    op.create_table(
        "conversations",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "chatbot_id",
            UUID(as_uuid=True),
            sa.ForeignKey("chatbots.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("visitor_id", sa.String(255), nullable=True),
        sa.Column("visitor_email", sa.String(255), nullable=True),
        sa.Column("visitor_name", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
        ),
    )

    op.create_table(
        "messages",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "conversation_id",
            UUID(as_uuid=True),
            sa.ForeignKey("conversations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("sources", sa.Text, nullable=True),
        sa.Column("tokens_used", sa.Integer, default=0),
        sa.Column("response_time_ms", sa.Integer, default=0),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "api_keys",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("key_hash", sa.String(255), nullable=False),
        sa.Column("prefix", sa.String(10), nullable=False),
        sa.Column("is_active", sa.Boolean, default=True),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("api_keys")
    op.drop_table("messages")
    op.drop_table("conversations")
    op.drop_table("custom_contexts")
    op.drop_table("document_chunks")
    op.drop_table("documents")
    op.drop_table("chatbots")
    op.drop_table("users")