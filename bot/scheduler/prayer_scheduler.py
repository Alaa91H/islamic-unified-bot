#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""حلقة جدولة الصلاة الخلفية — تستيقظ دوريًا وتطلق التنبيهات.

دورة العمل:
  كل TICK_SECONDS ثانية:
    1. تجمع كل المستخدمين/المجموعات التي فعّلت التنبيهات.
    2. لكل هدف: تحسب أوقات صلاة اليوم وتقارنها بالوقت الحالي (UTC).
    3. تتحقق من sent_notifications لمنع التكرار.
    4. تطلق: نص للمستخدم / بث للمجموعة.
    5. المقدمة (prelude) تُكتشف قبل الأذان بـN دقيقة كحدث منفصل (مفتاح prelude_<prayer>).

ضمانات:
- idempotent عبر UNIQUE constraint في sent_notifications.
- خطأ هدف واحد لا يوقف البقية (try/except لكل هدف).
- إيقاف آمن: stop() يُلغي المهمة عند SIGTERM.
"""

import asyncio
import contextlib
import logging
from datetime import datetime
from typing import List, Tuple

from bot.db.repositories.sent_notifications import SentNotificationsRepo
from bot.scheduler.notifier import Notifier

logger = logging.getLogger(__name__)

# نوع العنصر المستحق: (نوع_الهدف، معرّف_الهدف، معلومات)
_DueItem = Tuple[str, int, dict]


def _to_minutes(hhmm: str) -> int:
    """'12:30' → 750."""
    h, m = hhmm.split(":")
    return int(h) * 60 + int(m)


def _subtract_minutes(hhmm: str, minutes: int) -> str:
    """يطرح دقائق من توقيت HH:MM، مع التفاف حول منتصف الليل."""
    total = (_to_minutes(hhmm) - minutes) % (24 * 60)
    return f"{total // 60:02d}:{total % 60:02d}"


def _within(t1: str, t2: str, tolerance: int = 1) -> bool:
    """هل توقيتان متساويان ضمن سماحية دقائق؟"""
    return abs(_to_minutes(t1) - _to_minutes(t2)) <= tolerance


class PrayerScheduler:
    """حلقة asyncio خلفية لاكتشاف أوقات الصلاة وإطلاق التنبيهات."""

    TICK_SECONDS = 30

    def __init__(
        self,
        user_repo,
        group_repo,
        sent_repo: SentNotificationsRepo,
        notifier: Notifier,
        tick_seconds: int = None,
    ):
        self._user_repo = user_repo
        self._group_repo = group_repo
        self._sent_repo = sent_repo
        self._notifier = notifier
        if tick_seconds is not None:
            self.TICK_SECONDS = tick_seconds
        self._task: asyncio.Task | None = None
        self._running = False

    async def start(self) -> None:
        """يبدأ حلقة الجدولة الخلفية."""
        if self._task is not None:
            return
        self._running = True
        self._task = asyncio.create_task(self._loop())
        logger.info("✅ بدأت حلقة جدولة الصلاة (كل %sث)", self.TICK_SECONDS)

    async def stop(self) -> None:
        """يوقف الحلقة بأمان. idempotent."""
        self._running = False
        if self._task:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task
            self._task = None
        logger.info("🛑 توقفت حلقة الجدولة")

    async def _loop(self) -> None:
        """الحلقة الرئيسية — تستيقظ، تنفّذ tick، تنام."""
        while self._running:
            try:
                await self.tick()
            except Exception:
                logger.exception("⚠️ خطأ في دورة الجدولة (ستستأنف)")
            await asyncio.sleep(self.TICK_SECONDS)

    async def tick(self) -> None:
        """دورة واحدة: اكتشف التنبيهات المستحقة الآن وأطلقها.

        قابلة للاختبار بمعزل: تستدعي _find_due_prayers (قابلة للاستبدال)
        ثم _dispatch لكل عنصر.
        """
        due_items = await self._find_due_prayers()
        for target_type, target_id, info in due_items:
            await self._dispatch(target_type, target_id, info)

    async def _find_due_prayers(self) -> List[_DueItem]:
        """يفحص كل الأهداف ويُرجع التنبيهات المستحقة الآن.

        يمكن استبدالها (mock) في الاختبارات لعزل منطق الإرسال.
        """
        now = datetime.utcnow()
        results: List[_DueItem] = []

        # المستخدمون (تنبيه نصي)
        for u in await self._user_repo.list_with_notifications():
            due = self._check_due(
                u.city, u.method, u.asr_method, now, u.enabled_prayers
            )
            if due:
                results.append(("user", u.user_id, due))
            if u.prelude_on:
                prelude = self._check_prelude(
                    u.city,
                    u.method,
                    u.asr_method,
                    now,
                    u.enabled_prayers,
                    u.prelude_minutes,
                )
                if prelude:
                    results.append(("user", u.user_id, prelude))

        # المجموعات (بث أذان)
        for g in await self._group_repo.list_all():
            due = self._check_due(g.city, g.method, g.asr_method, now)
            if due:
                results.append(("group", g.chat_id, due))

        return results

    @staticmethod
    def _check_due(
        city: str,
        method: str,
        asr_method: str,
        now: datetime,
        enabled=None,
    ) -> dict | None:
        """هل حان وقت صلاة الآن لهذه المدينة؟ يُرجع معلومات الصلاة أو None."""
        from bot.prayer.calculator import CityCoordinates, PrayerTimeCalculator

        coords = CityCoordinates.get_city_coords(city)
        if not coords:
            return None
        calc = PrayerTimeCalculator(
            latitude=coords["lat"],
            longitude=coords["lng"],
            timezone=coords["tz"],
            method=method,
            asr_method=asr_method,
            dst=coords.get("dst", False),
            city_name=city,
        )
        times = calc.calculate_times(now)
        now_hhmm = now.strftime("%H:%M")
        prayers = enabled or ["fajr", "dhuhr", "asr", "maghrib", "isha"]
        for p in prayers:
            if p not in times:
                continue
            if _within(times[p], now_hhmm, tolerance=1):
                return {"prayer": p, "time": times[p], "is_prelude": False}
        return None

    @staticmethod
    def _check_prelude(
        city,
        method,
        asr_method,
        now,
        enabled,
        lead_minutes,
    ) -> dict | None:
        """هل اقتربت صلاة بحيث يجب إطلاق المقدمة الآن؟"""
        from bot.prayer.calculator import CityCoordinates, PrayerTimeCalculator

        coords = CityCoordinates.get_city_coords(city)
        if not coords:
            return None
        calc = PrayerTimeCalculator(
            latitude=coords["lat"],
            longitude=coords["lng"],
            timezone=coords["tz"],
            method=method,
            asr_method=asr_method,
            dst=coords.get("dst", False),
            city_name=city,
        )
        times = calc.calculate_times(now)
        now_hhmm = now.strftime("%H:%M")
        prayers = enabled or ["fajr", "dhuhr", "asr", "maghrib", "isha"]
        for p in prayers:
            if p not in times:
                continue
            target = _subtract_minutes(times[p], lead_minutes)
            if _within(target, now_hhmm, tolerance=1):
                return {
                    "prayer": p,
                    "time": times[p],
                    "is_prelude": True,
                    "prelude_key": f"prelude_{p}",
                }
        return None

    async def _dispatch(self, target_type: str, target_id: int, info: dict) -> None:
        """يُرسل تنبيهًا واحدًا مع منع التكرار ومعالجة الأخطاء."""
        prayer = info["prayer"]
        date = datetime.utcnow().strftime("%Y-%m-%d")
        key = info.get("prelude_key", prayer)

        if await self._sent_repo.already_sent(target_id, target_type, key, date):
            return  # سُبق وأُرسل

        try:
            if target_type == "user":
                ok = await self._notifier.notify_user(
                    target_id,
                    prayer,
                    info["time"],
                    info.get("is_prelude", False),
                )
            else:
                ok = await self._notifier.broadcast_group_azan(
                    target_id, prayer, "traditional"
                )
            if ok:
                await self._sent_repo.mark_sent(target_id, target_type, key, date)
        except Exception:
            logger.exception("⚠️ فشل إرسال تنبيه %s لـ %s", prayer, target_id)
