from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Depends
from fastapi.responses import HTMLResponse
from src.rag import add_chunks, ask_question
from src.extract_text import extract_text_from_pdf, chunking_text
from schemas import User
from models import users, bots
from db import DATABASE, metadata, engine
import bcrypt
import aiofiles

app = FastAPI()


@app.on_event("startup")
async def startup():
    await DATABASE.connect()
    async with engine.begin() as conn:
        await conn.run_sync(metadata.create_all)

@app.on_event("shutdown")
async def shutdown():
    await DATABASE.disconnect()


async def _serve_html(name: str) -> HTMLResponse:
    async with aiofiles.open(f"templates/{name}", "r") as f:
        content = await f.read()
    return HTMLResponse(content)


@app.get("/", response_class=HTMLResponse)
async def login_page():
    return await _serve_html("login.html")

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page():
    return await _serve_html("dashboard.html")

@app.post("/register")
async def register_user(user: User):
    if not user.username or not user.password:
        raise HTTPException(status_code=400, detail="Username and password cannot be empty.")

    query = users.select().where(users.c.username == user.username)
    existing_user = await DATABASE.fetch_one(query)

    if existing_user:
        raise HTTPException(status_code=400, detail="Username already exists.")
    
    password_hash = bcrypt.hashpw(user.password.encode(), bcrypt.gensalt()).decode()
    
    query = users.insert().values(username=user.username, password=password_hash)
    await DATABASE.execute(query)
    return {"message": "User registered successfully."}

@app.post("/login")
async def login_user(user: User):
    query = users.select().where(users.c.username == user.username)
    existing_user = await DATABASE.fetch_one(query)

    # Note: Accessing fields from Databases library records can be done via 
    # indexing existing_user["password"] or attribute style existing_user.password
    if not existing_user or not bcrypt.checkpw(user.password.encode(), existing_user["password"].encode()):
        raise HTTPException(status_code=400, detail="Invalid username or password.")
    
    return {"message": "Login successful."}

@app.post("/add_chunks")
async def add_chunks_endpoint(
    temp: float = Form(...),
    context: str = Form(...),
    id: str = Form(...),
    username: str = Form(...),
    pdf: UploadFile = File(...),
):
    if pdf.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Only PDFs are allowed.")
    
    bot_id = int(id)

    query = bots.insert().values(
        username=username,
        bot_id=bot_id,
        temperature=int(temp),
        context=context,
    )
    await DATABASE.execute(query)

    pdf_bytes = await pdf.read()
    text = extract_text_from_pdf(pdf_bytes)
    chunks = chunking_text(text)
    add_chunks(chunks, bot_id=bot_id)
    
    return {"status": "Chunks added successfully"}

@app.get("/ask_question")
async def ask_question_endpoint(question: str, bot_id: int):
    answer = ask_question(question, bot_id)
    return {"answer": answer}

