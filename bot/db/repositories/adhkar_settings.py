import logging
from dataclasses import dataclass
from typing import List, Optional

from bot.db.connection import Database

logger = logging.getLogger(__name__)


@dataclass
class AdhkarSettings:
    chat_id: int
    interval_enabled: bool = False
    interval_minutes: int = 20
    morning_enabled: bool = False
    morning_time: str = "06:00"
    evening_enabled: bool = False
    evening_time: str = "18:00"
    friday_enabled: bool = False
    friday_time: str = "10:00"
    last_adhkar_category: Optional[str] = None
    last_sent_at: Optional[str] = None


class AdhkarSettingsRepo:
    def __init__(self, db: Database):
        self._db = db

    async def get(self, chat_id: int) -> Optional[AdhkarSettings]:
        row = await self._db.fetchone(
            "SELECT * FROM adhkar_settings WHERE chat_id = ?", (chat_id,)
        )
        return self._row_to_model(row) if row else None

    async def upsert(self, s: AdhkarSettings) -> None:
        await self._db.execute(
            """INSERT INTO adhkar_settings
               (chat_id, interval_enabled, interval_minutes,
                morning_enabled, morning_time,
                evening_enabled, evening_time,
                friday_enabled, friday_time,
                last_adhkar_category, last_sent_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?)
               ON CONFLICT(chat_id) DO UPDATE SET
                 interval_enabled=excluded.interval_enabled,
                 interval_minutes=excluded.interval_minutes,
                 morning_enabled=excluded.morning_enabled,
                 morning_time=excluded.morning_time,
                 evening_enabled=excluded.evening_enabled,
                 evening_time=excluded.evening_time,
                 friday_enabled=excluded.friday_enabled,
                 friday_time=excluded.friday_time,
                 last_adhkar_category=excluded.last_adhkar_category,
                 last_sent_at=excluded.last_sent_at,
                 updated_at=datetime('now')""",
            (
                s.chat_id,
                int(s.interval_enabled),
                s.interval_minutes,
                int(s.morning_enabled),
                s.morning_time,
                int(s.evening_enabled),
                s.evening_time,
                int(s.friday_enabled),
                s.friday_time,
                s.last_adhkar_category,
                s.last_sent_at,
            ),
        )

    async def update_partial(self, chat_id: int, **kwargs) -> None:
        sets = ", ".join(f"{k}=?" for k in kwargs)
        vals = list(kwargs.values()) + [chat_id]
        await self._db.execute(
            f"UPDATE adhkar_settings SET {sets}, updated_at=datetime('now') "
            f"WHERE chat_id=?",
            vals,
        )

    async def list_all(self) -> List[AdhkarSettings]:
        rows = await self._db.fetchall("SELECT * FROM adhkar_settings")
        return [self._row_to_model(r) for r in rows]

    async def delete(self, chat_id: int) -> None:
        await self._db.execute(
            "DELETE FROM adhkar_settings WHERE chat_id = ?", (chat_id,)
        )

    @staticmethod
    def _row_to_model(row) -> AdhkarSettings:
        return AdhkarSettings(
            chat_id=row["chat_id"],
            interval_enabled=bool(row["interval_enabled"]),
            interval_minutes=row["interval_minutes"],
            morning_enabled=bool(row["morning_enabled"]),
            morning_time=row["morning_time"],
            evening_enabled=bool(row["evening_enabled"]),
            evening_time=row["evening_time"],
            friday_enabled=bool(row["friday_enabled"]),
            friday_time=row["friday_time"],
            last_adhkar_category=row["last_adhkar_category"],
            last_sent_at=row["last_sent_at"],
        )
