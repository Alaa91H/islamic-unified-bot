from bot.decorators import safe_handler

_PAGE_SIZE = 10


def register(app, deps) -> None:
    from pyrogram import filters
    from pyrogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup

    from bot.data.quran_data import AYAH_COUNTS, get_ayah_text, get_tafsir, search_quran
    from bot.data.surahs import SURAHS

    @app.on_message(filters.private & filters.command("quran_text"))
    @safe_handler()
    async def quran_text_cmd(client, message):
        surahs_kb = []
        row = []
        for i in range(1, 115):
            row.append(InlineKeyboardButton(str(i), callback_data=f"qts:{i}:0"))
            if len(row) == 10:
                surahs_kb.append(row)
                row = []
        if row:
            surahs_kb.append(row)
        surahs_kb.append(
            [
                InlineKeyboardButton(
                    "🔍 بحث في القرآن", switch_inline_query_current_chat=""
                )
            ]
        )
        surahs_kb.append(
            [InlineKeyboardButton("🔙 رجوع", callback_data="back_to_start")]
        )

        await message.reply_text(
            "📖 **القرآن الكريم - النص والتفسير**\n\nاختر رقم السورة لعرض آياتها:",
            reply_markup=InlineKeyboardMarkup(surahs_kb),
        )

    @app.on_callback_query(filters.regex("^qts:"))
    @safe_handler()
    async def quran_text_callback(client, cq: CallbackQuery):
        parts = cq.data.split(":")
        surah = int(parts[1])
        page = int(parts[2]) if len(parts) > 2 else 0
        name = SURAHS.get(surah, "")
        total = AYAH_COUNTS.get(surah, 0)

        if page == 0 or parts[-1] == "info":
            buttons = [
                [InlineKeyboardButton("📖 عرض الآيات", callback_data=f"qts:{surah}:1")],
                [
                    InlineKeyboardButton(
                        "🔍 تفسير السورة", callback_data=f"qts:{surah}:1:tafsir"
                    )
                ],
                [
                    InlineKeyboardButton(
                        "🎙 الاستماع", callback_data=f"quran_surah:{surah}"
                    )
                ],
                [InlineKeyboardButton("🔙 رجوع", callback_data="quran_text")],
            ]
            await cq.message.edit_text(
                f"📖 **سورة {name}**\n"
                f"───\n"
                f"• رقم السورة: {surah}\n"
                f"• عدد الآيات: {total}\n"
                f"• الجزء: {_get_juz(surah)}\n\n"
                f"اختر من القائمة:",
                reply_markup=InlineKeyboardMarkup(buttons),
            )
            await cq.answer()
            return

        start = (page - 1) * _PAGE_SIZE + 1
        end = min(start + _PAGE_SIZE - 1, total)

        lines = []
        show_tafsir = "tafsir" in parts
        for a in range(start, end + 1):
            text = await get_ayah_text(surah, a)
            if text:
                lines.append(f"**{a}** - {text}")
                if show_tafsir:
                    t = await get_tafsir(surah, a)
                    if t:
                        lines.append(f"  _{t}_\n")

        nav_buttons = []
        if page > 1:
            nav_buttons.append(
                InlineKeyboardButton(
                    "⬅️ السابق",
                    callback_data=f"qts:{surah}:{page - 1}"
                    + (":tafsir" if show_tafsir else ""),
                )
            )
        if end < total:
            nav_buttons.append(
                InlineKeyboardButton(
                    "التالي ➡️",
                    callback_data=f"qts:{surah}:{page + 1}"
                    + (":tafsir" if show_tafsir else ""),
                )
            )

        extra = []
        t_label = "🔍 إخفاء التفسير" if show_tafsir else "🔍 إظهار التفسير"
        t_data = f"qts:{surah}:{page}" + ("" if show_tafsir else ":tafsir")
        extra.append([InlineKeyboardButton(t_label, callback_data=t_data)])
        extra.append(
            [
                InlineKeyboardButton(
                    "ℹ️ معلومات السورة", callback_data=f"qts:{surah}:0:info"
                ),
                InlineKeyboardButton("🔙 رجوع", callback_data="quran_text"),
            ]
        )

        text = f"📖 **{name}** - صفحة {page}\n───\n" + "\n".join(lines)
        if len(text) > 4000:
            text = text[:4000] + "\n\n_...يتبع_"

        await cq.message.edit_text(
            text,
            reply_markup=InlineKeyboardMarkup(
                [nav_buttons] + extra if nav_buttons else extra
            ),
        )
        await cq.answer()

    @app.on_message(filters.private & filters.command("quran_search"))
    @safe_handler()
    async def quran_search_cmd(client, message):
        keyword = " ".join(message.command[1:])
        if not keyword:
            await message.reply_text(
                "❌ استخدم: `/quran_search [كلمة]`\nمثال: `/quran_search رحمة`"
            )
            return

        await message.reply_text(f"🔍 جاري البحث عن «{keyword}»...")
        results = await search_quran(keyword)

        if not results:
            await message.reply_text(f"❌ لا توجد نتائج لـ «{keyword}`")
            return

        lines = [f"🔍 **نتائج البحث عن:** {keyword}\n"]
        for r in results[:15]:
            surah_n = r.get("surah", {}).get("number", 0)
            ayah_n = r.get("numberInSurah", 0)
            text = r.get("text", "")[:100]
            lines.append(f"**{surah_n}:{ayah_n}** {text}...\n")

        await message.reply_text("\n".join(lines))


def _get_juz(surah: int) -> str:
    if surah <= 2:
        return "1"
    if surah <= 4:
        return "4-5"
    if surah <= 6:
        return "6-7"
    if surah <= 9:
        return "8-11"
    if surah <= 16:
        return "12-14"
    if surah <= 29:
        return "15-21"
    if surah <= 39:
        return "22-24"
    if surah <= 67:
        return "25-29"
    if surah <= 77:
        return "30"
    if surah <= 114:
        return "30"
    return "1"
