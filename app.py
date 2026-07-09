import os
import secrets
import sqlite3
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Form, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from jose import JWTError, jwt
import bcrypt

# ── Config ──────────────────────────────────────────────
SECRET_KEY = os.getenv("SECRET_KEY", secrets.token_urlsafe(48))
DATABASE = Path(__file__).parent / "rag.db"
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
API_URL = os.getenv("API_URL", "http://localhost:8000/api/v1")

def hash_password(p: str) -> str:
    return bcrypt.hashpw(p.encode(), bcrypt.gensalt()).decode()

def verify_password(p: str, h: str) -> bool:
    return bcrypt.checkpw(p.encode(), h.encode())

# ── Database ────────────────────────────────────────────
def get_db():
    conn = sqlite3.connect(str(DATABASE))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn

def init_db():
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            hashed_password TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS chatbots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            slug TEXT UNIQUE NOT NULL,
            description TEXT DEFAULT '',
            system_prompt TEXT DEFAULT '',
            model TEXT DEFAULT 'gpt-4o-mini',
            temperature REAL DEFAULT 0.7,
            theme_color TEXT DEFAULT '#2563eb',
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );
        CREATE TABLE IF NOT EXISTS documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chatbot_id INTEGER NOT NULL,
            filename TEXT NOT NULL,
            status TEXT DEFAULT 'pending',
            chunk_count INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (chatbot_id) REFERENCES chatbots(id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS contexts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chatbot_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            content TEXT NOT NULL,
            priority INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (chatbot_id) REFERENCES chatbots(id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    conn.commit()
    conn.close()

# ── Auth helpers ────────────────────────────────────────
def create_token(user_id: int, email: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(days=7)
    return jwt.encode({"sub": str(user_id), "email": email, "exp": expire}, SECRET_KEY, algorithm="HS256")

def decode_token(token: str):
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
    except JWTError:
        return None

def get_current_user(request: Request):
    token = request.cookies.get("token")
    if not token:
        return None
    data = decode_token(token)
    if not data:
        return None
    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE id = ?", (int(data["sub"]),)).fetchone()
    conn.close()
    return dict(user) if user else None

# ── App ─────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield

app = FastAPI(title="RAG Automation", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=Path(__file__).parent / "static"), name="static")
templates = Jinja2Templates(directory=Path(__file__).parent / "templates")

# ── Page routes ─────────────────────────────────────────
@app.get("/", response_class=HTMLResponse)
async def page_index(request: Request):
    return templates.TemplateResponse(request, "index.html")

@app.get("/login", response_class=HTMLResponse)
async def page_login(request: Request):
    return templates.TemplateResponse(request, "login.html")

@app.get("/register", response_class=HTMLResponse)
async def page_register(request: Request):
    return templates.TemplateResponse(request, "register.html")

@app.get("/dashboard", response_class=HTMLResponse)
async def page_dashboard(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse("/login", status_code=302)
    return templates.TemplateResponse(request, "dashboard.html", {"user": user})

@app.get("/chatbots", response_class=HTMLResponse)
async def page_chatbots(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse("/login", status_code=302)
    return templates.TemplateResponse(request, "chatbots.html", {"user": user})

@app.get("/chatbots/new", response_class=HTMLResponse)
async def page_chatbot_new(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse("/login", status_code=302)
    return templates.TemplateResponse(request, "chatbot_new.html", {"user": user})

@app.get("/chatbots/{chatbot_id}", response_class=HTMLResponse)
async def page_chatbot_detail(request: Request, chatbot_id: int):
    user = get_current_user(request)
    if not user:
        return RedirectResponse("/login", status_code=302)
    conn = get_db()
    bot = conn.execute("SELECT * FROM chatbots WHERE id = ? AND user_id = ?", (chatbot_id, user["id"])).fetchone()
    conn.close()
    if not bot:
        return RedirectResponse("/chatbots", status_code=302)
    return templates.TemplateResponse(request, "chatbot_detail.html", {"user": user, "bot": dict(bot)})

@app.get("/chat/{slug}", response_class=HTMLResponse)
async def page_chat(request: Request, slug: str):
    conn = get_db()
    bot = conn.execute("SELECT * FROM chatbots WHERE slug = ? AND is_active = 1", (slug,)).fetchone()
    conn.close()
    if not bot:
        return HTMLResponse("<h1>Chatbot not found</h1>", status_code=404)
    return templates.TemplateResponse(request, "chat.html", {"bot": dict(bot)})

# ── Auth API ────────────────────────────────────────────
@app.post("/api/register")
async def api_register(email: str = Form(...), password: str = Form(...), name: str = Form(...)):
    conn = get_db()
    existing = conn.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
    if existing:
        conn.close()
        raise HTTPException(400, "Email already registered")
    hashed = hash_password(password)
    cur = conn.execute("INSERT INTO users (email, name, hashed_password) VALUES (?, ?, ?)", (email, name, hashed))
    conn.commit()
    user_id = cur.lastrowid
    conn.close()
    token = create_token(user_id, email)
    resp = RedirectResponse("/dashboard", status_code=302)
    resp.set_cookie("token", token, httponly=True, max_age=60*60*24*7)
    return resp

@app.post("/api/login")
async def api_login(email: str = Form(...), password: str = Form(...)):
    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
    conn.close()
    if not user or not user["hashed_password"] or not verify_password(password, user["hashed_password"]):
        raise HTTPException(401, "Invalid credentials")
    token = create_token(user["id"], email)
    resp = RedirectResponse("/dashboard", status_code=302)
    resp.set_cookie("token", token, httponly=True, max_age=60*60*24*7)
    return resp

@app.get("/api/logout")
async def api_logout():
    resp = RedirectResponse("/", status_code=302)
    resp.delete_cookie("token")
    return resp

# ── Chatbot API ─────────────────────────────────────────
@app.get("/api/chatbots")
async def api_list_chatbots(request: Request):
    user = get_current_user(request)
    if not user:
        raise HTTPException(401)
    conn = get_db()
    bots = conn.execute("SELECT * FROM chatbots WHERE user_id = ? ORDER BY created_at DESC", (user["id"],)).fetchall()
    result = []
    for b in bots:
        d = dict(b)
        d["document_count"] = conn.execute("SELECT COUNT(*) FROM documents WHERE chatbot_id = ?", (b["id"],)).fetchone()[0]
        d["context_count"] = conn.execute("SELECT COUNT(*) FROM contexts WHERE chatbot_id = ?", (b["id"],)).fetchone()[0]
        result.append(d)
    conn.close()
    return result

@app.post("/api/chatbots")
async def api_create_chatbot(request: Request, name: str = Form(...), description: str = Form(""), system_prompt: str = Form(""), model: str = Form("gpt-4o-mini"), temperature: float = Form(0.7), theme_color: str = Form("#2563eb")):
    user = get_current_user(request)
    if not user:
        raise HTTPException(401)
    import re, uuid
    slug = re.sub(r"[^\w\s-]", "", name.lower().strip())
    slug = re.sub(r"[\s_-]+", "-", slug)
    slug = re.sub(r"^-+|-+$", "", slug)
    conn = get_db()
    existing = conn.execute("SELECT id FROM chatbots WHERE slug = ?", (slug,)).fetchone()
    if existing:
        slug = f"{slug}-{uuid.uuid4().hex[:8]}"
    cur = conn.execute("INSERT INTO chatbots (user_id, name, slug, description, system_prompt, model, temperature, theme_color) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", (user["id"], name, slug, description, system_prompt, model, temperature, theme_color))
    conn.commit()
    bot_id = cur.lastrowid
    conn.close()
    return RedirectResponse(f"/chatbots/{bot_id}", status_code=302)

@app.post("/api/chatbots/{chatbot_id}/update")
async def api_update_chatbot(chatbot_id: int, request: Request, name: str = Form(...), description: str = Form(""), system_prompt: str = Form(""), model: str = Form("gpt-4o-mini"), temperature: float = Form(0.7), theme_color: str = Form("#2563eb"), is_active: str = Form("on")):
    user = get_current_user(request)
    if not user:
        raise HTTPException(401)
    conn = get_db()
    conn.execute("UPDATE chatbots SET name=?, description=?, system_prompt=?, model=?, temperature=?, theme_color=?, is_active=? WHERE id=? AND user_id=?", (name, description, system_prompt, model, temperature, theme_color, 1 if is_active == "on" else 0, chatbot_id, user["id"]))
    conn.commit()
    conn.close()
    return RedirectResponse(f"/chatbots/{chatbot_id}", status_code=302)

@app.post("/api/chatbots/{chatbot_id}/delete")
async def api_delete_chatbot(chatbot_id: int, request: Request):
    user = get_current_user(request)
    if not user:
        raise HTTPException(401)
    conn = get_db()
    conn.execute("DELETE FROM chatbots WHERE id = ? AND user_id = ?", (chatbot_id, user["id"]))
    conn.commit()
    conn.close()
    return RedirectResponse("/chatbots", status_code=302)

# ── Document API ────────────────────────────────────────
@app.get("/api/chatbots/{chatbot_id}/documents")
async def api_list_docs(chatbot_id: int, request: Request):
    user = get_current_user(request)
    if not user:
        raise HTTPException(401)
    conn = get_db()
    docs = conn.execute("SELECT * FROM documents WHERE chatbot_id = ? ORDER BY created_at DESC", (chatbot_id,)).fetchall()
    conn.close()
    return [dict(d) for d in docs]

@app.get("/api/chatbots/{chatbot_id}/contexts")
async def api_list_contexts(chatbot_id: int, request: Request):
    user = get_current_user(request)
    if not user:
        raise HTTPException(401)
    conn = get_db()
    ctxs = conn.execute("SELECT * FROM contexts WHERE chatbot_id = ? ORDER BY priority DESC", (chatbot_id,)).fetchall()
    conn.close()
    return [dict(c) for c in ctxs]

@app.post("/api/chatbots/{chatbot_id}/documents")
async def api_upload_doc(chatbot_id: int, request: Request, file: UploadFile = File(...)):
    user = get_current_user(request)
    if not user:
        raise HTTPException(401)
    conn = get_db()
    bot = conn.execute("SELECT id FROM chatbots WHERE id = ? AND user_id = ?", (chatbot_id, user["id"])).fetchone()
    if not bot:
        conn.close()
        raise HTTPException(404)
    content = await file.read()
    conn.execute("INSERT INTO documents (chatbot_id, filename, status, chunk_count) VALUES (?, ?, 'completed', ?)", (chatbot_id, file.filename, max(1, len(content) // 1000)))
    conn.commit()
    conn.close()
    return RedirectResponse(f"/chatbots/{chatbot_id}", status_code=302)

@app.post("/api/chatbots/{chatbot_id}/documents/{doc_id}/delete")
async def api_delete_doc(chatbot_id: int, doc_id: int, request: Request):
    user = get_current_user(request)
    if not user:
        raise HTTPException(401)
    conn = get_db()
    conn.execute("DELETE FROM documents WHERE id = ? AND chatbot_id = ?", (doc_id, chatbot_id))
    conn.commit()
    conn.close()
    return RedirectResponse(f"/chatbots/{chatbot_id}", status_code=302)

# ── Context API ─────────────────────────────────────────
@app.post("/api/chatbots/{chatbot_id}/contexts")
async def api_create_context(chatbot_id: int, request: Request, name: str = Form(...), content: str = Form(...), priority: int = Form(0)):
    user = get_current_user(request)
    if not user:
        raise HTTPException(401)
    conn = get_db()
    conn.execute("INSERT INTO contexts (chatbot_id, name, content, priority) VALUES (?, ?, ?, ?)", (chatbot_id, name, content, priority))
    conn.commit()
    conn.close()
    return RedirectResponse(f"/chatbots/{chatbot_id}", status_code=302)

@app.post("/api/chatbots/{chatbot_id}/contexts/{ctx_id}/delete")
async def api_delete_context(chatbot_id: int, ctx_id: int, request: Request):
    user = get_current_user(request)
    if not user:
        raise HTTPException(401)
    conn = get_db()
    conn.execute("DELETE FROM contexts WHERE id = ? AND chatbot_id = ?", (ctx_id, chatbot_id))
    conn.commit()
    conn.close()
    return RedirectResponse(f"/chatbots/{chatbot_id}", status_code=302)

# ── Chat API ────────────────────────────────────────────
@app.post("/api/chat/{slug}")
async def api_chat(slug: str, message: str = Form(...), conversation_id: str = Form("")):
    conn = get_db()
    bot = conn.execute("SELECT * FROM chatbots WHERE slug = ? AND is_active = 1", (slug,)).fetchone()
    if not bot:
        conn.close()
        raise HTTPException(404, "Chatbot not found")

    if not conversation_id:
        import uuid
        conversation_id = str(uuid.uuid4())

    conn.execute("INSERT INTO messages (conversation_id, role, content) VALUES (?, 'user', ?)", (conversation_id, message))

    # Build context from custom contexts
    ctxs = conn.execute("SELECT content FROM contexts WHERE chatbot_id = ? ORDER BY priority DESC", (bot["id"],)).fetchall()
    system_parts = []
    if bot["system_prompt"]:
        system_parts.append(bot["system_prompt"])
    for c in ctxs:
        system_parts.append(c["content"])

    # Simple response (in real app, call OpenAI here)
    response_text = f"I received your message: '{message}'. This is a demo response. Connect your OpenAI API key for real AI responses."

    if OPENAI_API_KEY:
        try:
            import httpx
            system_prompt = "\n\n".join(system_parts) if system_parts else "You are a helpful assistant."
            async with httpx.AsyncClient() as client:
                resp = await client.post("https://api.openai.com/v1/chat/completions", json={
                    "model": bot["model"] or "gpt-4o-mini",
                    "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": message}],
                    "temperature": bot["temperature"] or 0.7,
                }, headers={"Authorization": f"Bearer {OPENAI_API_KEY}"}, timeout=30)
                if resp.status_code == 200:
                    response_text = resp.json()["choices"][0]["message"]["content"]
        except Exception:
            pass

    conn.execute("INSERT INTO messages (conversation_id, role, content) VALUES (?, 'assistant', ?)", (conversation_id, response_text))
    conn.commit()
    conn.close()

    return {"response": response_text, "conversation_id": conversation_id}

# ── Run ─────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    print("\n  🚀 RAG Automation running at http://localhost:8000\n")
    uvicorn.run(app, host="0.0.0.0", port=8000)
