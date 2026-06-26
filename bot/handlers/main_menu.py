#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""القائمة الرئيسية: /start /help /about + back_to_start.

البنية: دوال بناء لوحات المفاتيح والنصوص (نقية، قابلة للاختبار) + register()
الذي يربطها بـ Pyrogram Client.
"""

from bot.decorators import safe_handler

# استيراد Pyrogram كسليًا داخل register لتفصل المعالجات عن النقل


def home_keyboard():
    """لوحة القائمة الرئيسية. دالة نقية قابلة للاختبار."""
    from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "📖 القرآن الكريم (بث + نص + تفسير)", callback_data="quran_menu"
                )
            ],
            [InlineKeyboardButton("📚 الحديث الشريف", callback_data="hadith:books")],
            [
                InlineKeyboardButton(
                    "🤲 أسماء الله الحسنى", callback_data="names:page:0"
                )
            ],
            [
                InlineKeyboardButton(
                    "📿 الأذكار الإسلامية", callback_data="main_adhkar_menu"
                )
            ],
            [
                InlineKeyboardButton(
                    "🕌 أوقات الأذان والصلاة", callback_data="azan_home"
                )
            ],
            [InlineKeyboardButton("📻 راديو القرآن (بث متواصل)", callback_data="radio_info")],
            [InlineKeyboardButton("🧮 حاسبة الزكاة", callback_data="zakat_home")],
            [InlineKeyboardButton("🌙 رمضان", callback_data="ramadan_home")],
            [InlineKeyboardButton("📖 تسميع القرآن", callback_data="memorize_home")],
            [InlineKeyboardButton("📊 إحصائيات البوت", callback_data="stats_home")],
            [InlineKeyboardButton("ℹ️ حول البوت", callback_data="about")],
            [InlineKeyboardButton("🌐 اللغة", callback_data="language_home")],
        ]
    )


WELCOME_TEXT = (
    "🕌 **البوت الإسلامي الموحد** - الإصدار الكامل\n\n"
    "✅ **القرآن الكريم** - استماع + نص + تفسير + بحث\n"
    "✅ **الحديث الشريف** - كتب الحديث الستة\n"
    "✅ **أسماء الله الحسنى** - شرح 99 اسمًا\n"
    "✅ **الأذكار** - 200+ ذكر في 24 تصنيف\n"
    "✅ **الأذان** - أوقات الصلاة + تنبيهات\n"
    "✅ **البث الصوتي** - قرآن وأذان في المكالمات\n"
    "✅ **راديو القرآن** - بث متواصل للسور مع تحكم كامل\n"
    "✅ **حاسبة الزكاة** - زكاة المال والذهب والفضة\n"
    "✅ **رمضان** - أدعية ومواقيت السحور والإفطار\n"
    "✅ **تسميع القرآن** - اختبار حفظ السور\n"
    "✅ **المسبحة الإلكترونية** - 5 أذكار مع حفظ التعداد\n"
    "✅ **التقويم الهجري والقبلة** - تاريخ هجري + اتجاه القبلة\n\n"
    "اختر من القائمة أدناه:"
)

PRIVATE_HELP = (
    "🕌 **البوت الإسلامي الموحد - دليل الاستخدام**\n\n"
    "**📖 القرآن الكريم:**\n"
    "/quran - قائمة القرآن (استماع)\n"
    "/quran_text - عرض نص القرآن مع التفسير\n"
    "/quran_search [كلمة] - بحث في القرآن\n"
    "/radio - راديو القرآن (للمجموعات)\n\n"
    "**📚 الحديث الشريف:**\n"
    "/hadith - مكتبة الحديث (6 كتب)\n"
    "/hadith [كتاب] [رقم] - حديث محدد\n"
    "مثال: `/hadith bukhari 1`\n\n"
    "**🤲 الأذكار والأسماء:**\n"
    "/adhkar - الأذكار الإسلامية\n"
    "/names - أسماء الله الحسنى\n\n"
    "**🕌 الأذان والصلاة:**\n"
    "/azan_setup - إعداد مدينتك\n"
    "/azan_times - أوقات الصلاة اليوم\n"
    "/azan_next - الصلاة التالية\n"
    "/azan_search [مدينة] - البحث عن مدينة"
)

GROUP_HELP = (
    "🕌 **البوت الإسلامي الموحد - أوامر المجموعات**\n\n"
    "**🎙 بث القرآن في المكالمة الصوتية (للمشرفين):**\n"
    "/quran [رقم السورة] - تشغيل سورة في المكالمة\n"
    "مثال: `/quran 1` لسورة الفاتحة\n"
    "/stop - إيقاف البث\n\n"
    "**📻 راديو القرآن (للمشرفين):**\n"
    "/radio - تشغيل راديو القرآن (بث متواصل للسور)\n"
    "/radio stop - إيقاف الراديو\n"
    "• أزرار تحكم: ⏮️ ⏸️ ⏭️ 🔀 🎙️ ⏹️\n\n"
    "**📿 الأذكار التلقائية (للمشرفين):**\n"
    "/adhkar - لوحة تحكم إعدادات الأذكار\n"
    "• تشغيل/إطفاء الأذكار الدورية\n"
    "• ضبط المدة بين الأذكار\n"
    "• تفعيل أذكار الصباح والمساء والجمعة\n\n"
    "**ℹ️ أوامر أخرى:**\n"
    "/start - عرض رسالة الترحيب\n"
    "/help - هذه التعليمات"
)

ABOUT_TEXT = (
    "🕌 **البوت الإسلامي الموحد**\n\n"
    "**يضم ستة أنظمة متكاملة:**\n\n"
    "📖 **القرآن الكريم** - بث صوتي + نص + تفسير + بحث\n"
    "📚 **الحديث الشريف** - كتب الحديث الستة مع البحث\n"
    "🤲 **أسماء الله الحسنى** - شرح وتفسير 99 اسمًا\n"
    "📿 **الأذكار** - 200+ ذكر في 24 تصنيف\n"
    "🕌 **الأذان** - أوقات الصلاة + تنبيهات تلقائية\n"
    "🎙 **البث الصوتي** - قرآن وأذان في المكالمات\n"
    "📻 **راديو القرآن** - بث متواصل للسور\n\n"
    "**الأوامر:** /help"
)


def register(app, deps) -> None:
    """يسجّل أوامر القائمة الرئيسية."""
    from pyrogram import filters

    @app.on_message(filters.command("start"))
    @safe_handler()
    async def start_cmd(client, message):
        if message.chat.type != "private":
            await message.reply_text(GROUP_HELP)
        else:
            await message.reply_text(WELCOME_TEXT, reply_markup=home_keyboard())

    @app.on_message(filters.new_chat_members)
    @safe_handler()
    async def welcome_group(client, message):
        bot_user = await app.get_me()
        if bot_user.id not in [u.id for u in message.new_chat_members]:
            return
        await message.reply_text(
    "🕌 **أهلاً بالبوت الإسلامي الموحد في مجموعتكم!**\n\n"
    "🎙 **بث القرآن**: استخدم `/quran [رقم]` في المكالمة الصوتية (للمشرفين)\n"
    "📻 **راديو القرآن**: استخدم `/radio` لبث متواصل للسور (للمشرفين)\n"
    "📿 **الأذكار**: استخدم `/adhkar` لتفعيل الأذكار التلقائية (للمشرفين)\n\n"
    "📌 **للتعليمات الكاملة:** /help"
        )

    @app.on_message(filters.command("help"))
    @safe_handler()
    async def help_cmd(client, message):
        if message.chat.type != "private":
            await message.reply_text(GROUP_HELP)
        else:
            await message.reply_text(PRIVATE_HELP)

    @app.on_callback_query(filters.regex("^(back_to_start|about|radio_info|zakat_home|ramadan_home|memorize_home|stats_home|language_home)$"))
    @safe_handler()
    async def home_handler(client, callback_query):
        data = callback_query.data
        if data == "about":
            await callback_query.message.edit_text(ABOUT_TEXT, reply_markup=home_keyboard())
        elif data == "radio_info":
            await callback_query.message.edit_text(
                "📻 **راديو القرآن**\n\nبث متواصل لسور القرآن الكريم بدون توقف مثل الراديو.\n\n"
                "**للاستخدام في المجموعات (للمشرفين):**\n"
                "• `/radio` - بدء الراديو في المكالمة الصوتية\n"
                "• `/radio stop` - إيقاف الراديو\n\n"
                "**أزرار التحكم:**\n⏮️ ⏸️ ⏭️ 🔀 🎙️ ⏹️ ℹ️",
                reply_markup=home_keyboard(),
            )
        elif data == "zakat_home":
            await callback_query.message.edit_text(
                "🧮 **حاسبة الزكاة**\n\n"
                "• `/zakat` - عرض تصنيفات الزكاة\n"
                "• `/zakat حساب [المبلغ]` - حساب زكاة المال (2.5%)\n"
                "• `/zakat [التصنيف]` - معلومات عن نوع الزكاة\n\n"
                "**نصاب الذهب:** 85 جرام\n**نصاب الفضة:** 595 جرام",
                reply_markup=home_keyboard(),
            )
        elif data == "ramadan_home":
            await callback_query.message.edit_text(
                "🌙 **رمضان**\n\n"
                "• `/ramadan` - أدعية ومواقيت رمضان\n\n"
                "**مواقيت رمضان:**\n"
                "• السحور: قبل الفجر بـ 10-20 دقيقة\n"
                "• الإمساك: عند أذان الفجر\n"
                "• الإفطار: عند أذان المغرب",
                reply_markup=home_keyboard(),
            )
        elif data == "memorize_home":
            await callback_query.message.edit_text(
                "📖 **تسميع القرآن**\n\n"
                "• `/memorize` - عرض التعليمات\n"
                "• `/memorize [رقم]` - اختبار سورة محددة\n"
                "• `/memorize random` - سورة عشوائية\n"
                "• `/memorize list` - قائمة السور مع pagination",
                reply_markup=home_keyboard(),
            )
        elif data == "stats_home":
            await callback_query.message.edit_text(
                "📊 **إحصائيات البوت**\n\n"
                "• `/stats` - إحصائيات استخدام الأوامر\n"
                "_إحصاءات الاستخدام في الذاكرة._",
                reply_markup=home_keyboard(),
            )
        elif data == "language_home":
            await callback_query.message.edit_text(
                "🌐 **تغيير اللغة**\n\n"
                "• العربية - `/lang ar`\n"
                "• English - `/lang en`\n"
                "• اردو - `/lang ur`\n"
                "• Bahasa Indonesia - `/lang id`",
                reply_markup=home_keyboard(),
            )
        else:
            await callback_query.message.edit_text("🕌 **القائمة الرئيسية**\n\nاختر من القائمة:", reply_markup=home_keyboard())
        await callback_query.answer()
