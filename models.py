from sqlalchemy import create_engine, table, Column, Integer, String, MetaData

users = table(
    "users",
    MetaData(),
    Column("id", Integer, primary_key=True),
    Column("username", String, unique=True, nullable=False),
    Column("password", String, nullable=False),
)

bots = table(
    "bot",
    MetaData(),
    Column("bot_id", Integer, primary_key=True),
    Column("username", String, unique=False, nullable=False),
    Column("context", String),
    Column("temprature", Integer)
)

