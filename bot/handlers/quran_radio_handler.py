from bot.data.sources import QURANIC_RECITERS
from bot.data.surahs import SURAHS
from bot.decorators import admin_only, safe_handler
from bot.services.quran_radio import estimate_duration, AUDIO_QUALITY_OPTIONS, AUDIO_QUALITY_LABELS

CONTROLS = {
    "prev": "⏮️",
    "pause": "⏸️",
    "next": "⏭️ ",
    "shuffle": "🔀",
    "reciters": "🎙️",
    "stop": "⏹️",
    "info": "ℹ️",
}


def _radio_keyboard(chat_id: int, is_paused: bool, shuffle_on: bool, quality: str = "high"):
    from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
    q_label = AUDIO_QUALITY_LABELS.get(quality, quality)
    kb = [
        [
            InlineKeyboardButton("⏮️", callback_data=f"rdo:prev:{chat_id}"),
            InlineKeyboardButton("▶️" if is_paused else "⏸️", callback_data=f"rdo:{'resume' if is_paused else 'pause'}:{chat_id}"),
            InlineKeyboardButton("⏭️", callback_data=f"rdo:next:{chat_id}"),
        ],
        [
            InlineKeyboardButton(f"✅ عشوائي" if shuffle_on else "🔀 عشوائي", callback_data=f"rdo:shuffle:{chat_id}"),
            InlineKeyboardButton("🎙️ القارئ", callback_data=f"rdo:reciters:{chat_id}"),
        ],
        [
            InlineKeyboardButton(f"🎚️ {q_label}", callback_data=f"rdo:quality:{chat_id}"),
            InlineKeyboardButton("⏹️ إيقاف الراديو", callback_data=f"rdo:stop:{chat_id}"),
        ],
        [
            InlineKeyboardButton("ℹ️ الآن", callback_data=f"rdo:info:{chat_id}"),
        ],
    ]
    return InlineKeyboardMarkup(kb)


def _reciters_keyboard(chat_id: int):
    from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

    kb = []
    for key, info in QURANIC_RECITERS.items():
        kb.append([InlineKeyboardButton(f"🎙️ {info['name']}", callback_data=f"rdo:setreciter:{chat_id}:{key}")])
    kb.append([InlineKeyboardButton("🔙 رجوع", callback_data=f"rdo:panel:{chat_id}")])
    return InlineKeyboardMarkup(kb)


