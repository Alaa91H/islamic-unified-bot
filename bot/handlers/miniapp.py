"""معالج بيانات Telegram Mini App.

يعتمد المسار على ``web_app_data`` الذي يرسله Telegram نفسه، ولا يفتح نقطة HTTP
عامة بلا تحقق. تتحقق الدالة الخالصة من الحمولة قبل لمس قاعدة البيانات.
"""

from __future__ import annotations

import json
from typing import Any

from pyrogram import filters

from bot.i18n.messages import message_for
from bot.prayer.calculator import CityCoordinates

ALLOWED_LANGUAGES = {"ar", "en"}
MAX_PAYLOAD_BYTES = 1024


def _has_web_app_data(_, __, message) -> bool:
    """فلتر متوافق مع Pyrogram 2 لاكتشاف رسالة Telegram Web App."""
    return getattr(message, "web_app_data", None) is not None


web_app_data_filter = filters.create(_has_web_app_data, name="WebAppData")


def validate_miniapp_payload(raw_payload: str) -> dict[str, Any]:
    """تحقق من حمولة Mini App وأرجع الحقول المسموحة فقط."""
    if len(raw_payload.encode("utf-8")) > MAX_PAYLOAD_BYTES:
        raise ValueError("البيانات المرسلة أكبر من المسموح")
    try:
        payload = json.loads(raw_payload)
    except json.JSONDecodeError as exc:
        raise ValueError("بيانات Mini App غير صالحة") from exc
    if not isinstance(payload, dict) or payload.get("source") != "miniapp":
        raise ValueError("مصدر البيانات غير صالح")

    city = payload.get("city")
    if not isinstance(city, str) or CityCoordinates.get_city_coords(city) is None:
        raise ValueError("المدينة غير مدعومة")

    language = payload.get("language")
    if language not in ALLOWED_LANGUAGES:
        raise ValueError("اللغة غير مدعومة")
    notifications = payload.get("notifications")
    if not isinstance(notifications, bool):
        raise ValueError("قيمة التنبيهات غير صالحة")

    return {"city": city, "language": language, "notifications_on": notifications}


def register(app, deps) -> None:
    """تسجيل معالج خاص لمستخدم أرسل إعدادات Mini App عبر Telegram."""

    @app.on_message(filters.private & web_app_data_filter)
    async def save_miniapp_preferences(_, message) -> None:
        user_id = message.from_user.id if message.from_user else None
        if user_id is None:
            return
        try:
            payload = validate_miniapp_payload(message.web_app_data.data)
            settings = await deps.user_repo.get(user_id)
            if settings is None:
                await message.reply_text(
                    message_for(payload["language"], "miniapp_setup_first")
                )
                return
            await deps.user_repo.update_partial(user_id, **payload)
            await message.reply_text(message_for(payload["language"], "miniapp_saved"))
        except ValueError:
            await message.reply_text(message_for("ar", "miniapp_invalid"))
