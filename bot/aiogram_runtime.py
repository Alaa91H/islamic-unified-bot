"""مسار Bot API تجريبي ومدروس لنقل أوامر Telegram البسيطة إلى aiogram.

لا يبدأ هذا المسار مع Pyrogram في الوقت نفسه، لأن long polling لنفس bot token
يسبب تعارض تحديثات. يقتصر على أوامر القائمة الثابتة حتى تكتمل هجرة البث الصوتي.
"""

from __future__ import annotations


def _home_keyboard():
    """لوحة pilot لا تعرض إلا callbacks التي ينفذها Router الحالي."""
    from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

    return InlineKeyboardMarkup(
        inline_keyboard=[
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


def create_main_menu_router():
    """أنشئ Router للأوامر الثابتة فقط دون اعتماد على Pyrogram أو MTProto."""
    from aiogram import F, Router
    from aiogram.filters import Command, CommandStart

    from bot.handlers.main_menu import (
        ABOUT_TEXT,
        GROUP_HELP,
        PRIVATE_HELP,
        WELCOME_TEXT,
    )

    router = Router(name="main-menu-pilot")

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
