from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import MetaData
from databases import Database
from config import DATABASE_URL

DATABASE = Database(DATABASE_URL)
metadata = MetaData()
engine = create_async_engine(DATABASE_URL)
