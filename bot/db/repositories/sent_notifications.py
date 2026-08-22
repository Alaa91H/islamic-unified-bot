"""مستودع سجل تسليم الإشعارات.

يحافظ السجل على مفتاح فريد لكل هدف/حدث/يوم، ويضيف دورة حياة صغيرة:
``processing → sent | failed``. يتيح ذلك حجز الحدث قبل الإرسال، ويمنع مثيلين
من إرسال التنبيه نفسه في وقت واحد، مع تحريره لإعادة المحاولة عند الفشل.
"""

from __future__ import annotations

from typing import Literal

from bot.db.connection import Database

TargetType = Literal["user", "group"]


class SentNotificationsRepo:
    """سجل الإشعارات بتسليم ذري وآمن لإعادة المحاولة."""

    def __init__(self, db: Database):
        self._db = db

    @staticmethod
    def _key(
        target_id: int, target_type: TargetType, prayer: str, prayer_date: str
    ) -> tuple[int, TargetType, str, str]:
        return target_id, target_type, prayer, prayer_date

    async def already_sent(
        self,
        target_id: int,
        target_type: TargetType,
        prayer: str,
        prayer_date: str,
    ) -> bool:
        """هل اكتمل إرسال هذا التنبيه بالفعل؟"""
        row = await self._db.fetchone(
            """SELECT 1 FROM sent_notifications
               WHERE target_id=? AND target_type=? AND prayer=? AND prayer_date=?
                 AND status='sent'
               LIMIT 1""",
            self._key(target_id, target_type, prayer, prayer_date),
        )
        return row is not None

    async def mark_sent(
        self,
        target_id: int,
        target_type: TargetType,
        prayer: str,
        prayer_date: str,
    ) -> bool:
        """واجهة متوافقة لتسجيل حدث مكتمل عند عدم وجود سجل سابق."""
        cursor = await self._db.execute(
            """INSERT INTO sent_notifications
                   (target_id, target_type, prayer, prayer_date, status, claimed_at)
               VALUES (?, ?, ?, ?, 'sent', datetime('now'))
               ON CONFLICT(target_id, target_type, prayer, prayer_date) DO NOTHING""",
            self._key(target_id, target_type, prayer, prayer_date),
        )
        return cursor.rowcount == 1

    async def claim_delivery(
        self,
        target_id: int,
        target_type: TargetType,
        prayer: str,
        prayer_date: str,
        *,
        stale_after_seconds: int = 300,
    ) -> bool:
        """حجز حدث للتسليم.

        لا ينجح الحجز إلا عند عدم وجود سجل أو إذا كان السجل فاشلًا أو عالقًا
        في حالة processing لمدة تجاوزت المهلة. ينفذ القرار داخل SQLite نفسها.
        """
        cursor = await self._db.execute(
            """INSERT INTO sent_notifications
                   (target_id, target_type, prayer, prayer_date, status, claimed_at, attempts)
               VALUES (?, ?, ?, ?, 'processing', datetime('now'), 1)
               ON CONFLICT(target_id, target_type, prayer, prayer_date) DO UPDATE SET
                   status='processing',
                   claimed_at=datetime('now'),
                   attempts=sent_notifications.attempts + 1,
                   last_error=NULL
               WHERE sent_notifications.status='failed'
                  OR (
                      sent_notifications.status='processing'
                      AND sent_notifications.claimed_at < datetime('now', ?)
                  )""",
            (
                *self._key(target_id, target_type, prayer, prayer_date),
                f"-{stale_after_seconds} seconds",
            ),
        )
        return cursor.rowcount == 1

    async def complete_delivery(
        self,
        target_id: int,
        target_type: TargetType,
        prayer: str,
        prayer_date: str,
    ) -> None:
        """وضع الحدث المحجوز في حالة sent بعد نجاح الإرسال."""
        await self._db.execute(
            """UPDATE sent_notifications
               SET status='sent', sent_at=datetime('now'), last_error=NULL
               WHERE target_id=? AND target_type=? AND prayer=? AND prayer_date=?""",
            self._key(target_id, target_type, prayer, prayer_date),
        )

    async def fail_delivery(
        self,
        target_id: int,
        target_type: TargetType,
        prayer: str,
        prayer_date: str,
        error: Exception,
    ) -> None:
        """تسجيل فشل قابل لإعادة المحاولة من دورة جدولة لاحقة."""
        await self._db.execute(
            """UPDATE sent_notifications
               SET status='failed', last_error=?
               WHERE target_id=? AND target_type=? AND prayer=? AND prayer_date=?""",
            (str(error)[:500], *self._key(target_id, target_type, prayer, prayer_date)),
        )
