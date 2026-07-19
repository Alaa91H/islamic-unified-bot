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
                InlineKeyboardButton("📖 القرآن الكريم", callback_data="quran_menu"),
                InlineKeyboardButton("📚 الحديث الشريف", callback_data="hadith:books"),
            ],
            [
                InlineKeyboardButton("🤲 الأذكار", callback_data="main_adhkar_menu"),
                InlineKeyboardButton("🕌 الأذان والصلاة", callback_data="azan_home"),
            ],
            [
                InlineKeyboardButton("📻 راديو القرآن", callback_data="radio_info"),
                InlineKeyboardButton("🧮 الزكاة", callback_data="zakat_home"),
            ],
            [
                InlineKeyboardButton("🌙 رمضان", callback_data="ramadan_home"),
                InlineKeyboardButton("📖 تسميع القرآن", callback_data="memorize_home"),
            ],
            [
                InlineKeyboardButton("🎛️ لوحة التحكم", callback_data="panel_quran"),
                InlineKeyboardButton("🌐 اللغة", callback_data="language_home"),
            ],
            [
                InlineKeyboardButton("📊 الإحصائيات", callback_data="stats_home"),
                InlineKeyboardButton("ℹ️ حول البوت", callback_data="about"),
            ],
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
    "✅ **لوحة التحكم** - /panel (مركزية) + /control (للمجموعات)\n"
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
    "/azan_search [مدينة] - البحث عن مدينة\n"
    "/hijri - التقويم الهجري\n"
    "/qibla [مدينة] - اتجاه القبلة\n"
    "/calendar - التقويم الإسلامي\n\n"
    "**🎛️ لوحة التحكم:**\n"
    "/panel - لوحة التحكم المركزية\n"
    "/commands - جميع الأوامر\n"
    "/daily - جرعتك اليومية\n"
    "/stats - إحصائيات الاستخدام"
)

