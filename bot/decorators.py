#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Decorators للتحقق من الصلاحيات ومعالجة الأخطاء موحّدة.

تُستخدم عبر كل المعالجات لتقليل التكرار وضمان سلوك متّسق:
- owner_only: فقط مالك البوت.
- admin_only: مشرفو المجموعة (أو المالك).
- safe_handler: يلتقط الاستثناءات ويرد برسالة أنيقة بدل انهيار الزر.
"""

import functools
import logging

logger = logging.getLogger(__name__)


def owner_only(settings):
    """يسمح فقط للمالك. يتطلب message.from_user.id."""

    def decorator(func):
        @functools.wraps(func)
        async def wrapper(client, message, *args, **kwargs):
            user_id = message.from_user.id if message.from_user else None
            if not settings.is_owner(user_id):
                await message.reply_text("❌ لا تملك صلاحية استخدام هذا الأمر")
                logger.warning("🚫 محاولة وصول غير مصرّح: %s", user_id)
                return None
            return await func(client, message, *args, **kwargs)

        return wrapper

    return decorator


def admin_only(app):
    """للمجموعات: يسمح للمشرفين أو للمالك. يتحقق عبر client.get_chat_member."""

    def decorator(func):
        @functools.wraps(func)
        async def wrapper(client, update, *args, **kwargs):
            user = getattr(update, "from_user", None)
            msg = getattr(update, "message", None) or update
            chat = getattr(msg, "chat", None)
            chat_id = getattr(chat, "id", None) if chat else None
            if user and chat_id:
                try:
                    member = await client.get_chat_member(chat_id, user.id)
                    if member.status not in ("administrator", "creator"):
                        await update.reply_text("❌ هذا الأمر للمشرفين فقط")
                        return None
                except Exception as e:  # noqa: BLE001
                    logger.warning("⚠️ تعذّر التحقق من المشرف: %s", e)
            return await func(client, update, *args, **kwargs)

        return wrapper

    return decorator


def safe_handler():
    """يلتقط الاستثناءات ويرد برسالة أنيقة بدل انهيار الزر/الأمر."""

    def decorator(func):
        @functools.wraps(func)
        async def wrapper(client, update, *args, **kwargs):
            try:
                return await func(client, update, *args, **kwargs)
            except Exception as e:  # noqa: BLE001
                logger.exception("⚠️ خطأ في معالج")
                # جرّب الرد بالطريقة المتاحة (رسالة أو زر)
                reply = (
                    getattr(update, "reply_text", None)
                    or getattr(getattr(update, "message", None), "edit_text", None)
                    or getattr(update, "answer", None)
                )
                if reply:
                    try:
                        await reply(f"❌ حدث خطأ: {str(e)[:100]}")
                    except Exception:  # noqa: BLE001
                        pass

        return wrapper

    return decorator
