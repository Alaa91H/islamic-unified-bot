#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""اتصال SQLite (aiosqlite) + منفّذ migrations المرقّمة.

يوفّر غلافًا رفيعًا يُسهّل الاختبار والعزل. كل الـ repositories تأخذ مثيل Database
وتستخدم واجهته الموحّدة (execute/fetchone/fetchall).
"""

import logging
from pathlib import Path
from typing import Any, Sequence

import aiosqlite

logger = logging.getLogger(__name__)
_MIGRATIONS_DIR = Path(__file__).parent / "migrations"


class Database:
    """غلاف حول aiosqlite يدعم migrations مرقّمة وتفعيل PRAGMAs الآمنة."""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self._conn: aiosqlite.Connection | None = None

    @property
    def conn(self) -> aiosqlite.Connection:
        if self._conn is None:
            raise RuntimeError("Database not connected — call connect() first")
        return self._conn

    async def connect(self) -> None:
        """يفتح الاتصال، يضبط PRAGMAs، ويُطبّق migrations."""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = await aiosqlite.connect(self.db_path)
        self._conn.row_factory = aiosqlite.Row
        # WAL: أداء أعلى للقراءة/الكتابة المتزامنة + أمان ضد الفساد
        await self._conn.execute("PRAGMA journal_mode=WAL")
        await self._conn.execute("PRAGMA foreign_keys=ON")
        await self.apply_migrations()
        logger.info("✅ قاعدة البيانات جاهزة: %s", self.db_path)

    async def close(self) -> None:
        if self._conn is not None:
            await self._conn.close()
            self._conn = None

    async def apply_migrations(self) -> None:
        """ينفّذ كل ملفات migrations المرقّمة غير المُطبّقة بعد.

        ترقيم الملفات: 0001_name.sql → الإصدار 1.
        """
        # جدول الإصدارات يُنشأ دائمًا أولًا (إن لم يوجد)
        await self.conn.execute(
            "CREATE TABLE IF NOT EXISTS schema_version "
            "(version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL"
            " DEFAULT (datetime('now')))"
        )
        await self.conn.commit()

        async with self.conn.execute("SELECT version FROM schema_version") as cur:
            applied = {row[0] for row in await cur.fetchall()}

        files = sorted(
            _MIGRATIONS_DIR.glob("*.sql"),
            key=lambda p: int(p.stem.split("_")[0]),
        )
        for f in files:
            version = int(f.stem.split("_")[0])
            if version in applied:
                continue
            logger.info("📦 تطبيق migration %s", f.name)
            await self.conn.executescript(f.read_text(encoding="utf-8"))
            await self.conn.execute(
                "INSERT INTO schema_version (version) VALUES (?)", (version,)
            )
            await self.conn.commit()

    async def execute(self, sql: str, params: Sequence[Any] = ()) -> aiosqlite.Cursor:
        cur = await self.conn.execute(sql, params)
        await self.conn.commit()
        return cur

    async def executemany(self, sql: str, params: Sequence[Sequence[Any]]) -> None:
        await self.conn.executemany(sql, params)
        await self.conn.commit()

    async def fetchone(
        self, sql: str, params: Sequence[Any] = ()
    ) -> aiosqlite.Row | None:
        async with self.conn.execute(sql, params) as cur:
            return await cur.fetchone()

    async def fetchall(
        self, sql: str, params: Sequence[Any] = ()
    ) -> list[aiosqlite.Row]:
        async with self.conn.execute(sql, params) as cur:
            return await cur.fetchall()
