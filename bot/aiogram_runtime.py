"""مسار Bot API تجريبي ومدروس لنقل أوامر Telegram البسيطة إلى aiogram.

لا يبدأ هذا المسار مع Pyrogram في الوقت نفسه، لأن long polling لنفس bot token
يسبب تعارض تحديثات. لا يعرض الـpilot إلا callbacks التي ينفذها Router الحالي.
"""

from __future__ import annotations


def _home_keyboard():
    """لوحة pilot لا تعرض إلا callbacks التي ينفذها Router الحالي."""
    from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📖 القرآن الكريم", callback_data="quran_text:home"
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🤲 أسماء الله الحسنى", callback_data="names:page:0"
                ),
            ],
            [
                InlineKeyboardButton(text="ℹ️ حول البوت", callback_data="about"),
            ],
        ]
    )


def _names_keyboard(page: int):
    """لوحة أسماء الله الحسنى في aiogram، مستقلة عن أنواع Pyrogram."""
    from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

    from bot.data.islamic_names import NAMES_OF_ALLAH

    page = max(0, min(page, 9))
    start = page * 10
    end = min(start + 10, len(NAMES_OF_ALLAH))
    buttons = [
        [
            InlineKeyboardButton(
                text=f"{index}. {name_ar}", callback_data=f"names:show:{index}"
            )
        ]
        for index, name_ar, *_ in NAMES_OF_ALLAH[start:end]
    ]
    navigation = []
    if page > 0:
        navigation.append(
            InlineKeyboardButton(text="⬅️", callback_data=f"names:page:{page - 1}")
        )
    navigation.append(
        InlineKeyboardButton(text=f"{page + 1}/10", callback_data="names:_")
    )
    if end < len(NAMES_OF_ALLAH):
        navigation.append(
            InlineKeyboardButton(text="➡️", callback_data=f"names:page:{page + 1}")
        )
    buttons.extend(
        [
            navigation,
            [InlineKeyboardButton(text="🔙 الرئيسية", callback_data="back_to_start")],
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def _name_detail(index: int) -> tuple[str, int] | None:
    """أعد نص اسم موثق وفهرس صفحة القائمة أو None لفهرس callback غير صالح."""
    from bot.data.islamic_names import NAMES_OF_ALLAH

    if not 1 <= index <= len(NAMES_OF_ALLAH):
        return None
    _index, name_ar, name_en, description_ar, _description_en = NAMES_OF_ALLAH[
        index - 1
    ]
    return (
        f"🤲 **الاسم {index} من {len(NAMES_OF_ALLAH)}**\n───\n"
        f"**{name_ar}**\n_{name_en}_\n\n"
        f"**الشرح:** {description_ar}\n\n**الذكر:** يا {name_ar}",
        (index - 1) // 10,
    )


def _quran_text_keyboard():
    """لوحة اختيار السور لمسار aiogram النصي فقط، بلا عناصر بث غير مهاجرة."""
    from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

    buttons = []
    row = []
    for surah in range(1, 115):
        row.append(
            InlineKeyboardButton(text=str(surah), callback_data=f"qts:{surah}:0")
        )
        if len(row) == 10:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    buttons.append(
        [InlineKeyboardButton(text="🔙 الرئيسية", callback_data="back_to_start")]
    )
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def _parse_qts_callback(data: str) -> tuple[int, int, bool] | None:
    """تحقق من callback لقراءة القرآن قبل الوصول إلى بيانات السور."""
    parts = data.split(":")
    if len(parts) not in {3, 4} or parts[0] != "qts":
        return None
    if len(parts) == 4 and parts[3] != "tafsir":
        return None
    try:
        surah, page = int(parts[1]), int(parts[2])
    except ValueError:
        return None
    if not 1 <= surah <= 114 or page < 0:
        return None
    return surah, page, len(parts) == 4


def _quran_info_keyboard(surah: int):
    from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📖 عرض الآيات", callback_data=f"qts:{surah}:1"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔍 تفسير السورة", callback_data=f"qts:{surah}:1:tafsir"
                )
            ],
            [InlineKeyboardButton(text="🔙 السور", callback_data="quran_text:home")],
            [InlineKeyboardButton(text="⌂ الرئيسية", callback_data="back_to_start")],
        ]
    )


