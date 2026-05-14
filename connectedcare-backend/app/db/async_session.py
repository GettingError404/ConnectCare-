"""Async SQLAlchemy session scaffold (not yet wired into app)."""
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings


DATABASE_URL_ASYNC = settings.DATABASE_URL.replace("+psycopg2", "+asyncpg") if "+psycopg2" in settings.DATABASE_URL else settings.DATABASE_URL

# Async engine and session factory (scaffold)
async_engine: AsyncEngine = create_async_engine(DATABASE_URL_ASYNC, future=True, echo=False)
AsyncSessionLocal = sessionmaker(bind=async_engine, class_=AsyncSession, expire_on_commit=False)


async def get_async_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session
