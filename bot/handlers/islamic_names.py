from bot.decorators import safe_handler
from bot.handlers.ui import with_bottom_controls

_PAGE = 10


def register(app, deps) -> None:
    from pyrogram import filters
    from pyrogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup

    @app.on_message(filters.private & filters.command("names"))
    @safe_handler()
    async def names_cmd(client, message):
        from bot.data.islamic_names import NAMES_OF_ALLAH

        total = len(NAMES_OF_ALLAH)
        await message.reply_text(
            f"🤲 **أسماء الله الحسنى**\n───\n"
            f"• عدد الأسماء: {total}\n"
            f"• قال ﷺ: «إن لله تسعةً وتسعين اسمًا، من أحصاها دخل الجنة»\n\n"
            f"اختر اسماً لترى معناه:",
            reply_markup=_names_keyboard(0),
        )

    @app.on_callback_query(filters.regex("^names:"))
    @safe_handler()
    async def names_callback(client, cq: CallbackQuery):
        from bot.data.islamic_names import NAMES_OF_ALLAH

        parts = cq.data.split(":")
        action = parts[1]

        if action == "page":
            page = int(parts[2])
            await cq.message.edit_text(
                "🤲 **أسماء الله الحسنى**\n───\nاختر اسماً لترى معناه:",
                reply_markup=_names_keyboard(page),
            )
            await cq.answer()

        elif action == "show":
            idx = int(parts[2])
            i, name_ar, name_en, desc_ar, desc_en = NAMES_OF_ALLAH[idx - 1]
            text = (
                f"🤲 **الاسم {idx} من 99**\n───\n"
                f"**{name_ar}**\n"
                f"_{name_en}_\n\n"
                f"**الشرح:** {desc_ar}\n\n"
                f"**الذكر:** يا {name_ar}"
            )
            page = (idx - 1) // _PAGE
            buttons = [
                [
                    (
                        InlineKeyboardButton(
                            "⬅️ السابق", callback_data=f"names:show:{idx - 1}"
                        )
                        if idx > 1
                        else None
                    ),
                    (
                        InlineKeyboardButton(
                            "التالي ➡️", callback_data=f"names:show:{idx + 1}"
                        )
                        if idx < 99
                        else None
                    ),
                ],
                [
                    InlineKeyboardButton(
                        "🔙 القائمة", callback_data=f"names:page:{page}"
                    )
                ],
            ]
            buttons = [[b for b in row if b] for row in buttons if any(b for b in row)]
            buttons = with_bottom_controls(
                buttons, back_callback="back_to_start", home_callback=None
            )
            await cq.message.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons))
            await cq.answer()

        elif action == "close":
            await cq.message.delete()
            await cq.answer()

        elif action == "_":
            await cq.answer()

    def _names_keyboard(page: int):
        from bot.data.islamic_names import NAMES_OF_ALLAH

        start = page * _PAGE
        end = min(start + _PAGE, 99)
        buttons = []
        for i in range(start, end):
            idx, name_ar, *_ = NAMES_OF_ALLAH[i]
            buttons.append(
                [
                    InlineKeyboardButton(
                        f"{idx}. {name_ar}", callback_data=f"names:show:{i + 1}"
                    )
                ]
            )

        nav = []
        if page > 0:
            nav.append(
                InlineKeyboardButton("⬅️", callback_data=f"names:page:{page - 1}")
            )
        nav.append(InlineKeyboardButton(f"{page + 1}/10", callback_data="names:_"))
        if end < 99:
            nav.append(
                InlineKeyboardButton("➡️", callback_data=f"names:page:{page + 1}")
            )
        buttons.append(nav)
        buttons = with_bottom_controls(
            buttons, back_callback="back_to_start", home_callback=None
        )
        return InlineKeyboardMarkup(buttons)
