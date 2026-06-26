#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""مستودع إعدادات المجموعات (voice chat)."""

import logging
from dataclasses import dataclass
from typing import List, Optional

from bot.db.connection import Database

logger = logging.getLogger(__name__)


@dataclass
class GroupSettings:
    """إعدادات مجموعة (سوبر جروب) — تتحكم في بث الأذان/القرآن."""

    chat_id: int
    city: str
    method: str = "isna"
    asr_method: str = "standard"
    azan_source: str = "traditional"
    stream_quran_on: bool = False
    stop_stream_before_min: int = 0
    linked_user_id: Optional[int] = None


class GroupSettingsRepo:
    """CRUD لإعدادات المجموعات."""

    def __init__(self, db: Database):
        self._db = db

    async def get(self, chat_id: int) -> Optional[GroupSettings]:
        row = await self._db.fetchone(
            "SELECT * FROM group_settings WHERE chat_id = ?", (chat_id,)
        )
        return self._row_to_model(row) if row else None

    async def upsert(self, g: GroupSettings) -> None:
        await self._db.execute(
            """INSERT INTO group_settings
               (chat_id, city, method, asr_method, azan_source,
                stream_quran_on, stop_stream_before_min, linked_user_id)
               VALUES (?,?,?,?,?,?,?,?)
               ON CONFLICT(chat_id) DO UPDATE SET
                 city=excluded.city, method=excluded.method,
                 asr_method=excluded.asr_method, azan_source=excluded.azan_source,
                 stream_quran_on=excluded.stream_quran_on,
                 stop_stream_before_min=excluded.stop_stream_before_min,
                 linked_user_id=excluded.linked_user_id,
                 updated_at=datetime('now')""",
            (
                g.chat_id,
                g.city,
                g.method,
                g.asr_method,
                g.azan_source,
                int(g.stream_quran_on),
                g.stop_stream_before_min,
                g.linked_user_id,
            ),
        )

    async def list_all(self) -> List[GroupSettings]:
        rows = await self._db.fetchall("SELECT * FROM group_settings")
        return [self._row_to_model(r) for r in rows]

    async def delete(self, chat_id: int) -> None:
        await self._db.execute(
            "DELETE FROM group_settings WHERE chat_id = ?", (chat_id,)
        )

    @staticmethod
    def _row_to_model(row) -> GroupSettings:
        return GroupSettings(
            chat_id=row["chat_id"],
            city=row["city"],
            method=row["method"],
            asr_method=row["asr_method"],
            azan_source=row["azan_source"],
            stream_quran_on=bool(row["stream_quran_on"]),
            stop_stream_before_min=row["stop_stream_before_min"],
            linked_user_id=row["linked_user_id"],
        )
