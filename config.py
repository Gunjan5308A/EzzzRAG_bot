from dotenv import load_dotenv
import os

load_dotenv()

OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
CHROMA_API_KEY: str = os.getenv("CHROMA_API_KEY", "")
OpenAI_base_URL: str = os.getenv("BASE_URL", "")
DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./rag.db")
EMBEDDING_MODEL: str = os.getenv("DATABASE_URL", "sqlite:///./rag.db")
