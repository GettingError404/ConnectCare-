from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from app.core.config import settings


async def ensure_pgvector_extension(engine: AsyncEngine) -> None:
    """Ensure pgvector extension exists in the current database."""
    async with engine.begin() as connection:
        await connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))


async def set_ivfflat_probes(session: AsyncSession, probes: int | None = None) -> None:
    """Tune IVFFlat search recall for the current transaction.

    Higher probes generally increase recall at the cost of latency.
    """
    effective_probes = probes or settings.PGVECTOR_IVFFLAT_PROBES
    await session.execute(
        text("SET LOCAL ivfflat.probes = :probes"),
        {"probes": int(effective_probes)},
    )