GROUP_HELP = (
    "🕌 **البوت الإسلامي الموحد — أوامر المجموعات**\n\n"
    "⚠️ **ملاحظة مهمة**: البوت لا يستطيع إنشاء المكالمة الصوتية.\n"
    "يجب على أحد المشرفين بدء مكالمة صوتية في المجموعة أولاً،\n"
    "ثم استخدام الأوامر أدناه للتحكم في البث.\n\n"
    "━━━━━━━━━━━━━━━━\n"
    "**🎙 بث القرآن في المكالمة الصوتية** *(للمشرفين)*\n"
    "━━━━━━━━━━━━━━━━\n"
    "▫️ `/quran [رقم السورة]` ← تشغيل سورة مباشر\n"
    "   مثال: `/quran 1` → الفاتحة، `/quran 67` → الملك\n"
    "▫️ `/stop` ← إيقاف البث وإغلاق المكالمة\n"
    "▫️ عند التشغيل تظهر أزرار: ⏹️ إيقاف | 🔙 لوحة التحكم\n\n"
    "━━━━━━━━━━━━━━━━\n"
    "**🎛️ لوحة التحكم الشاملة** *(للمشرفين)*\n"
    "━━━━━━━━━━━━━━━━\n"
    "▫️ `/control` ← قائمة أزرار متكاملة:\n"
    "   📖 تشغيل سورة | 📻 راديو القرآن\n"
    "   🛑 إيقاف البث | ℹ️ حالة البث\n"
    "   🤲 إعدادات الأذكار | 🕌 أوقات الصلاة\n"
    "   ⚙️ إعدادات المجموعة\n\n"
    "━━━━━━━━━━━━━━━━\n"
    "**📻 راديو القرآن — بث متواصل** *(للمشرفين)*\n"
    "━━━━━━━━━━━━━━━━\n"
    "▫️ `/radio` ← تشغيل راديو (سور متتالية بلا توقف)\n"
    "▫️ `/radio stop` ← إيقاف الراديو\n"
    "▫️ أزرار التحكم أثناء البث:\n"
    "   ⏮️ السابق | ⏸️/▶️ إيقاف/استئناف | ⏭️ التالي\n"
    "   🔀 عشوائي/تسلسلي | 🎙️ تغيير القارئ | ⏹️ إيقاف\n\n"
    "━━━━━━━━━━━━━━━━\n"
    "**📿 الأذكار التلقائية** *(للمشرفين)*\n"
    "━━━━━━━━━━━━━━━━\n"
    "▫️ `/adhkar` ← لوحة تحكم الأذكار:\n"
    "   • 🔁 الذكر الدوري (كل مدة زمنية)\n"
    "   • 🌅 أذكار الصباح (يومياً)\n"
    "   • 🌆 أذكار المساء (يومياً)\n"
    "   • 🕌 أذكار الجمعة (يوم الجمعة)\n\n"
    "━━━━━━━━━━━━━━━━\n"
    "**ℹ️ أوامر عامة**\n"
    "━━━━━━━━━━━━━━━━\n"
    "▫️ `/start` ← رسالة الترحيب\n"
    "▫️ `/help` ← هذه التعليمات\n\n"
    "💡 *جميع أوامر البث تتطلب وجود مكالمة صوتية في المجموعة*\n"
    "💡 *يمكنك استخدام `/panel` في الخاص للوحة تحكم مركزية*"
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
            "🎛️ **لوحة التحكم**: استخدم `/control` للتحكم الكامل (للمشرفين)\n"
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

    @app.on_message(filters.command("panel"))
    @safe_handler()
    async def panel_cmd(client, message):
        from pyrogram.types import InlineKeyboardButton

        from bot.handlers.ui import markup_with_bottom_controls

        kb = markup_with_bottom_controls(
            [
                [InlineKeyboardButton("📖 القرآن الكريم", callback_data="panel_quran")],
                [InlineKeyboardButton("🕌 الأذان والصلاة", callback_data="panel_azan")],
                [
                    InlineKeyboardButton(
                        "🤲 الأذكار والأدعية", callback_data="panel_adhkar"
                    )
                ],
                [InlineKeyboardButton("📚 الحديث", callback_data="panel_hadith")],
                [InlineKeyboardButton("🧮 الزكاة", callback_data="panel_zakat")],
                [InlineKeyboardButton("📊 الإحصائيات", callback_data="stats_home")],
                [InlineKeyboardButton("⚙️ الإعدادات", callback_data="panel_settings")],
            ],
            home_callback="back_to_start",
        )
        await message.reply_text(
            "🎛️ **لوحة التحكم المركزية**\nاختر القسم:", reply_markup=kb
        )

    @app.on_callback_query(
        filters.regex("^panel_(quran|azan|adhkar|hadith|zakat|settings)$")
    )
    @safe_handler()
    async def panel_sections(client, cq):
        section = cq.data.split("_", 1)[1]
        from bot.handlers.ui import markup_with_bottom_controls

        texts = {
            "quran": (
                "📖 **القرآن الكريم**\n\n"
                "/quran - قائمة السور\n/quran_text - النص والتفسير\n/quran_search - بحث\n"
                "/quran [رقم] - بث سورة\n/radio - راديو القرآن\n/download - تحميل MP3"
            ),
            "azan": (
                "🕌 **الأذان والصلاة**\n\n"
                "/azan_setup - إعداد المدينة\n/azan_times - أوقات الصلاة\n/azan_next - الصلاة التالية\n"
                "/azan_settings - الإعدادات\n/qibla [مدينة] - القبلة\n/hijri - التاريخ الهجري\n"
                "/prayer [مدينة] - أوقات مدينة"
            ),
            "adhkar": (
                "🤲 **الأذكار والأدعية**\n\n"
                "/adhkar - الأذكار (24 تصنيفاً)\n/dua - الأدعية الجامعة\n/tasbih - مسبحة\n"
                "/daily - جرعتك اليومية\n/names - أسماء الله الحسنى"
            ),
            "hadith": (
                "📚 **الحديث النبوي**\n\n"
                "/hadith - مكتبة الحديث (6 كتب)\n/hadith [كتاب] [رقم] - حديث محدد"
            ),
            "zakat": (
                "🧮 **الزكاة**\n\n"
                "/zakat - معلومات الزكاة\n/zakat حساب [المبلغ] - حساب الزكاة"
            ),
            "settings": (
                "⚙️ **الإعدادات**\n\n"
                "/language - تغيير اللغة\n/azan_settings - إعدادات الأذان\n"
                "/commands - جميع الأوامر"
            ),
        }
        await cq.message.edit_text(
            texts.get(section, "❌ قسم غير معروف"),
            reply_markup=markup_with_bottom_controls(
                [], back_callback="back_to_start", home_callback=None
            ),
        )

    @app.on_callback_query(filters.regex("^ui:(close|noop)$"))
    @safe_handler()
    async def common_ui_handler(client, cq):
        if cq.data == "ui:close":
            await cq.message.delete()
        await cq.answer()

    @app.on_callback_query(
        filters.regex(
            "^(back_to_start|about|radio_info|zakat_home|ramadan_home|memorize_home|stats_home|language_home)$"
        )
    )
    @safe_handler()
    async def home_handler(client, callback_query):
        data = callback_query.data
        if data == "about":
            await callback_query.message.edit_text(
                ABOUT_TEXT, reply_markup=home_keyboard()
            )
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
            await callback_query.message.edit_text(
                "🕌 **القائمة الرئيسية**\n\nاختر من القائمة:",
                reply_markup=home_keyboard(),
            )
        await callback_query.answer()
