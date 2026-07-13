from fastapi import FastAPI, UploadedFile, File, HTTPException
from src.rag import add_chunks, ask_question
from src.extract_text import extract_text_from_pdf, chunking_text
from fastapi.responses import HTMLResponse
from schemas import retrivalItem, User
from models import users, bots
from db import DATABASE, metadata, engine
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

app = FastAPI()



@app.on_event("startup")
async def startup():
    await DATABASE.connect()
    metadata.create_all(engine)

@app.on_event("shutdown")
async def shutdown():
    await DATABASE.disconnect()




@app.post("/register")
async def register_user(user: User):
    query = users.select().where(users.c.username == user.username)
    existing_user = await DATABASE.fetch_one(query)

    if existing_user:
        raise HTTPException(status_code=400, detail="Username already exists.")
    
    password_hash = pwd_context.hash(user.password)
    if not user.username or not user.password:
        raise HTTPException(status_code=400, detail="Username and password cannot be empty.")
    
    query = users.insert().values(username=user.username, password=password_hash)
    await DATABASE.execute(query)
    return {"message": "User registered successfully."}




@app.post("/login")
async def login_user(user: User):

    query = users.select().where(users.c.username == user.username)
    existing_user = await DATABASE.fetch_one(query)

    if not existing_user or not pwd_context.verify(user.password, existing_user["password"]):
        raise HTTPException(status_code=400, detail="Invalid username or password.")
    
    return {"message": "Login successful."}




@app.get("/add_chunks")
async def add_chunks_endpoint(bot: retrivalItem):
    if bot.pdf.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Only PDFs are allowed.")
    
    query = bots.insert().values(username=bot.username, bot_id=bot.id, temprature = bot.temp, context=bot.context)
    await DATABASE.execute(query)

    pdf_bytes = await bot.pdf.read()
    text = extract_text_from_pdf(pdf_bytes)

    chunks = chunking_text(text)
    add_chunks(chunks, bot_id = bot.id)
    return {"status": "Chunks added successfully"}





@app.get("/ask_question")
async def ask_question_endpoint(question: str):
    answer = ask_question(question)
    return {"answer": answer}