def register(app, deps) -> None:
    from pyrogram import filters
    from pyrogram.types import CallbackQuery

    radio_service = deps.quran_radio
    settings = deps.settings

    @app.on_message(filters.group & filters.command("radio"))
    @admin_only(app)
    @safe_handler()
    async def radio_cmd(client, message):
        chat_id = message.chat.id
        args = message.command[1:]

        if args and args[0] == "stop":
            ok = await radio_service.stop(chat_id)
            await message.reply_text("✅ تم إيقاف راديو القرآن" if ok else "❌ لا يوجد راديو نشط")
            return

        state = radio_service.get_state(chat_id)
        if state:
            await _show_panel(message, chat_id, radio_service)
            return

        ok = await radio_service.start(chat_id)
        if ok:
            await _show_panel(message, chat_id, radio_service)
        else:
            await message.reply_text("❌ فشل بدء الراديو. تأكد من وجود مكالمة صوتية نشطة.")

    @app.on_callback_query(filters.regex(r"^rdo:"))
    @safe_handler()
    async def radio_control(client, cq: CallbackQuery):
        parts = cq.data.split(":")
        action = parts[1]
        chat_id = int(parts[2])
        extra = parts[3] if len(parts) > 3 else None

        if cq.message.chat.id != chat_id:
            await cq.answer("❌ هذا التحكم خاص بالمجموعة التي بدأ منها الراديو", show_alert=True)
            return

        state = radio_service.get_state(chat_id)
        if not state:
            await cq.answer("❌ الراديو غير نشط", show_alert=True)
            return

        if action == "prev":
            ok = await radio_service.prev(chat_id)
            await cq.answer("⏮️ السورة السابقة" if ok else "❌ فشل")
        elif action == "next":
            ok = await radio_service.next(chat_id)
            await cq.answer("⏭️ السورة التالية" if ok else "❌ فشل")
        elif action == "pause":
            ok = await radio_service.pause(chat_id)
            await cq.answer("⏸️ تم الإيقاف المؤقت" if ok else "❌ فشل")
        elif action == "resume":
            ok = await radio_service.resume(chat_id)
            await cq.answer("▶️ استئناف" if ok else "❌ فشل")
        elif action == "shuffle":
            ok = await radio_service.toggle_shuffle(chat_id)
            await cq.answer("🔀 تم تفعيل العشوائية" if ok else "❌ فشل")
        elif action == "stop":
            ok = await radio_service.stop(chat_id)
            await cq.answer("⏹️ تم إيقاف الراديو" if ok else "❌ فشل")
            if ok:
                await cq.message.delete()
                return
        elif action == "info":
            surah_num = state.queue[state.current_index]
            surah_name = SURAHS.get(surah_num, f"{surah_num}")
            await cq.answer(f"📖 {surah_num} - {surah_name}", show_alert=False)
            return
        elif action == "panel":
            pass
        elif action == "reciters":
            await cq.message.edit_text("🎙️ **اختر القارئ لراديو القرآن:**", reply_markup=_reciters_keyboard(chat_id))
            await cq.answer()
            return
        elif action == "setreciter" and extra:
            reciter_key = extra
            ok = await radio_service.set_reciter(chat_id, reciter_key)
            await cq.answer(f"🎙️ تم تغيير القارئ إلى {QURANIC_RECITERS[reciter_key]['name']}" if ok else "❌ فشل")
        elif action == "quality":
            current = state.audio_quality
            idx = AUDIO_QUALITY_OPTIONS.index(current) if current in AUDIO_QUALITY_OPTIONS else 2
            next_q = AUDIO_QUALITY_OPTIONS[(idx + 1) % len(AUDIO_QUALITY_OPTIONS)]
            ok = await radio_service.set_quality(chat_id, next_q)
            await cq.answer(f"🎚️ الجودة: {AUDIO_QUALITY_LABELS.get(next_q, next_q)}" if ok else "❌ فشل")

        await _update_panel(cq, chat_id, radio_service)

    @app.on_message(filters.group & filters.command("radio_stop"))
    @admin_only(app)
    @safe_handler()
    async def radio_stop_cmd(client, message):
        ok = await radio_service.stop(message.chat.id)
        await message.reply_text("✅ تم إيقاف راديو القرآن" if ok else "❌ لا يوجد راديو نشط")


async def _show_panel(message, chat_id, radio_service):
    state = radio_service.get_state(chat_id)
    if not state:
        await message.reply_text("❌ الراديو غير نشط")
        return
    surah_num = state.queue[state.current_index]
    surah_name = SURAHS.get(surah_num, f"{surah_num}")
    reciter_name = QURANIC_RECITERS.get(state.reciter_key, {}).get("name", state.reciter_key)
    dur = estimate_duration(surah_num)

    text = _build_radio_text(surah_num, surah_name, reciter_name, dur, state.shuffle, state.paused)
    await message.reply_text(text, reply_markup=_radio_keyboard(chat_id, state.paused, state.shuffle))


async def _update_panel(cq, chat_id, radio_service):
    state = radio_service.get_state(chat_id)
    if not state:
        await cq.message.edit_text("❌ الراديو غير نشط")
        return
    surah_num = state.queue[state.current_index]
    surah_name = SURAHS.get(surah_num, f"{surah_num}")
    reciter_name = QURANIC_RECITERS.get(state.reciter_key, {}).get("name", state.reciter_key)
    dur = estimate_duration(surah_num)
    text = _build_radio_text(surah_num, surah_name, reciter_name, dur, state.shuffle, state.paused)
    await cq.message.edit_text(text, reply_markup=_radio_keyboard(chat_id, state.paused, state.shuffle))


def _build_radio_text(surah_num: int, surah_name: str, reciter_name: str, dur: int, shuffle_on: bool, paused: bool = False) -> str:
    status = "⏸️ **متوقف مؤقتاً**" if paused else "▶️ **يعمل**"
    return (
        f"📻 **راديو القرآن**\n\n"
        f"{status}\n"
        f"🎙️ **القارئ:** {reciter_name}\n"
        f"📖 **السورة:** {surah_num} - {surah_name}\n"
        f"⏱ **المدة التقريبية:** {dur} دقيقة\n"
        f"{'🔀 **عشوائي:** مفعل' if shuffle_on else '🔀 **عشوائي:** معطل'}\n"
    )
