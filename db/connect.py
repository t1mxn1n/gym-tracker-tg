from os import getenv

from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

load_dotenv()

# для отслеживания запросов echo=True
engine_async = create_async_engine(getenv("async_db_url"), echo=False)
async_session_maker = async_sessionmaker(engine_async, class_=AsyncSession, expire_on_commit=False)
