from dotenv import load_dotenv
import os

load_dotenv()

# Backward-compatible helpers: fall back to old single-key env vars
_legacy_key = os.getenv("OPENAI_API_KEY", "")
_legacy_url = os.getenv("BASE_URL", "")

# LLM Provider
LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "openai")
LLM_API_KEY: str = os.getenv("LLM_API_KEY") or _legacy_key or ""
LLM_BASE_URL: str = os.getenv("LLM_BASE_URL") or _legacy_url or "https://api.openai.com/v1"
LLM_MODEL: str = os.getenv("LLM_MODEL", "gpt-4o-mini")

# Embedding Provider
EMBEDDING_PROVIDER: str = os.getenv("EMBEDDING_PROVIDER", "openai")
EMBEDDING_API_KEY: str = os.getenv("EMBEDDING_API_KEY") or _legacy_key or ""
EMBEDDING_BASE_URL: str = os.getenv("EMBEDDING_BASE_URL") or _legacy_url or "https://api.openai.com/v1"
EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")

# Chroma / Vector Store
CHROMA_API_KEY: str = os.getenv("CHROMA_API_KEY", "")
CHROMA_URL: str = os.getenv("CHROMA_URL", "http://localhost:8000")

# Database
DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./rag.db")
