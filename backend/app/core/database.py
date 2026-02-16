from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncAttrs, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import String
from urllib.parse import quote_plus
import aiomysql

from app.core.config import DB_HOST, DB_NAME, DB_PASSWORD, DB_PORT, DB_USER


class Base(AsyncAttrs, DeclarativeBase):
    """Async SQLAlchemy base with common id column."""

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)


# Build async MySQL URL with safe quoting
DATABASE_URL = (
    f"mysql+aiomysql://{quote_plus(DB_USER)}:{quote_plus(DB_PASSWORD)}@"
    f"{DB_HOST}:{DB_PORT}/{quote_plus(DB_NAME)}"
)

engine = create_async_engine(DATABASE_URL, pool_pre_ping=True, future=True)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def init_db() -> None:
    """Create tables if they do not exist."""
    await ensure_database_exists()

    from app.db import models  # noqa: WPS433 - import to register models

    async with engine.begin() as conn:
        await conn.run_sync(models.Base.metadata.create_all)


async def ensure_database_exists() -> None:
    """Create the target database if it does not already exist."""
    conn = await aiomysql.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        autocommit=True,
    )
    try:
        async with conn.cursor() as cur:
            await cur.execute(f"CREATE DATABASE IF NOT EXISTS `{DB_NAME}` DEFAULT CHARACTER SET utf8mb4")
    finally:
        conn.close()


async def get_db() -> AsyncSession:
    """FastAPI dependency that yields a DB session."""
    async with SessionLocal() as session:
        yield session
