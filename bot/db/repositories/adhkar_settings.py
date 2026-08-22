import logging
from dataclasses import dataclass

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
    last_adhkar_category: str | None = None
    last_sent_at: str | None = None


class AdhkarSettingsRepo:
    def __init__(self, db: Database):
        self._db = db

    async def get(self, chat_id: int) -> AdhkarSettings | None:
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
        if not kwargs:
            return
        allowed = {
            "interval_enabled",
            "interval_minutes",
            "morning_enabled",
            "morning_time",
            "evening_enabled",
            "evening_time",
            "friday_enabled",
            "friday_time",
            "last_adhkar_category",
            "last_sent_at",
        }
        unknown = set(kwargs) - allowed
        if unknown:
            raise ValueError(f"حقول إعدادات أذكار غير معروفة: {unknown}")
        for field in ("interval_minutes",):
            if field in kwargs and (
                not isinstance(kwargs[field], int) or not 1 <= kwargs[field] <= 1440
            ):
                raise ValueError("interval_minutes يجب أن يكون بين 1 و1440")
        for field in ("morning_time", "evening_time", "friday_time"):
            if field in kwargs:
                value = kwargs[field]
                if (
                    not isinstance(value, str)
                    or len(value) != 5
                    or value[2] != ":"
                    or not value.replace(":", "").isdigit()
                    or not 0 <= int(value[:2]) <= 23
                    or not 0 <= int(value[3:]) <= 59
                ):
                    raise ValueError(f"{field} يجب أن يكون بتنسيق HH:MM")
        values = {
            key: int(value)
            if key.endswith("_enabled") and isinstance(value, bool)
            else value
            for key, value in kwargs.items()
        }
        defaults = {
            "interval_enabled": 0,
            "interval_minutes": 20,
            "morning_enabled": 0,
            "morning_time": "06:00",
            "evening_enabled": 0,
            "evening_time": "18:00",
            "friday_enabled": 0,
            "friday_time": "10:00",
            "last_adhkar_category": None,
            "last_sent_at": None,
        }
        vals = []
        for field_name, default in defaults.items():
            vals.extend((field_name in values, values.get(field_name, default)))
        vals.append(chat_id)
        await self._db.execute(
            """UPDATE adhkar_settings SET
               interval_enabled = CASE WHEN ? THEN ? ELSE interval_enabled END,
               interval_minutes = CASE WHEN ? THEN ? ELSE interval_minutes END,
               morning_enabled = CASE WHEN ? THEN ? ELSE morning_enabled END,
               morning_time = CASE WHEN ? THEN ? ELSE morning_time END,
               evening_enabled = CASE WHEN ? THEN ? ELSE evening_enabled END,
               evening_time = CASE WHEN ? THEN ? ELSE evening_time END,
               friday_enabled = CASE WHEN ? THEN ? ELSE friday_enabled END,
               friday_time = CASE WHEN ? THEN ? ELSE friday_time END,
               last_adhkar_category = CASE WHEN ? THEN ? ELSE last_adhkar_category END,
               last_sent_at = CASE WHEN ? THEN ? ELSE last_sent_at END,
               updated_at = datetime('now')
               WHERE chat_id=?""",
            vals,
        )

    async def list_all(self) -> list[AdhkarSettings]:
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
