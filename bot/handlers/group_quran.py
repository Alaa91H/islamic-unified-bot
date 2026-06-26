from bot.decorators import admin_only, safe_handler

MESSAGES = {
    "not_group": "❌ هذا الأمر يعمل فقط في المجموعات",
    "no_number": "❌ استخدم: `/quran [رقم السورة]`\nمثال: `/quran 1`",
    "invalid": "❌ رقم السورة يجب أن يكون 1-114",
    "playing": "✅ تم بدء بث سورة **{num} - {name}** في المكالمة الصوتية",
    "failed": "❌ فشل بدء البث. تأكد من وجود مكالمة صوتية نشطة في المجموعة",
    "stopped": "✅ تم إيقاف البث في هذه المجموعة",
    "not_streaming": "❌ لا يوجد بث نشط في هذه المجموعة",
}

SURAH_NAMES = None


def _get_surah_name(num: int) -> str:
    global SURAH_NAMES
    if SURAH_NAMES is None:
        from bot.data.surahs import SURAHS

        SURAH_NAMES = SURAHS
    return SURAH_NAMES.get(num, "")


def register(app, deps) -> None:
    from pyrogram import filters

    settings = deps.settings
    stream_manager = deps.stream_manager

    @app.on_message(filters.group & filters.command("quran"))
    @admin_only(app)
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
            await message.reply_text(MESSAGES["playing"].format(num=num, name=name))
        else:
            await message.reply_text(MESSAGES["failed"])

    @app.on_message(filters.group & filters.command("stop"))
    @admin_only(app)
    @safe_handler()
    async def quran_stop(client, message):
        chat_id = message.chat.id
        ok = await stream_manager.stop(chat_id)
        await message.reply_text(
            MESSAGES["stopped"] if ok else MESSAGES["not_streaming"]
        )
