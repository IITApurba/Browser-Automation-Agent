import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from packages.db.models import MemoryEntry


class MemoryStore:
    async def save(self, session: AsyncSession, run_id: str, key: str, value: dict | list | None) -> MemoryEntry:
        entry = MemoryEntry(run_id=uuid.UUID(str(run_id)), key=key, value=value)
        session.add(entry)
        await session.commit()
        await session.refresh(entry)
        return entry

    async def get(self, session: AsyncSession, run_id: str, key: str) -> MemoryEntry | None:
        stmt = (
            select(MemoryEntry)
            .where(MemoryEntry.run_id == uuid.UUID(str(run_id)), MemoryEntry.key == key)
            .order_by(MemoryEntry.created_at.desc())
        )
        result = await session.execute(stmt)
        return result.scalars().first()

    async def list_for_run(self, session: AsyncSession, run_id: str) -> list[MemoryEntry]:
        stmt = (
            select(MemoryEntry)
            .where(MemoryEntry.run_id == uuid.UUID(str(run_id)))
            .order_by(MemoryEntry.created_at.asc())
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())
