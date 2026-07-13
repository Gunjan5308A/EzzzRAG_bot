from pydantic import BaseModel
from fastapi import UploadedFile, File

class retrivalItem(BaseModel):
    temp: int = 0.2
    context: str
    id: str
    user: str
    pdf: UploadedFile = File(...)

class User(BaseModel):
    username: str
    password: str

