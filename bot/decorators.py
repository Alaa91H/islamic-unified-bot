#!/usr/bin/env python3
"""Decorators للتحقق من الصلاحيات ومعالجة الأخطاء موحّدة.

تُستخدم عبر كل المعالجات لتقليل التكرار وضمان سلوك متّسق:
- owner_only: فقط مالك البوت.
- admin_only: مشرفو المجموعة (أو المالك).
- safe_handler: يلتقط الاستثناءات ويرد برسالة أنيقة بدل انهيار الزر.
"""

import contextlib
import functools
import logging

logger = logging.getLogger(__name__)


async def _reply_or_answer(update, text: str) -> None:
    """يرد على message أو callback query بالطريقة المتاحة."""
    reply = getattr(update, "reply_text", None)
    if not callable(reply):
        reply = getattr(getattr(update, "message", None), "reply_text", None)
    if callable(reply):
        await reply(text)
        return

    answer = getattr(update, "answer", None)
    if callable(answer):
        try:
            await answer(text, show_alert=True)
        except TypeError:
            await answer(text)


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


def admin_only(app, settings=None):
    """للمجموعات: يسمح للمشرفين أو للمالك. يتحقق عبر client.get_chat_member."""

    def decorator(func):
        @functools.wraps(func)
        async def wrapper(client, update, *args, **kwargs):
            user = getattr(update, "from_user", None)
            if user:
                uid = user.id
                if settings and settings.is_owner(uid):
                    logger.info("👑 سماح للمالك %s", uid)
                    return await func(client, update, *args, **kwargs)
                logger.info(
                    "🔍 فحص مشرف: uid=%s settings=%s", uid, settings is not None
                )
            msg = getattr(update, "message", None) or update
            chat = getattr(msg, "chat", None)
            chat_id = getattr(chat, "id", None) if chat else None
            if not user or not chat_id:
                await _reply_or_answer(update, "❌ تعذّر التحقق من صلاحيات المشرف")
                logger.warning("🚫 منع أمر إداري بلا مستخدم أو chat_id")
                return None
            if user and chat_id:
                try:
                    member = await client.get_chat_member(chat_id, user.id)
                    status = str(member.status).lower()
                    if status not in (
                        "administrator",
                        "creator",
                        "owner",
                        "chatmemberstatus.administrator",
                        "chatmemberstatus.owner",
                    ):
                        await _reply_or_answer(update, "❌ هذا الأمر للمشرفين فقط")
                        return None
                except Exception as e:
                    logger.warning("⚠️ تعذّر التحقق من المشرف: %s", e)
                    await _reply_or_answer(update, "❌ تعذّر التحقق من صلاحيات المشرف")
                    return None
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
            except Exception as e:
                err_name = type(e).__name__
                if "MessageNotModified" in err_name or "MESSAGE_NOT_MODIFIED" in str(e):
                    return  # تجاهل صامت — تحرير بنفس المحتوى
                logger.exception("⚠️ خطأ في معالج")
                # جرّب الرد بالطريقة المتاحة (رسالة أو زر)
                reply = (
                    getattr(update, "reply_text", None)
                    or getattr(getattr(update, "message", None), "edit_text", None)
                    or getattr(update, "answer", None)
                )
                if reply:
                    with contextlib.suppress(Exception):
                        await reply(f"❌ حدث خطأ: {str(e)[:100]}")

        return wrapper

    return decorator
