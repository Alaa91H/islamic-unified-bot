#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""إرسال التنبيهات: نص للمستخدم (خاص) + بث أذان للمجموعة (voice chat).

المسؤولية الوحيدة: ترجمة "حان وقت صلاة" إلى إجراء فعلي (رسالة/بث).
لا يعرف شيئًا عن الجدولة أو قاعدة البيانات — يُستدعى من PrayerScheduler.
"""

import logging
from typing import Optional

from bot.data.sources import AZAN_SOURCES

logger = logging.getLogger(__name__)

_PRAYER_EMOJI = {
    "fajr": "🌅",
    "dhuhr": "☀️",
    "asr": "⛅",
    "maghrib": "🌆",
    "isha": "🌙",
}
_PRAYER_NAME = {
    "fajr": "الفجر",
    "dhuhr": "الظهر",
    "asr": "العصر",
    "maghrib": "المغرب",
    "isha": "العشاء",
}


class Notifier:
    """يُرسل التنبيهات عبر Pyrogram ويُدير بث الأذان عبر StreamManager."""

    def __init__(self, app, stream_manager):
        self._app = app
        self._stream = stream_manager

    async def notify_user(
        self,
        user_id: int,
        prayer: str,
        prayer_time: str,
        is_prelude: bool = False,
    ) -> bool:
        """إرسال رسالة نصية لمستخدم في الخاص. يُرجع True عند النجاح."""
        name = _PRAYER_NAME.get(prayer, prayer)
        emoji = _PRAYER_EMOJI.get(prayer, "🕌")
        if is_prelude:
            text = f"{emoji} سيبدأ أذان {name} خلال دقائق\n🕐 {prayer_time}"
        else:
            text = f"{emoji} حان وقت صلاة {name}\n🕐 {prayer_time}\nحي على الصلاة"
        try:
            await self._app.send_message(user_id, text)
            logger.info("📩 تنبيه أُرسل للمستخدم %s (%s)", user_id, prayer)
            return True
        except Exception as e:
            logger.error("❌ فشل إرسال التنبيه لـ %s: %s", user_id, e)
            return False

    async def broadcast_group_azan(
        self,
        chat_id: int,
        prayer: str,
        azan_source: str = "traditional",
    ) -> bool:
        """بث الأذان في voice chat المجموعة + رسالة نصية. يُرجع True عند النجاح."""
        name = _PRAYER_NAME.get(prayer, prayer)
        emoji = _PRAYER_EMOJI.get(prayer, "🕌")
        url = self._get_azan_url(prayer, azan_source)
        if not url:
            logger.warning(
                "⚠️ لا يوجد رابط أذان لـ %s/%s — إرسال نص فقط",
                azan_source,
                prayer,
            )
            # نرسل نصًا على الأقل إن تعذّر البث
            try:
                await self._app.send_message(
                    chat_id, f"{emoji} حان وقت صلاة {name}\n🕐 الأذان"
                )
                return True
            except Exception as e:
                logger.error("❌ فشل الإرسال النصي في %s: %s", chat_id, e)
                return False
        try:
            ok = await self._stream.play(
                chat_id, url, f"أذان {name}", loop=False, duration_min=4
            )
            if ok:
                await self._app.send_message(
                    chat_id,
                    f"{emoji} حان وقت صلاة {name}\n🕌 الأذان يبث الآن",
                )
            return ok
        except Exception as e:
            logger.error("❌ فشل بث الأذان في %s: %s", chat_id, e)
            return False

    @staticmethod
    def _get_azan_url(prayer: str, source: str) -> Optional[str]:
        """يُرجع رابط الأذان لمصدر/صلاة معيّنين، أو None."""
        return AZAN_SOURCES.get(source, {}).get(prayer)
