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
        max_attempts: int = 5,
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
               WHERE (
                      sent_notifications.status='failed'
                      AND sent_notifications.retry_class='transient'
                      AND sent_notifications.attempts < ?
                      AND (
                          sent_notifications.next_retry_at IS NULL
                          OR sent_notifications.next_retry_at <= datetime('now')
                      )
                  )
                  OR (
                      sent_notifications.status='processing'
                      AND sent_notifications.attempts < ?
                      AND sent_notifications.claimed_at < datetime('now', ?)
                  )""",
            (
                *self._key(target_id, target_type, prayer, prayer_date),
                max_attempts,
                max_attempts,
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
               SET status='sent', sent_at=datetime('now'), last_error=NULL,
                   next_retry_at=NULL
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
        *,
        retryable: bool = True,
    ) -> None:
        """تسجيل فشل بمهلة تصاعدية، أو إنهاؤه كفشل دائم عند عدم قابلية الإعادة."""
        await self._db.execute(
            """UPDATE sent_notifications
               SET status='failed', last_error=?,
                   retry_class=?,
                   next_retry_at = CASE
                       WHEN ? = 0 THEN NULL
                       WHEN attempts <= 1 THEN datetime('now', '+30 seconds')
                       WHEN attempts = 2 THEN datetime('now', '+1 minute')
                       WHEN attempts = 3 THEN datetime('now', '+2 minutes')
                       WHEN attempts = 4 THEN datetime('now', '+5 minutes')
                       ELSE datetime('now', '+15 minutes')
                   END
               WHERE target_id=? AND target_type=? AND prayer=? AND prayer_date=?""",
            (
                str(error)[:500],
                "transient" if retryable else "permanent",
                int(retryable),
                *self._key(target_id, target_type, prayer, prayer_date),
            ),
        )

    async def delivery_metrics(self) -> dict[str, int]:
        """إرجاع عدادات outbox وصحته التشغيلية دون كشف أي محتوى مستخدم."""
        rows = await self._db.fetchall(
            "SELECT status, COUNT(*) AS count FROM sent_notifications GROUP BY status"
        )
        metrics = {"processing": 0, "sent": 0, "failed": 0}
        metrics.update({row["status"]: row["count"] for row in rows})
        health = await self._db.fetchone(
            """SELECT
                   SUM(CASE WHEN status='failed' AND retry_class='transient'
                            THEN 1 ELSE 0 END) AS transient_failed,
                   SUM(CASE WHEN status='failed' AND retry_class='permanent'
                            THEN 1 ELSE 0 END) AS permanent_failed,
                   SUM(CASE WHEN status='failed' AND retry_class='transient'
                              AND (next_retry_at IS NULL OR next_retry_at <= datetime('now'))
                            THEN 1 ELSE 0 END) AS retry_due,
                   MAX(CASE WHEN status='processing' AND claimed_at IS NOT NULL
                            THEN CAST(strftime('%s', 'now') - strftime('%s', claimed_at) AS INTEGER)
                            ELSE 0 END) AS oldest_processing_age_seconds
               FROM sent_notifications"""
        )
        metrics.update(
            {
                "transient_failed": int(health["transient_failed"] or 0),
                "permanent_failed": int(health["permanent_failed"] or 0),
                "retry_due": int(health["retry_due"] or 0),
                "oldest_processing_age_seconds": int(
                    health["oldest_processing_age_seconds"] or 0
                ),
            }
        )
        return metrics
