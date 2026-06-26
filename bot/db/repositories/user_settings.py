#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""مستودع إعدادات المستخدمين (المحادثات الخاصة)."""

import json
import logging
from dataclasses import dataclass, field
from typing import List, Optional

from bot.db.connection import Database

logger = logging.getLogger(__name__)
_DEFAULT_PRAYERS = ["fajr", "dhuhr", "asr", "maghrib", "isha"]


@dataclass
class UserSettings:
    """إعدادات مستخدم في الخاص."""

    user_id: int
    city: str
    method: str = "isna"
    asr_method: str = "standard"
    timezone: int = 0
    language: str = "ar"
    notifications_on: bool = True
    prelude_on: bool = False
    prelude_minutes: int = 5
    enabled_prayers: List[str] = field(default_factory=lambda: list(_DEFAULT_PRAYERS))


class UserSettingsRepo:
    """CRUD لإعدادات المستخدمين."""

    def __init__(self, db: Database):
        self._db = db

    async def get(self, user_id: int) -> Optional[UserSettings]:
        row = await self._db.fetchone(
            "SELECT * FROM user_settings WHERE user_id = ?", (user_id,)
        )
        return self._row_to_model(row) if row else None

    async def upsert(self, s: UserSettings) -> None:
        """إدراج أو تحديث (INSERT ... ON CONFLICT)."""
        prayers_json = json.dumps(s.enabled_prayers, ensure_ascii=False)
        await self._db.execute(
            """INSERT INTO user_settings
               (user_id, city, method, asr_method, timezone, language,
                notifications_on, prelude_on, prelude_minutes, enabled_prayers)
               VALUES (?,?,?,?,?,?,?,?,?,?)
               ON CONFLICT(user_id) DO UPDATE SET
                 city=excluded.city, method=excluded.method,
                 asr_method=excluded.asr_method, timezone=excluded.timezone,
                 language=excluded.language,
                 notifications_on=excluded.notifications_on,
                 prelude_on=excluded.prelude_on,
                 prelude_minutes=excluded.prelude_minutes,
                 enabled_prayers=excluded.enabled_prayers,
                 updated_at=datetime('now')""",
            (
                s.user_id,
                s.city,
                s.method,
                s.asr_method,
                s.timezone,
                s.language,
                int(s.notifications_on),
                int(s.prelude_on),
                s.prelude_minutes,
                prayers_json,
            ),
        )

    async def update_partial(self, user_id: int, **kwargs) -> bool:
        """تحديث حقول محددة فقط. يرفع ValueError لحقول غير معروفة."""
        if not kwargs:
            return False
        allowed = {
            "city",
            "method",
            "asr_method",
            "timezone",
            "language",
            "notifications_on",
            "prelude_on",
            "prelude_minutes",
            "enabled_prayers",
        }
        bad = set(kwargs) - allowed
        if bad:
            raise ValueError(f"حقول غير معروفة: {bad}")

        sets: list[str] = []
        params: list = []
        for k, v in kwargs.items():
            if k == "enabled_prayers":
                v = json.dumps(v, ensure_ascii=False)
            elif isinstance(v, bool):
                v = int(v)
            sets.append(f"{k} = ?")
            params.append(v)
        sets.append("updated_at = datetime('now')")
        params.append(user_id)
        await self._db.execute(
            f"UPDATE user_settings SET {', '.join(sets)} WHERE user_id = ?",
            params,
        )
        return True

    async def list_with_notifications(self) -> List[UserSettings]:
        """كل المستخدمين الذين فعّلوا التنبيهات (تستخدمهم حلقة الجدولة)."""
        rows = await self._db.fetchall(
            "SELECT * FROM user_settings WHERE notifications_on = 1"
        )
        return [self._row_to_model(r) for r in rows]

    @staticmethod
    def _row_to_model(row) -> UserSettings:
        prayers = row["enabled_prayers"]
        try:
            prayers = json.loads(prayers)
            if not isinstance(prayers, list):
                raise ValueError
        except (ValueError, TypeError):
            logger.warning("⚠️ enabled_prayers تالف، استخدام الافتراضي")
            prayers = list(_DEFAULT_PRAYERS)
        return UserSettings(
            user_id=row["user_id"],
            city=row["city"],
            method=row["method"],
            asr_method=row["asr_method"],
            timezone=row["timezone"],
            language=row["language"],
            notifications_on=bool(row["notifications_on"]),
            prelude_on=bool(row["prelude_on"]),
            prelude_minutes=row["prelude_minutes"],
            enabled_prayers=prayers,
        )
