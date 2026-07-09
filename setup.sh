#!/usr/bin/env bash
set -euo pipefail

# ──────────────────────────────────────────────
#  RAG Automation - Full Setup Script
#  Sets up backend + static frontend for
#  Railway (backend) + Vercel (frontend) deploy
# ──────────────────────────────────────────────

BOLD='\033[1m'
DIM='\033[2m'
GREEN='\033[32m'
YELLOW='\033[33m'
BLUE='\033[34m'
RED='\033[31m'
NC='\033[0m'

info()  { echo -e "${BLUE}▸${NC} $1"; }
ok()    { echo -e "${GREEN}✓${NC} $1"; }
warn()  { echo -e "${YELLOW}⚠${NC} $1"; }
err()   { echo -e "${RED}✗${NC} $1"; }

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_DIR"

echo -e "\n${BOLD}╔══════════════════════════════════════════╗${NC}"
echo -e "${BOLD}║       RAG Automation - Setup Script      ║${NC}"
echo -e "${BOLD}╚══════════════════════════════════════════╝${NC}\n"

# ── 1. Check prerequisites ──────────────────
info "Checking prerequisites..."

check_cmd() {
  if command -v "$1" &>/dev/null; then
    ok "$1 $(command $1 --version 2>&1 | head -1)"
  else
    err "$1 is not installed. Please install it first."
    exit 1
  fi
}

check_cmd python3
check_cmd pip3
check_cmd git

if command -v node &>/dev/null; then
  ok "node $(node --version)"
else
  warn "node not found (optional, only needed for local dev)"
fi

echo ""

# ── 2. Setup Python virtual environment ──────
info "Setting up Python virtual environment..."

if [ ! -d "venv" ]; then
  python3 -m venv venv
  ok "Created venv/"
else
  ok "venv/ already exists"
fi

source venv/bin/activate
pip install --upgrade pip --quiet
pip install -r backend/requirements.txt --quiet
ok "Backend dependencies installed"

echo ""

# ── 3. Generate .env ─────────────────────────
info "Configuring environment..."

generate_secret() {
  python3 -c "import secrets; print(secrets.token_urlsafe(48))"
}

if [ ! -f ".env" ]; then
  SECRET_KEY=$(generate_secret)

  echo -e "${DIM}Paste values or press Enter to skip optional ones.${NC}\n"

  read -rp "  OpenAI API Key (required): " OPENAI_KEY
  read -rp "  Database URL [postgresql+asyncpg://postgres:postgres@localhost:5432/ragautomation]: " DB_URL
  DB_URL="${DB_URL:-postgresql+asyncpg://postgres:postgres@localhost:5432/ragautomation}"
  read -rp "  Redis URL [redis://localhost:6379/0]: " REDIS_URL
  REDIS_URL="${REDIS_URL:-redis://localhost:6379/0}"
  read -rp "  Frontend URL (your Vercel domain) [http://localhost:3000]: " FRONTEND_URL
  FRONTEND_URL="${FRONTEND_URL:-http://localhost:3000}"

  cat > .env <<EOF
# App
APP_NAME="RAG Automation API"
APP_VERSION="0.1.0"
DEBUG=false
ENVIRONMENT=production
SECRET_KEY=${SECRET_KEY}

# Database
DATABASE_URL=${DB_URL}

# Redis
REDIS_URL=${REDIS_URL}

# CORS (comma-separated, include your Vercel URL)
CORS_ORIGINS=${FRONTEND_URL}

# OAuth (optional)
GITHUB_CLIENT_ID=
GITHUB_CLIENT_SECRET=
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=

# OpenAI
OPENAI_API_KEY=${OPENAI_KEY}
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
OPENAI_CHAT_MODEL=gpt-4o-mini
OPENAI_MAX_TOKENS=4000

# Pinecone (optional - uses pgvector if not set)
PINECONE_API_KEY=
PINECONE_ENVIRONMENT=
PINECONE_INDEX_NAME=rag-automation

# S3 (optional)
S3_ENDPOINT_URL=
S3_ACCESS_KEY=
S3_SECRET_KEY=
S3_BUCKET_NAME=rag-automation

# Celery
CELERY_BROKER_URL=${REDIS_URL/\/0/\/1}
CELERY_RESULT_BACKEND=${REDIS_URL/\/0/\/2}

