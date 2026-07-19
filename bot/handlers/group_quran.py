from bot.decorators import admin_only, safe_handler
from bot.handlers.ui import markup_with_bottom_controls

MESSAGES = {
    "not_group": "❌ هذا الأمر يعمل فقط في المجموعات",
    "no_number": "❌ استخدم: `/quran [رقم السورة]`\nمثال: `/quran 1`",
    "invalid": "❌ رقم السورة يجب أن يكون 1-114",
    "playing": "✅ تم بدء بث سورة **{num} - {name}** في المكالمة الصوتية",
    "failed": "❌ فشل بدء البث. تأكد من وجود مكالمة صوتية نشطة في المجموعة",
    "stopped": "✅ تم إيقاف البث في هذه المجموعة",
    "not_streaming": "❌ لا يوجد بث نشط في هذه المجموعة",
    "paused": "⏸️ تم الإيقاف المؤقت",
    "resumed": "▶️ تم الاستئناف",
}

SURAH_NAMES = None


def _get_surah_name(num: int) -> str:
    global SURAH_NAMES
    if SURAH_NAMES is None:
        from bot.data.surahs import SURAHS

        SURAH_NAMES = SURAHS
    return SURAH_NAMES.get(num, "")


def _playback_kb(chat_id: int, title: str = ""):
    from pyrogram.types import InlineKeyboardButton

    return markup_with_bottom_controls(
        [
            [
                InlineKeyboardButton("⏹️ إيقاف", callback_data=f"qctrl:stop:{chat_id}"),
            ],
        ],
        back_callback=f"qctrl:panel:{chat_id}",
        back_label="🎛️ التحكم",
        home_callback=None,
        close_callback=f"qctrl:close:{chat_id}",
    )


def register(app, deps) -> None:
    from pyrogram import filters
    from pyrogram.types import CallbackQuery

    settings = deps.settings
    stream_manager = deps.stream_manager

    @app.on_message(filters.group & filters.command("quran"))
    @admin_only(app, settings)
    @safe_handler()
    async def quran_play(client, message):
        chat_id = message.chat.id
        args = message.command[1:]
        if not args:
            await message.reply_text(MESSAGES["no_number"])
            return
        try:
            num = int(args[0])
        except ValueError:
            await message.reply_text(MESSAGES["no_number"])
            return
        if not (1 <= num <= 114):
            await message.reply_text(MESSAGES["invalid"])
            return
        name = _get_surah_name(num)
        url = f"{settings.quran_stream_url}{num:03d}.mp3"
        ok = await stream_manager.play(chat_id, url, f"{num} - {name}")
        if ok:
            await message.reply_text(
                MESSAGES["playing"].format(num=num, name=name),
                reply_markup=_playback_kb(chat_id, f"{num} - {name}"),
            )
        else:
            await message.reply_text(MESSAGES["failed"])

    @app.on_message(filters.group & filters.command("stop"))
    @admin_only(app, settings)
    @safe_handler()
    async def quran_stop(client, message):
        chat_id = message.chat.id
        ok = await stream_manager.stop(chat_id)
        await message.reply_text(
            MESSAGES["stopped"] if ok else MESSAGES["not_streaming"]
        )

    @app.on_callback_query(filters.regex(r"^qctrl:"))
    @admin_only(app, settings)
    @safe_handler()
    async def quran_playback_control(client, cq: CallbackQuery):
        parts = cq.data.split(":")
        action = parts[1]
        chat_id = int(parts[2])

        if cq.message.chat.id != chat_id:
            await cq.answer("❌ هذا التحكم خاص بهذه المجموعة", show_alert=True)
            return

        if action == "stop":
            ok = await stream_manager.stop(chat_id)
            await cq.answer("✅ تم إيقاف البث" if ok else "❌ لا يوجد بث")
            if ok:
                await cq.message.delete()
            return

        if action == "panel":
            from bot.handlers.group_control import show_control_panel

            await cq.message.delete()
            await show_control_panel(client, cq.message, deps)
            await cq.answer()
            return

        if action == "close":
            await cq.message.delete()
            await cq.answer()
            return

        await cq.answer()
