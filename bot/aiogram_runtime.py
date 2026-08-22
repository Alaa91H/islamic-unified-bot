"""مسار Bot API تجريبي ومدروس لنقل أوامر Telegram البسيطة إلى aiogram.

لا يبدأ هذا المسار مع Pyrogram في الوقت نفسه، لأن long polling لنفس bot token
يسبب تعارض تحديثات. يقتصر على أوامر القائمة الثابتة حتى تكتمل هجرة البث الصوتي.
"""

from __future__ import annotations


def _home_keyboard():
    from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📖 القرآن الكريم", callback_data="quran_menu"
                ),
                InlineKeyboardButton(
                    text="📚 الحديث الشريف", callback_data="hadith:books"
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🤲 الأذكار", callback_data="main_adhkar_menu"
                ),
                InlineKeyboardButton(
                    text="🕌 الأذان والصلاة", callback_data="azan_home"
                ),
            ],
            [
                InlineKeyboardButton(text="ℹ️ حول البوت", callback_data="about"),
            ],
        ]
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

    return router


def build_aiogram_app(settings):
    """ابنِ Bot وDispatcher بدون بدء polling؛ مسؤولية بدءهما تبقى في main."""
    from aiogram import Bot, Dispatcher

    bot = Bot(token=settings.bot_token)
    dispatcher = Dispatcher()
    dispatcher.include_router(create_main_menu_router())
    return bot, dispatcher
