from urllib.parse import urlparse, urlencode, parse_qs
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import MetaData
from databases import Database
from config import DATABASE_URL

_async_url = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)
parsed = urlparse(_async_url)
if parsed.scheme == "postgresql+asyncpg":
    qs = parse_qs(parsed.query)
    for key in ("sslmode", "channel_binding"):
        qs.pop(key, None)
    new_qs = urlencode(qs, doseq=True)
    _async_url = parsed._replace(query=new_qs).geturl()

DATABASE = Database(_async_url)
metadata = MetaData()
engine = create_async_engine(_async_url)