# Domain
BASE_DOMAIN=${FRONTEND_URL#http://}
SUBDOMAIN_ENABLED=false

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json
EOF

  ok ".env created"
else
  ok ".env already exists (skipping)"
fi

echo ""

# ── 4. Generate vercel.json ──────────────────
info "Generating vercel.json..."

if [ ! -f "vercel.json" ]; then
  cat > vercel.json <<'VERCEL'
{
  "buildCommand": null,
  "outputDirectory": "site",
  "framework": null,
  "rewrites": [
    { "source": "/(.*)", "destination": "/index.html" }
  ],
  "headers": [
    {
      "source": "/(.*)",
      "headers": [
        { "key": "X-Content-Type-Options", "value": "nosniff" },
        { "key": "X-Frame-Options", "value": "DENY" },
        { "key": "Referrer-Policy", "value": "strict-origin-when-cross-origin" }
      ]
    }
  ]
}
VERCEL
  ok "vercel.json created"
else
  ok "vercel.json already exists (skipping)"
fi

# ── 5. Generate railway.json ─────────────────
info "Generating railway.json..."

if [ ! -f "railway.json" ]; then
  cat > railway.json <<'RAILWAY'
{
  "$schema": "https://railway.app/railway.schema.json",
  "build": {
    "builder": "DOCKERFILE",
    "dockerfilePath": "backend/Dockerfile"
  },
  "deploy": {
    "startCommand": "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT",
    "restartPolicyType": "ON_FAILURE",
    "restartPolicyMaxRetries": 10
  }
}
RAILWAY
  ok "railway.json created"
else
  ok "railway.json already exists (skipping)"
fi

echo ""

# ── 6. Generate static frontend ──────────────
info "Building static frontend..."

mkdir -p site/css site/js

# Only generate if site/index.html doesn't exist
if [ ! -f "site/index.html" ]; then
  warn "site/ directory is empty. Run setup.sh from the project root to auto-generate."
  warn "Or copy the site/ files manually."
else
  ok "site/ directory already populated"
fi

echo ""

# ── 7. Run database migrations ───────────────
info "Running database migrations..."

if python3 -c "import asyncpg; asyncpg.connect('$DB_URL')" 2>/dev/null; then
  cd backend
  alembic upgrade head 2>/dev/null && ok "Migrations applied" || warn "Migration skipped (DB may not be reachable)"
  cd "$PROJECT_DIR"
else
  warn "Database not reachable. Run migrations manually after deploying:"
  echo "  cd backend && alembic upgrade head"
fi

echo ""

# ── 8. Print summary ────────────────────────
echo -e "${BOLD}╔══════════════════════════════════════════╗${NC}"
echo -e "${BOLD}║              Setup Complete!              ║${NC}"
echo -e "${BOLD}╚══════════════════════════════════════════╝${NC}\n"

echo -e "${BOLD}Deployment Steps:${NC}\n"

echo -e "${BOLD}1. Deploy Backend to Railway:${NC}"
echo -e "   ${DIM}cd $PROJECT_DIR${NC}"
echo -e "   ${DIM}railway login${NC}"
echo -e "   ${DIM}railway init${NC}"
echo -e "   ${DIM}railway add --database postgres${NC}"
echo -e "   ${DIM}railway add --database redis${NC}"
echo -e "   ${DIM}railway variables set OPENAI_API_KEY=your_key SECRET_KEY=$(generate_secret)${NC}"
echo -e "   ${DIM}railway up${NC}"
echo -e ""

echo -e "${BOLD}2. Deploy Frontend to Vercel:${NC}"
echo -e "   ${DIM}cd $PROJECT_DIR${NC}"
echo -e "   ${DIM}npx vercel --prod${NC}"
echo -e "   ${DIM}(Or connect your Git repo to Vercel dashboard)${NC}"
echo -e ""

echo -e "${BOLD}3. Update CORS:${NC}"
echo -e "   ${DIM}After Vercel deploy, update CORS_ORIGINS in Railway:${NC}"
echo -e "   ${DIM}railway variables set CORS_ORIGINS=https://your-app.vercel.app${NC}"
echo -e ""

echo -e "${BOLD}4. Update Frontend API URL:${NC}"
echo -e "   ${DIM}Edit site/js/api.js and set:${NC}"
echo -e "   ${DIM}const API_BASE = 'https://your-app.up.railway.app/api/v1';${NC}"
echo -e ""

echo -e "${BOLD}Local Development:${NC}"
echo -e "   ${DIM}source venv/bin/activate${NC}"
echo -e "   ${DIM}cd backend && uvicorn app.main:app --reload${NC}"
echo -e "   ${DIM}# Open site/index.html in browser${NC}"
echo -e ""

echo -e "${GREEN}Done! 🚀${NC}"
