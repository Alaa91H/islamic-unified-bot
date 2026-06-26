#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""مستودع سجل التنبيهات المُرسلة — لمنع التكرار بعد restart أو race condition.

المفتاح الفريد (target_id, target_type, prayer, prayer_date) يضمن أن أي تنبيه
لا يُرسل مرتين لنفس الهدف في نفس اليوم، حتى لو تداخلت دورتا جدولة.
مفاتيح المقدمة (prelude) تستخدم مفتاحًا منفصلًا: prelude_<prayer>.
"""

import logging
from typing import Literal

from bot.db.connection import Database

logger = logging.getLogger(__name__)
TargetType = Literal["user", "group"]


class SentNotificationsRepo:
    """يومية التنبيهات المُرسلة — idempotent وخيطيّ-آمن عبر UNIQUE constraint."""

    def __init__(self, db: Database):
        self._db = db

    async def already_sent(
        self,
        target_id: int,
        target_type: TargetType,
        prayer: str,
        prayer_date: str,
    ) -> bool:
        """هل أُرسل هذا التنبيه فعلًا (نفس الهدف/الصلاة/اليوم)؟"""
        row = await self._db.fetchone(
            """SELECT 1 FROM sent_notifications
               WHERE target_id=? AND target_type=? AND prayer=? AND prayer_date=?
               LIMIT 1""",
            (target_id, target_type, prayer, prayer_date),
        )
        return row is not None

    async def mark_sent(
        self,
        target_id: int,
        target_type: TargetType,
        prayer: str,
        prayer_date: str,
    ) -> bool:
        """يسجّل الإرسال. يُرجع True إذا سُجّل الآن، False إذا كان مسجّلًا سابقًا.

        آمن ضد التزامن: UNIQUE constraint يضمن نجاح إدراج واحد فقط.
        """
        try:
            await self._db.execute(
                """INSERT INTO sent_notifications
                   (target_id, target_type, prayer, prayer_date)
                   VALUES (?,?,?,?)""",
                (target_id, target_type, prayer, prayer_date),
            )
            return True
        except Exception:  # IntegrityError → موجود مسبقًا
            return False
