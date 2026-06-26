from bot.data.surahs import SURAHS
from bot.decorators import owner_only, safe_handler
from bot.streaming import HAS_STREAMING


def register(app, deps) -> None:
    from pyrogram import filters

    settings = deps.settings
    stream_manager = deps.stream_manager

    if not HAS_STREAMING:
        _register_streaming_unavailable(app, settings)
        return

    @app.on_message(filters.command("stream"))
    @owner_only(settings)
    @safe_handler()
    async def stream_cmd(client, message):
        args = message.command[1:]
        if len(args) < 2:
            await message.reply_text(
                "📌 **استخدام:**\n"
                "`/stream [chat_id] quran [رقم]`\n"
                "`/stream [chat_id] url [رابط]`\n"
                "`/stream [chat_id] file [رقم]`",
            )
            return

        chat_id = int(args[0])
        stream_type = args[1].lower()

        if stream_type == "quran":
            if len(args) < 3:
                await message.reply_text("❌ أدخل رقم السورة")
                return
            surah_num = int(args[2])
            if not (1 <= surah_num <= 114):
                await message.reply_text("❌ رقم السورة يجب أن يكون 1-114")
                return
            url = f"{settings.quran_stream_url}{surah_num:03d}.mp3"
            name = SURAHS.get(surah_num, "سورة")
            ok = await stream_manager.play(chat_id, url, f"{surah_num} - {name}")
            await message.reply_text(
                f"{'✅' if ok else '❌'} بدأ البث: **{surah_num} - {name}**"
                if ok
                else "❌ فشل بدء البث"
            )

        elif stream_type == "url":
            url = args[2]
            ok = await stream_manager.play(chat_id, url, "بث مخصص")
            await message.reply_text(f"{'✅' if ok else '❌'} البث في `{chat_id}`")

        elif stream_type == "file":
            if len(args) < 3:
                await message.reply_text("❌ أدخل رقم الملف")
                return
            file_num = int(args[2])
            files = stream_manager.get_local_files(settings.music_dir)
            if file_num not in files:
                await message.reply_text(f"❌ الملف {file_num} غير موجود")
                return
            info = files[file_num]
            ok = await stream_manager.play(chat_id, info["path"], info["name"])
            await message.reply_text(f"{'✅' if ok else '❌'} {info['name']}")

    @app.on_message(filters.command("stop"))
    @owner_only(settings)
    @safe_handler()
    async def stop_cmd(client, message):
        args = message.command[1:]
        if not args:
            await message.reply_text("`/stop [chat_id]`")
            return
        chat_id = int(args[0])
        ok = await stream_manager.stop(chat_id)
        await message.reply_text(f"{'✅' if ok else '❌'} إيقاف البث في `{chat_id}`")

    @app.on_message(filters.command("status"))
    @owner_only(settings)
    @safe_handler()
    async def status_cmd(client, message):
        streams = stream_manager.active_streams()
        if not streams:
            await message.reply_text("✅ لا توجد بثات نشطة")
            return
        text = "📊 **البثات النشطة:**\n\n"
        for cid, info in streams.items():
            text += f"📍 `{cid}`\n🎵 {info.get('title', '')}\n"
            if "started_at" in info:
                mins = (
                    __import__("datetime").datetime.now() - info["started_at"]
                ).seconds // 60
                text += f"⏱️ {mins}د\n"
        await message.reply_text(text)

    @app.on_message(filters.command("dashboard"))
    @owner_only(settings)
    @safe_handler()
    async def dashboard_cmd(client, message):
        import json, os
        stream_count = len(stream_manager.active_streams())
        usage_path = os.path.join("data", "usage_counts.json")
        total_usage = 0
        top_cmds = ""
        try:
            with open(usage_path, encoding="utf-8") as f:
                data = json.load(f)
                total_usage = sum(data.values())
                sorted_cmds = sorted(data.items(), key=lambda x: -x[1])[:10]
                top_cmds = "\n".join(f"  {i+1}. `/{c}`: {n}" for i, (c, n) in enumerate(sorted_cmds))
        except (FileNotFoundError, json.JSONDecodeError):
            top_cmds = "  لا توجد بيانات"
        await message.reply_text(
            f"📊 **لوحة التحكم**\n\n"
            f"**البث النشط:** {stream_count}\n"
            f"**إجمالي الأوامر:** {total_usage}\n\n"
            f"**الأكثر استخداماً:**\n{top_cmds}\n\n"
            f"_آخر تحديث: الآن_"
        )

    @app.on_message(filters.command("files"))
    @owner_only(settings)
    @safe_handler()
    async def files_cmd(client, message):
        files = (
            await __import__("asyncio")
            .get_event_loop()
            .run_in_executor(None, stream_manager.get_local_files, settings.music_dir)
        )
        if not files:
            await message.reply_text(f"❌ لا توجد ملفات في `{settings.music_dir}`")
            return
        text = f"📁 **الملفات ({len(files)}):**\n\n"
        for num, info in files.items():
            size_mb = info["size"] / (1024 * 1024)
            text += f"{num}. {info['name']} ({size_mb:.2f} MB)\n"
        await message.reply_text(text[:3000])


def _register_streaming_unavailable(app, settings):
    from pyrogram import filters

    msg = "❌ البث الصوتي غير متاح (مكتبة py-tgcalls غير مثبتة)"

    @app.on_message(filters.command("stream"))
    async def stream_unavailable(client, message):
        await message.reply_text(msg)

    @app.on_message(filters.command("stop"))
    async def stop_unavailable(client, message):
        await message.reply_text(msg)
