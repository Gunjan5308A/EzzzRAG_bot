# RAG Automation

RAG Automation is a FastAPI-based application that lets users upload PDF documents, extract their content, index it into a vector database, and ask questions about the uploaded material using an LLM.

## What this project does

The application provides a lightweight workflow for building a document Q&A experience:

- Register and log in users with password hashing
- Upload PDF files through a web form
- Extract text from PDFs using PyMuPDF and OCR with EasyOCR
- Split the extracted text into chunks
- Store the chunks in a Chroma vector database
- Retrieve relevant chunks and answer questions with an LLM

## Main features

- User authentication with hashed passwords
- Bot-specific knowledge bases using a `bot_id` filter
- PDF ingestion and indexing pipeline
- RAG-style question answering
- Configurable LLM and embedding providers through environment variables
- Simple HTML-based dashboard and login UI

## Tech stack

- Python 3.10+
- FastAPI for the API and web endpoints
- SQLAlchemy + Databases for async database access
- SQLite by default, with PostgreSQL support via `DATABASE_URL`
- Chroma vector database for embeddings and retrieval
- LangChain for model and retrieval orchestration
- PyMuPDF and EasyOCR for PDF text extraction
- Jinja2 templates for the web UI

## Project structure

- `app.py` - FastAPI application and API routes
- `config.py` - Environment configuration
- `db.py` - Async database setup and engine creation
- `models.py` - SQLAlchemy table definitions
- `schemas.py` - Pydantic request models
- `src/extract_text.py` - PDF extraction and chunking logic
- `src/model.py` - LLM and embedding provider factory
- `src/rag.py` - Vector store indexing and question answering pipeline
- `templates/` - Login and dashboard HTML templates

## Installation

1. Create and activate a Python virtual environment:

   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```

2. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Configure environment variables. Create a `.env` file with values such as:

   ```env
   LLM_PROVIDER=openai
   LLM_API_KEY=your-openai-key
   LLM_MODEL=gpt-4o-mini

   EMBEDDING_PROVIDER=openai
   EMBEDDING_API_KEY=your-openai-key
   EMBEDDING_MODEL=text-embedding-3-small

   CHROMA_API_KEY=your-chroma-key
   CHROMA_TENANT=your-tenant
   CHROMA_DATABASE=your-database

   DATABASE_URL=sqlite+aiosqlite:///./rag.db
   ```

## Running the app

Start the FastAPI server:

```bash
uvicorn app:app --reload
```

Then open the app in your browser at:

- `http://127.0.0.1:8000/` for the login page
- `http://127.0.0.1:8000/dashboard` for the dashboard UI

## API overview

### Authentication

- `POST /register` - Create a new user account
- `POST /login` - Authenticate a user

### Document ingestion

- `POST /add_chunks` - Upload a PDF and index it for later retrieval

Expected form fields:

- `temp`
- `context`
- `id`
- `username`
- `pdf`

### Question answering

- `GET /ask_question?question=...&bot_id=...` - Ask a question against the indexed documents for a specific bot

## Notes

- The current implementation uses Chroma Cloud by default and expects Chroma credentials to be configured.
- PDF extraction relies on OCR, which can be slower for large or scanned documents.
- The current retrieval pipeline uses the top 3 matching chunks for each question.

## Future improvements

Possible enhancements include:

- JWT-based authentication
- Better file management and per-user document collections
- Support for non-PDF documents
- Improved chunking and metadata strategies
- A richer frontend experience
