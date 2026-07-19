#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""اتصال SQLite (aiosqlite) + منفّذ migrations المرقّمة.

يوفّر غلافًا رفيعًا يُسهّل الاختبار والعزل. كل الـ repositories تأخذ مثيل Database
وتستخدم واجهته الموحّدة (execute/fetchone/fetchall).
"""

import asyncio
import logging
from pathlib import Path
from typing import Any, Sequence

logger = logging.getLogger(__name__)
_MIGRATIONS_DIR = Path(__file__).parent / "migrations"


class Database:
    """غلاف حول aiosqlite يدعم migrations مرقّمة وتفعيل PRAGMAs الآمنة ومجمّع اتصالات."""

    def __init__(self, db_path: str, pool_size: int = 3):
        self.db_path = db_path
        self.pool_size = pool_size
        self._primary = None
        self._pool: list = []
        self._pool_lock = asyncio.Lock()
        self._migrated = False

    async def _setup_conn(self, conn):
        await conn.execute("PRAGMA journal_mode=WAL")
        await conn.execute("PRAGMA foreign_keys=ON")
        await conn.execute("PRAGMA cache_size=-4000")
        await conn.execute("PRAGMA mmap_size=8388608")
        await conn.execute("PRAGMA synchronous=NORMAL")
        await conn.execute("PRAGMA temp_store=MEMORY")
        await conn.execute("PRAGMA busy_timeout=5000")

    async def connect(self) -> None:
        """يفتح الاتصال، يضبط PRAGMAs، ويُطبّق migrations."""
        import aiosqlite

        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._primary = await aiosqlite.connect(self.db_path, timeout=10)
        self._primary.row_factory = aiosqlite.Row
        await self._setup_conn(self._primary)
        await self.apply_migrations()
        logger.info("✅ قاعدة البيانات جاهزة: %s", self.db_path)

    async def _acquire(self):
        conn = self._primary
        if conn is None:
            raise RuntimeError("Database not connected — call connect() first")
        return conn

    async def _release(self, conn):
        pass

    async def close(self) -> None:
        if self._primary is not None:
            await self._primary.close()
            self._primary = None
        async with self._pool_lock:
            for conn in self._pool:
                await conn.close()
            self._pool.clear()

    @property
    def conn(self):
        if self._primary is None:
            raise RuntimeError("Database not connected — call connect() first")
        return self._primary

    async def apply_migrations(self) -> None:
        """ينفّذ كل ملفات migrations المرقّمة غير المُطبّقة بعد.

        ترقيم الملفات: 0001_name.sql → الإصدار 1.
        """
        if self._migrated:
            return
        conn = self._primary
        await conn.execute(
            "CREATE TABLE IF NOT EXISTS schema_version "
            "(version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL"
            " DEFAULT (datetime('now')))"
        )
        await conn.commit()

        async with conn.execute("SELECT version FROM schema_version") as cur:
            applied = {row[0] for row in await cur.fetchall()}

        files = sorted(
            _MIGRATIONS_DIR.glob("*.sql"),
            key=lambda p: int(p.stem.split("_")[0]),
        )

        pending = [f for f in files if int(f.stem.split("_")[0]) not in applied]
        if not pending:
            self._migrated = True
            return

        for f in pending:
            version = int(f.stem.split("_")[0])
            logger.info("📦 تطبيق migration %s", f.name)
            sql = f.read_text(encoding="utf-8")
            await conn.executescript(sql)
            await conn.execute(
                "INSERT INTO schema_version (version) VALUES (?)", (version,)
            )
            await conn.commit()

        self._migrated = True

    async def execute(self, sql: str, params: Sequence[Any] = ()):
        conn = await self._acquire()
        try:
            cur = await conn.execute(sql, params)
            await conn.commit()
            return cur
        finally:
            await self._release(conn)

    async def executemany(self, sql: str, params: Sequence[Sequence[Any]]) -> None:
        conn = await self._acquire()
        try:
            await conn.executemany(sql, params)
            await conn.commit()
        finally:
            await self._release(conn)

    async def fetchone(self, sql: str, params: Sequence[Any] = ()):
        conn = await self._acquire()
        try:
            async with conn.execute(sql, params) as cur:
                return await cur.fetchone()
        finally:
            await self._release(conn)

    async def fetchall(self, sql: str, params: Sequence[Any] = ()) -> list:
        conn = await self._acquire()
        try:
            async with conn.execute(sql, params) as cur:
                return await cur.fetchall()
        finally:
            await self._release(conn)
