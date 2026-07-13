from sqlalchemy import Table, Column, Integer, String
from db import metadata

users = Table(
    "users",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("username", String, unique=True, nullable=False),
    Column("password", String, nullable=False),
)

bots = Table(
    "bot",
    metadata,
    Column("bot_id", Integer, primary_key=True),
    Column("username", String, unique=False, nullable=False),
    Column("context", String),
    Column("temperature", Integer)
)

