from bot.decorators import safe_handler
from bot.handlers.ui import markup_with_bottom_controls


def surahs_keyboard(page: int = 0):
    from pyrogram.types import InlineKeyboardButton

    from bot.data.surahs import SURAHS

    items_per_page = 20
    keys = sorted(SURAHS.keys())
    total = len(keys)
    start = page * items_per_page
    end = min(start + items_per_page, total)
    kb = []
    for i in range(start, end, 2):
        row = []
        row.append(
            InlineKeyboardButton(
                f"{keys[i]}. {SURAHS[keys[i]]}", callback_data=f"quran_surah:{keys[i]}"
            )
        )
        if i + 1 < end:
            row.append(
                InlineKeyboardButton(
                    f"{keys[i + 1]}. {SURAHS[keys[i + 1]]}",
                    callback_data=f"quran_surah:{keys[i + 1]}",
                )
            )
        kb.append(row)

    nav = []
    if page > 0:
        nav.append(
            InlineKeyboardButton("⬅️ السابق", callback_data=f"quran_page:{page - 1}")
        )
    if end < total:
        nav.append(
            InlineKeyboardButton("التالي ➡️", callback_data=f"quran_page:{page + 1}")
        )
    if nav:
        kb.append(nav)

    return markup_with_bottom_controls(
        kb, back_callback="quran_menu", back_label="🔙 القرآن"
    )


def reciters_keyboard():
    from pyrogram.types import InlineKeyboardButton

    from bot.data.sources import QURANIC_RECITERS

    kb = []
    for key, info in QURANIC_RECITERS.items():
        kb.append(
            [
                InlineKeyboardButton(
                    f"🎙️ {info['name']}", callback_data=f"quran_reciter:{key}"
                )
            ]
        )
    return markup_with_bottom_controls(
        kb, back_callback="quran_menu", back_label="🔙 القرآن"
    )


def register(app, deps) -> None:
    from pyrogram import filters

    @app.on_message(filters.private & filters.command("quran"))
    @safe_handler()
    async def quran_cmd(client, message):
        from pyrogram.types import InlineKeyboardButton

        await message.reply_text(
            "📖 **القرآن الكريم**\n\nاختر طريقة:",
            reply_markup=markup_with_bottom_controls(
                [
                    [
                        InlineKeyboardButton(
                            "📚 قائمة السور", callback_data="quran_list"
                        )
                    ],
                    [InlineKeyboardButton("🎙️ القرّاء", callback_data="quran_reciters")],
                ],
                back_callback="back_to_start",
                home_callback=None,
            ),
        )

    @app.on_callback_query(filters.regex("^quran_menu$"))
    @safe_handler()
    async def quran_menu_handler(client, cq):
        from pyrogram.types import InlineKeyboardButton

        await cq.message.edit_text(
            "📖 **القرآن الكريم**",
            reply_markup=markup_with_bottom_controls(
                [
                    [
                        InlineKeyboardButton(
                            "📚 قائمة السور", callback_data="quran_list"
                        )
                    ],
                    [InlineKeyboardButton("🎙️ القرّاء", callback_data="quran_reciters")],
                ],
                back_callback="back_to_start",
                home_callback=None,
            ),
        )

    @app.on_callback_query(filters.regex("^quran_list$"))
    @safe_handler()
    async def quran_list_handler(client, cq):
        await cq.message.edit_text(
            "📚 **اختر السورة:**", reply_markup=surahs_keyboard(0)
        )

    @app.on_callback_query(filters.regex("^quran_page:"))
    @safe_handler()
    async def quran_page_handler(client, cq):
        page = int(cq.data.split(":")[1])
        await cq.message.edit_text(
            "📚 **اختر السورة:**", reply_markup=surahs_keyboard(page)
        )

    @app.on_callback_query(filters.regex("^quran_surah:"))
    @safe_handler()
    async def quran_surah_handler(client, cq):
        from bot.data.surahs import SURAHS

        num = int(cq.data.split(":")[1])
        name = SURAHS.get(num, "")

        await cq.message.edit_text(
            f"📖 **{num} - {name}**\n\n"
            f"🎵 للاستماع استخدم:\n`/stream [chat_id] quran {num}`",
            reply_markup=markup_with_bottom_controls(
                [], back_callback="quran_list", back_label="🔙 السور"
            ),
        )

    @app.on_callback_query(filters.regex("^quran_reciters$"))
    @safe_handler()
    async def quran_reciters_handler(client, cq):
        await cq.message.edit_text(
            "🎙️ **اختر القارئ:**", reply_markup=reciters_keyboard()
        )

    @app.on_callback_query(filters.regex("^quran_reciter:"))
    @safe_handler()
    async def quran_reciter_handler(client, cq):
        from pyrogram.types import InlineKeyboardButton

        from bot.data.sources import QURANIC_RECITERS

        key = cq.data.split(":", 1)[1]
        info = QURANIC_RECITERS.get(key)
        if not info:
            await cq.answer("❌ غير معروف", show_alert=True)
            return

        await cq.message.edit_text(
            f"🎙️ **{info['name']}**\n"
            f"🌍 {info['country']}\n"
            f"📝 {info['description']}\n\n"
            f"📡 رابط البث:\n`{info['stream_url']}`",
            reply_markup=markup_with_bottom_controls(
                [[InlineKeyboardButton("📚 السور", callback_data="quran_list")]],
                back_callback="quran_reciters",
                back_label="🔙 القرّاء",
            ),
        )
