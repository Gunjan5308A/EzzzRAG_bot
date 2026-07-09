# RAG Automation

A SaaS platform for building AI-powered chatbots with RAG (Retrieval-Augmented Generation) capabilities. Upload documents, add custom context, and deploy intelligent chatbots to your website.

## Features

- **OAuth Authentication**: Sign in with GitHub or Google
- **Document Processing**: Upload PDFs, TXT, MD, CSV, DOCX files
- **Vector Embeddings**: Automatic document embedding using OpenAI
- **Custom Context**: Add FAQs, instructions, or product information
- **RAG-powered Chat**: Chatbots that answer based on your documents
- **Widget Embedding**: Easy embed code for any website
- **Subdomain Support**: Each chatbot gets its own subdomain

## Tech Stack

### Backend
- **FastAPI**: High-performance Python API framework
- **PostgreSQL**: Primary database with pgvector for vector storage
- **Redis**: Caching and Celery task queue
- **Celery**: Background job processing
- **OpenAI**: Embeddings and chat completions
- **Pinecone**: Optional vector database (alternative to pgvector)

### Frontend
- **Next.js 15**: React framework with App Router
- **TypeScript**: Type-safe development
- **Tailwind CSS**: Utility-first styling
- **Radix UI**: Accessible component primitives

## Prerequisites

- Python 3.11+
- Node.js 20+
- PostgreSQL 16+ (with pgvector extension)
- Redis 7+

## Quick Start

### 1. Clone and Setup

```bash
# Clone the repository
git clone <repository-url>
cd ragAutomation

# Copy environment files
cp .env.example .env
cp frontend/.env.local.example frontend/.env.local
```

### 2. Configure Environment

Edit `.env` with your credentials:

```env
SECRET_KEY=your-super-secret-key-min-32-chars
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/ragautomation
OPENAI_API_KEY=sk-your-openai-api-key
GITHUB_CLIENT_ID=your-github-client-id
GITHUB_CLIENT_SECRET=your-github-client-secret
```

### 3. Start with Docker Compose

```bash
docker-compose up -d
```

This starts:
- API server on http://localhost:8000
- Frontend on http://localhost:3000
- PostgreSQL on port 5432
- Redis on port 6379
- Celery worker
- Flower monitoring on http://localhost:5555

### 4. Run Database Migrations

```bash
cd backend
alembic upgrade head
```

## Development Setup

### Backend

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -e ".[dev]"

# Run migrations
alembic upgrade head

# Start the server
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

## API Documentation

Once running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Project Structure

```
ragAutomation/
├── backend/
│   ├── app/
│   │   ├── api/v1/          # API routes
│   │   ├── core/            # Configuration, database
│   │   ├── models/          # SQLAlchemy models
│   │   ├── schemas/         # Pydantic schemas
│   │   ├── services/        # Business logic
│   │   └── tasks/           # Celery tasks
│   ├── alembic/             # Database migrations
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── app/             # Next.js App Router pages
│   │   ├── components/      # React components
│   │   ├── hooks/           # Custom hooks
│   │   ├── lib/             # Utilities, API client
│   │   └── types/           # TypeScript types
│   └── Dockerfile
├── docker-compose.yml
└── .env.example
```

## Deployment

### Production Docker Build

```bash
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

### Environment Variables for Production

```env
ENVIRONMENT=production
DEBUG=false
SECRET_KEY=<secure-random-key>
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/dbname
OPENAI_API_KEY=sk-...
CORS_ORIGINS=https://yourdomain.com
```

### Kubernetes Deployment

The Docker images are ready for Kubernetes. Use the following base images:
- Backend: `ragautomation-backend:latest`
- Frontend: `ragautomation-frontend:latest`

## License

MIT# EzzzRAG_bot
