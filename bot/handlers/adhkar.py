#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""معالجات الأذكار.

منطق البناء (لوحات/نصوص) في دوال نقية قابلة للاختبار؛ التسجيل في register().
يستخدم bot.data.adhkar المدموج (12 فئة / 33 ذكرًا).
"""

from bot.data.adhkar import ADHKAR, ADHKAR_CATEGORIES
from bot.decorators import safe_handler


def categories_keyboard():
    """لوحة فئات الأذكار (مع زر العودة). دالة نقية."""
    from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

    kb = [
        [InlineKeyboardButton(v, callback_data=f"category_{k}")]
        for k, v in ADHKAR_CATEGORIES.items()
    ]
    kb.append([InlineKeyboardButton("🔙 العودة", callback_data="back_to_start")])
    return InlineKeyboardMarkup(kb)


def items_keyboard(category):
    """لوحة عناصر فئة معينة. تُرجع None إذا الفئة غير معروفة."""
    from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

    items = ADHKAR.get(category, [])
    if not items:
        return None
    kb = [
        [
            InlineKeyboardButton(
                f"{i + 1}. {it['title'][:35]}",
                callback_data=f"adhkar_{category}_{i}",
            )
        ]
        for i, it in enumerate(items)
    ]
    kb.append([InlineKeyboardButton("🔙 الرجوع", callback_data="main_adhkar_menu")])
    return InlineKeyboardMarkup(kb)


def item_text(category, idx):
    """نص عرض ذكر معين. تُرجع (text, keyboard) أو None."""
    from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

    items = ADHKAR.get(category, [])
    if idx < 0 or idx >= len(items):
        return None
    it = items[idx]
    text = (
        f"🕌 **{it['title']}**\n\n"
        f"📝 **النص:**\n{it['text']}\n\n"
        f"✨ **الفضل:**\n{it['benefit']}"
    )
    kb = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("🔙 الرجوع", callback_data=f"category_{category}")],
            [InlineKeyboardButton("🏠 الرئيسية", callback_data="back_to_start")],
        ]
    )
    return text, kb


def register(app, deps) -> None:
    """يسجّل أوامر/أزرار الأذكار."""
    from pyrogram import filters

    @app.on_message(filters.command("adhkar"))
    @safe_handler()
    async def adhkar_cmd(client, message):
        await message.reply_text(
            "📿 **الأذكار الإسلامية الشاملة**\n\nاختر الفئة:",
            reply_markup=categories_keyboard(),
        )

    @app.on_callback_query(filters.regex("^main_adhkar_menu$"))
    @safe_handler()
    async def menu_handler(client, callback_query):
        await callback_query.message.edit_text(
            "📿 **اختر فئة الأذكار:**", reply_markup=categories_keyboard()
        )
        await callback_query.answer()

    @app.on_callback_query(filters.regex("^category_"))
    @safe_handler()
    async def category_handler(client, callback_query):
        category = callback_query.data.replace("category_", "")
        title = ADHKAR_CATEGORIES.get(category, category)
        kb = items_keyboard(category)
        if kb is None:
            await callback_query.answer("❌ فئة غير معروفة", show_alert=True)
            return
        await callback_query.message.edit_text(f"📿 **{title}:**", reply_markup=kb)
        await callback_query.answer()

    @app.on_callback_query(filters.regex("^adhkar_"))
    @safe_handler()
    async def item_handler(client, callback_query):
        parts = callback_query.data.replace("adhkar_", "").split("_")
        category, idx = parts[0], int(parts[1])
        result = item_text(category, idx)
        if result is None:
            await callback_query.answer("❌ ذكر غير موجود", show_alert=True)
            return
        text, kb = result
        await callback_query.message.edit_text(text, reply_markup=kb)
        await callback_query.answer()
