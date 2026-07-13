from pydantic import BaseModel

class RetrievalItem(BaseModel):
    temp: float = 0.2
    context: str
    id: str
    username: str

class User(BaseModel):
    username: str
    password: str