def _quran_page_keyboard(surah: int, page: int, total_pages: int, show_tafsir: bool):
    from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

    navigation = []
    suffix = ":tafsir" if show_tafsir else ""
    if page > 1:
        navigation.append(
            InlineKeyboardButton(
                text="⬅️ السابق", callback_data=f"qts:{surah}:{page - 1}{suffix}"
            )
        )
    if page < total_pages:
        navigation.append(
            InlineKeyboardButton(
                text="التالي ➡️", callback_data=f"qts:{surah}:{page + 1}{suffix}"
            )
        )
    toggle_label = "🔍 إخفاء التفسير" if show_tafsir else "🔍 إظهار التفسير"
    toggle_data = f"qts:{surah}:{page}" + ("" if show_tafsir else ":tafsir")
    rows = [navigation] if navigation else []
    rows.extend(
        [
            [InlineKeyboardButton(text=toggle_label, callback_data=toggle_data)],
            [
                InlineKeyboardButton(
                    text="ℹ️ معلومات السورة", callback_data=f"qts:{surah}:0"
                )
            ],
            [InlineKeyboardButton(text="🔙 السور", callback_data="quran_text:home")],
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def create_main_menu_router():
    """أنشئ Router للأوامر النصية فقط دون اعتماد على Pyrogram أو MTProto."""
    from aiogram import F, Router
    from aiogram.filters import Command, CommandStart

    from bot.handlers.main_menu import (
        ABOUT_TEXT,
        GROUP_HELP,
        PRIVATE_HELP,
        WELCOME_TEXT,
    )

    router = Router(name="main-menu-pilot")

    async def show_quran_landing(message, *, edit: bool = False):
        text = "📖 **القرآن الكريم - النص والتفسير**\n\nاختر رقم السورة لعرض آياتها:"
        if edit:
            await message.edit_text(text, reply_markup=_quran_text_keyboard())
        else:
            await message.answer(text, reply_markup=_quran_text_keyboard())

    @router.message(CommandStart())
    async def start_command(message):
        if message.chat.type != "private":
            await message.answer(GROUP_HELP)
            return
        await message.answer(WELCOME_TEXT, reply_markup=_home_keyboard())

    @router.message(Command("help"))
    async def help_command(message):
        await message.answer(
            PRIVATE_HELP if message.chat.type == "private" else GROUP_HELP
        )

    @router.message(Command("names"))
    async def names_command(message):
        from bot.data.islamic_names import NAMES_OF_ALLAH

        await message.answer(
            "🤲 **أسماء الله الحسنى**\n───\n"
            f"• عدد الأسماء: {len(NAMES_OF_ALLAH)}\n"
            "• قال ﷺ: «إن لله تسعةً وتسعين اسمًا، من أحصاها دخل الجنة»\n\n"
            "اختر اسماً لترى معناه:",
            reply_markup=_names_keyboard(0),
        )

    @router.message(Command("quran_text"))
    async def quran_text_command(message):
        await show_quran_landing(message)

    @router.callback_query(F.data == "about")
    async def about_callback(callback):
        if callback.message:
            await callback.message.edit_text(ABOUT_TEXT)
        await callback.answer()

    @router.callback_query(F.data == "back_to_start")
    async def back_to_start_callback(callback):
        if callback.message:
            await callback.message.edit_text(
                WELCOME_TEXT, reply_markup=_home_keyboard()
            )
        await callback.answer()

    @router.callback_query(F.data == "quran_text:home")
    async def quran_text_home_callback(callback):
        if callback.message:
            await show_quran_landing(callback.message, edit=True)
        await callback.answer()

    @router.callback_query(F.data.startswith("names:"))
    async def names_callback(callback):
        data = callback.data or ""
        parts = data.split(":")
        if len(parts) == 2 and parts[1] == "_":
            await callback.answer()
            return
        if len(parts) != 3 or parts[1] not in {"page", "show"}:
            await callback.answer("طلب غير صالح", show_alert=True)
            return
        try:
            index = int(parts[2])
        except ValueError:
            await callback.answer("طلب غير صالح", show_alert=True)
            return
        if callback.message is None:
            await callback.answer()
            return
        if parts[1] == "page":
            if not 0 <= index <= 9:
                await callback.answer("صفحة غير صالحة", show_alert=True)
                return
            await callback.message.edit_text(
                "🤲 **أسماء الله الحسنى**\n───\nاختر اسماً لترى معناه:",
                reply_markup=_names_keyboard(index),
            )
            await callback.answer()
            return
        detail = _name_detail(index)
        if detail is None:
            await callback.answer("اسم غير صالح", show_alert=True)
            return
        text, page = detail
        await callback.message.edit_text(text, reply_markup=_names_keyboard(page))
        await callback.answer()

    @router.callback_query(F.data.startswith("qts:"))
    async def quran_text_callback(callback):
        from bot.data.quran_data import AYAH_COUNTS, get_ayah_text, get_tafsir
        from bot.data.surahs import SURAHS

        parsed = _parse_qts_callback(callback.data or "")
        if parsed is None or callback.message is None:
            await callback.answer("طلب غير صالح", show_alert=True)
            return
        surah, page, show_tafsir = parsed
        total = AYAH_COUNTS.get(surah, 0)
        total_pages = (total + 9) // 10
        if total == 0 or page > total_pages:
            await callback.answer("سورة أو صفحة غير صالحة", show_alert=True)
            return
        name = SURAHS.get(surah, "")
        if page == 0:
            await callback.message.edit_text(
                f"📖 **سورة {name}**\n───\n"
                f"• رقم السورة: {surah}\n• عدد الآيات: {total}\n\n"
                "اختر من القائمة:",
                reply_markup=_quran_info_keyboard(surah),
            )
            await callback.answer()
            return

        start = (page - 1) * 10 + 1
        end = min(start + 9, total)
        lines = []
        for ayah in range(start, end + 1):
            text = await get_ayah_text(surah, ayah)
            if text:
                lines.append(f"**{ayah}** - {text}")
                if show_tafsir:
                    tafsir = await get_tafsir(surah, ayah)
                    if tafsir:
                        lines.append(f"  _{tafsir}_\n")
        content = f"📖 **{name}** - صفحة {page}\n───\n" + "\n".join(lines)
        await callback.message.edit_text(
            content[:4000],
            reply_markup=_quran_page_keyboard(surah, page, total_pages, show_tafsir),
        )
        await callback.answer()

    return router


def build_aiogram_app(settings):
    """ابنِ Bot وDispatcher بدون بدء polling؛ مسؤولية بدءهما تبقى في main."""
    from aiogram import Bot, Dispatcher
    from aiogram.client.default import DefaultBotProperties
    from aiogram.enums import ParseMode

    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN),
    )
    dispatcher = Dispatcher()
    dispatcher.include_router(create_main_menu_router())
    return bot, dispatcher
