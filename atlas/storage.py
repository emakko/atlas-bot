"""SQLite persistence: channel subscriptions and already-posted items."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import aiosqlite

SCHEMA = """
CREATE TABLE IF NOT EXISTS subscriptions (
    guild_id   INTEGER NOT NULL,
    channel_id INTEGER NOT NULL,
    source_key TEXT    NOT NULL,
    role_id    INTEGER,
    PRIMARY KEY (channel_id, source_key)
);
CREATE TABLE IF NOT EXISTS seen_items (
    source_key TEXT NOT NULL,
    item_id    TEXT NOT NULL,
    seen_at    TEXT NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (source_key, item_id)
);
CREATE TABLE IF NOT EXISTS primed_sources (
    source_key TEXT PRIMARY KEY
);
"""


@dataclass(frozen=True)
class Subscription:
    guild_id: int
    channel_id: int
    source_key: str
    role_id: int | None


class Storage:
    def __init__(self, db: aiosqlite.Connection) -> None:
        self._db = db

    @classmethod
    async def open(cls, path: Path | str) -> "Storage":
        if str(path) != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        db = await aiosqlite.connect(path)
        await db.executescript(SCHEMA)
        await db.commit()
        return cls(db)

    async def close(self) -> None:
        await self._db.close()

    # --- subscriptions ---------------------------------------------------

    async def subscribe(
        self, guild_id: int, channel_id: int, source_key: str, role_id: int | None
    ) -> bool:
        """Create or update a subscription. Returns True if it was newly created."""
        cur = await self._db.execute(
            "SELECT 1 FROM subscriptions WHERE channel_id = ? AND source_key = ?",
            (channel_id, source_key),
        )
        existed = await cur.fetchone() is not None
        await self._db.execute(
            "INSERT INTO subscriptions (guild_id, channel_id, source_key, role_id) "
            "VALUES (?, ?, ?, ?) "
            "ON CONFLICT (channel_id, source_key) DO UPDATE SET role_id = excluded.role_id",
            (guild_id, channel_id, source_key, role_id),
        )
        await self._db.commit()
        return not existed

    async def unsubscribe(self, channel_id: int, source_key: str) -> bool:
        cur = await self._db.execute(
            "DELETE FROM subscriptions WHERE channel_id = ? AND source_key = ?",
            (channel_id, source_key),
        )
        await self._db.commit()
        return cur.rowcount > 0

    async def remove_channel(self, channel_id: int) -> None:
        await self._db.execute("DELETE FROM subscriptions WHERE channel_id = ?", (channel_id,))
        await self._db.commit()

    async def subscriptions(
        self, *, guild_id: int | None = None, source_key: str | None = None
    ) -> list[Subscription]:
        query = "SELECT guild_id, channel_id, source_key, role_id FROM subscriptions"
        clauses, params = [], []
        if guild_id is not None:
            clauses.append("guild_id = ?")
            params.append(guild_id)
        if source_key is not None:
            clauses.append("source_key = ?")
            params.append(source_key)
        if clauses:
            query += " WHERE " + " AND ".join(clauses)
        query += " ORDER BY channel_id, source_key"
        cur = await self._db.execute(query, params)
        return [Subscription(*row) for row in await cur.fetchall()]

    async def subscribed_source_keys(self) -> set[str]:
        cur = await self._db.execute("SELECT DISTINCT source_key FROM subscriptions")
        return {row[0] for row in await cur.fetchall()}

    # --- seen items ------------------------------------------------------

    async def is_primed(self, source_key: str) -> bool:
        cur = await self._db.execute(
            "SELECT 1 FROM primed_sources WHERE source_key = ?", (source_key,)
        )
        return await cur.fetchone() is not None

    async def unseen(self, source_key: str, item_ids: list[str]) -> set[str]:
        if not item_ids:
            return set()
        placeholders = ",".join("?" * len(item_ids))
        cur = await self._db.execute(
            f"SELECT item_id FROM seen_items WHERE source_key = ? AND item_id IN ({placeholders})",
            (source_key, *item_ids),
        )
        seen = {row[0] for row in await cur.fetchall()}
        return set(item_ids) - seen

    async def mark_seen(self, source_key: str, item_ids: list[str], *, prime: bool = False) -> None:
        await self._db.executemany(
            "INSERT OR IGNORE INTO seen_items (source_key, item_id) VALUES (?, ?)",
            [(source_key, i) for i in item_ids],
        )
        if prime:
            await self._db.execute(
                "INSERT OR IGNORE INTO primed_sources (source_key) VALUES (?)", (source_key,)
            )
        await self._db.commit()
