from bot.decorators import admin_only, safe_handler
from bot.handlers.ui import markup_with_bottom_controls


def _control_panel_keyboard(chat_id: int):
    from pyrogram.types import InlineKeyboardButton

    quick_surah = [
        ("1", "الفاتحة"),
        ("67", "الملك"),
        ("55", "الرحمن"),
        ("36", "يس"),
        ("18", "الكهف"),
        ("56", "الواقعة"),
    ]

    rows = [
        [
            InlineKeyboardButton(
                f"▶️ {name}", callback_data=f"gctrl:qfast:{chat_id}:{num}"
            )
            for num, name in quick_surah[:3]
        ],
        [
            InlineKeyboardButton(
                f"▶️ {name}", callback_data=f"gctrl:qfast:{chat_id}:{num}"
            )
            for num, name in quick_surah[3:]
        ],
        [
            InlineKeyboardButton(
                "📖 سورة أخرى", callback_data=f"gctrl:quran:{chat_id}"
            ),
            InlineKeyboardButton(
                "📻 راديو القرآن", callback_data=f"gctrl:radio:{chat_id}"
            ),
        ],
        [
            InlineKeyboardButton("⏹️ إيقاف البث", callback_data=f"gctrl:stop:{chat_id}"),
            InlineKeyboardButton("ℹ️ الحالة", callback_data=f"gctrl:status:{chat_id}"),
        ],
        [
            InlineKeyboardButton("🤲 الأذكار", callback_data=f"gctrl:adhkar:{chat_id}"),
            InlineKeyboardButton(
                "🕌 أوقات الصلاة", callback_data=f"gctrl:prayer:{chat_id}"
            ),
        ],
        [
            InlineKeyboardButton(
                "⚙️ إعدادات المجموعة", callback_data=f"gctrl:settings:{chat_id}"
            ),
        ],
    ]
    return markup_with_bottom_controls(
        rows,
        home_callback=None,
        close_callback=f"gctrl:close:{chat_id}",
        close_label="🔒 إغلاق",
    )


def _control_panel_text(is_streaming: bool) -> str:
    status = "🟢 يعمل" if is_streaming else "🔴 متوقف"
    return (
        "🎛️ **لوحة تحكم المجموعة**\n"
        f"حالة البث: {status}\n"
        f"{'━' * 16}\n"
        "▶️ **تشغيل سريع:** اضغط على السورة مباشرة"
    )


async def _edit_control_panel(cq, deps) -> None:
    chat_id = cq.message.chat.id
    is_streaming = chat_id in deps.stream_manager.active_streams()
    await cq.message.edit_text(
        _control_panel_text(is_streaming),
        reply_markup=_control_panel_keyboard(chat_id),
    )


async def show_control_panel(client, message, deps) -> None:
    """Module-level function — يمكن استيرادها من وحدات أخرى (مثل group_quran)."""
    chat_id = message.chat.id
    stream_manager = deps.stream_manager
    is_streaming = chat_id in stream_manager.active_streams()
    await message.reply_text(
        _control_panel_text(is_streaming),
        reply_markup=_control_panel_keyboard(chat_id),
    )


def register(app, deps) -> None:
    from pyrogram import filters
    from pyrogram.types import CallbackQuery, InlineKeyboardButton

    stream_manager = deps.stream_manager
    settings = deps.settings

    @app.on_message(filters.group & filters.command("control"))
    @admin_only(app, settings)
    @safe_handler()
    async def control_panel(client, message):
        await show_control_panel(client, message, deps)

    @app.on_callback_query(filters.regex(r"^gctrl:"))
    @admin_only(app, settings)
    @safe_handler()
    async def gctrl_handler(client, cq: CallbackQuery):
        parts = cq.data.split(":")
        action = parts[1]
        chat_id = int(parts[2]) if len(parts) > 2 else cq.message.chat.id
        extra = parts[3] if len(parts) > 3 else None

        if cq.message.chat.id != chat_id:
            await cq.answer("❌ هذا التحكم خاص بهذه المجموعة", show_alert=True)
            return

        if action == "qfast":
            from bot.data.surahs import SURAHS

            try:
                num = int(extra)
            except (ValueError, TypeError):
                await cq.answer("❌ رقم غير صالح", show_alert=True)
                return
            name = SURAHS.get(num, "")
            url = f"{settings.quran_stream_url}{num:03d}.mp3"
            ok = await stream_manager.play(chat_id, url, f"{num} - {name}")
            if ok:
                await cq.answer(f"✅ تم تشغيل {num} - {name}")
                from bot.handlers.group_quran import _playback_kb

                await cq.message.edit_text(
                    f"🎵 **جاري تشغيل:** {num} - {name}",
                    reply_markup=_playback_kb(chat_id, f"{num} - {name}"),
                )
            else:
                await cq.answer(
                    "❌ فشل التشغيل. تأكد من وجود مكالمة صوتية", show_alert=True
                )
            return

        if action == "quran":
            await cq.message.edit_text(
                "📖 **تشغيل سورة**\n"
                "أرسل رقم السورة (1-114)\n"
                "مثال: `1` للفاتحة\n"
                "أو أرسل /cancel للإلغاء",
                reply_markup=markup_with_bottom_controls(
                    [],
                    back_callback=f"gctrl:back:{chat_id}",
                    home_callback=None,
                    close_callback=f"gctrl:close:{chat_id}",
                    close_label="🔒 إغلاق",
                ),
            )
            try:
                answer = await client.ask(
                    cq.message.chat.id,
                    "رقم السورة:",
                    timeout=60,
                    filters=filters.text,
                )
            except TimeoutError:
                await cq.message.reply_text("❌ انتهت المهلة")
                return
            txt = answer.text.strip()
            if txt == "/cancel":
                await answer.reply_text("✅ أُلغيت")
                await control_panel(client, answer)
                return
            try:
                num = int(txt)
                if not (1 <= num <= 114):
                    raise ValueError
            except ValueError:
                await answer.reply_text("❌ رقم غير صالح (1-114)")
                return
            from bot.data.surahs import SURAHS

            name = SURAHS.get(num, "")
            url = f"{settings.quran_stream_url}{num:03d}.mp3"
            ok = await stream_manager.play(chat_id, url, f"{num} - {name}")
            if ok:
                await answer.reply_text(
                    f"✅ تم بدء بث سورة **{num} - {name}**",
                    reply_markup=_quran_playback_kb(
                        chat_id, paused=False, title=f"{num} - {name}"
                    ),
                )
            else:
                await answer.reply_text("❌ فشل البث. تأكد من وجود مكالمة صوتية")

        elif action == "radio":
            radio_service = deps.quran_radio
            state = radio_service.get_state(chat_id)
            if state:
                await _show_radio_panel(cq, chat_id, radio_service)
                return
            ok = await radio_service.start(chat_id)
            if ok:
                await _show_radio_panel(cq, chat_id, radio_service)
            else:
                await cq.answer("❌ فشل. تأكد من وجود مكالمة صوتية", show_alert=True)

        elif action == "stop":
            ok = await stream_manager.stop(chat_id)
            radio_service = deps.quran_radio
            await radio_service.stop(chat_id)
            await cq.answer("✅ تم إيقاف البث" if ok else "✅ تم", show_alert=True)
            await _edit_control_panel(cq, deps)

        elif action == "status":
            from bot.streaming.null_stream_manager import NullStreamManager

            if isinstance(stream_manager, NullStreamManager):
                text = "❌ البث الصوتي غير متاح"
            else:
                active = stream_manager.active_streams()
                info = active.get(chat_id)
                radio_state = deps.quran_radio.get_state(chat_id)
                lines = ["📊 **حالة البث**\n"]
                if info:
                    from bot.data.surahs import SURAHS

                    title = info.get("title", "")
                    lines.append(f"🎵 **{title}**")
                    if "started_at" in info:
                        elapsed = (
                            __import__("datetime").datetime.now() - info["started_at"]
                        ).seconds // 60
                        lines.append(f"⏱ المدة: {elapsed} دقيقة")
                if radio_state:
                    from bot.data.surahs import SURAHS

                    surah_name = SURAHS.get(
                        radio_state.queue[radio_state.current_index], ""
                    )
                    lines.append("\n📻 **الراديو:**")
                    lines.append(
                        f"📖 {radio_state.queue[radio_state.current_index]} - {surah_name}"
                    )
                    lines.append(f"{'⏸️ متوقف' if radio_state.paused else '▶️ يعمل'}")
                    lines.append(
                        f"{'🔀 عشوائي' if radio_state.shuffle else '🔀 تسلسلي'}"
                    )
                if not info and not radio_state:
                    lines.append("ℹ️ لا يوجد بث نشط حالياً")
                text = "\n".join(lines)
            await cq.message.edit_text(
                text,
                reply_markup=markup_with_bottom_controls(
                    [],
                    back_callback=f"gctrl:back:{chat_id}",
                    home_callback=None,
                    close_callback=f"gctrl:close:{chat_id}",
                    close_label="🔒 إغلاق",
                ),
            )

        elif action == "prayer":
            from bot.data.cities import CITIES

            city_list = "\n".join(
                f"• {c['name']} ({c.get('country', '')})"
                for c in list(CITIES.values())[:10]
            )
            await cq.message.edit_text(
                f"🕌 **أوقات الصلاة**\n"
                f"لضبط المدينة: /azan_setup\n"
                f"للمشاهدة: /azan_times\n\n"
                f"**المدن المتاحة:**\n{city_list}",
                reply_markup=markup_with_bottom_controls(
                    [],
                    back_callback=f"gctrl:back:{chat_id}",
                    home_callback=None,
                    close_callback=f"gctrl:close:{chat_id}",
                    close_label="🔒 إغلاق",
                ),
            )

        elif action == "adhkar":
            from bot.db.repositories.adhkar_settings import AdhkarSettings

            repo = deps.adhkar_repo
            s = await repo.get(chat_id) or AdhkarSettings(chat_id=chat_id)
            kb = markup_with_bottom_controls(
                [
                    [
                        InlineKeyboardButton(
                            f"{'✅' if s.interval_enabled else '❌'} الذكر الدوري ({s.interval_minutes}د)",
                            callback_data=f"gctrl:adhk_toggle:interval:{chat_id}",
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            f"{'✅' if s.morning_enabled else '❌'} أذكار الصباح ({s.morning_time})",
                            callback_data=f"gctrl:adhk_toggle:morning:{chat_id}",
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            f"{'✅' if s.evening_enabled else '❌'} أذكار المساء ({s.evening_time})",
                            callback_data=f"gctrl:adhk_toggle:evening:{chat_id}",
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            f"{'✅' if s.friday_enabled else '❌'} أذكار الجمعة ({s.friday_time})",
                            callback_data=f"gctrl:adhk_toggle:friday:{chat_id}",
                        )
                    ],
                ],
                back_callback=f"gctrl:back:{chat_id}",
                home_callback=None,
                close_callback=f"gctrl:close:{chat_id}",
                close_label="🔒 إغلاق",
            )
            await cq.message.edit_text("🤲 **إعدادات الأذكار**", reply_markup=kb)

        elif action == "adhk_toggle":
            key = extra
            repo = deps.adhkar_repo
            from bot.db.repositories.adhkar_settings import AdhkarSettings

            s = await repo.get(chat_id) or AdhkarSettings(chat_id=chat_id)
            if key == "interval":
                s.interval_enabled = not s.interval_enabled
            elif key == "morning":
                s.morning_enabled = not s.morning_enabled
            elif key == "evening":
                s.evening_enabled = not s.evening_enabled
            elif key == "friday":
                s.friday_enabled = not s.friday_enabled
            await repo.upsert(s)
            await cq.answer("✅ تم التحديث")
            kb = markup_with_bottom_controls(
                [
                    [
                        InlineKeyboardButton(
                            f"{'✅' if s.interval_enabled else '❌'} الذكر الدوري ({s.interval_minutes}د)",
                            callback_data=f"gctrl:adhk_toggle:interval:{chat_id}",
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            f"{'✅' if s.morning_enabled else '❌'} أذكار الصباح ({s.morning_time})",
                            callback_data=f"gctrl:adhk_toggle:morning:{chat_id}",
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            f"{'✅' if s.evening_enabled else '❌'} أذكار المساء ({s.evening_time})",
                            callback_data=f"gctrl:adhk_toggle:evening:{chat_id}",
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            f"{'✅' if s.friday_enabled else '❌'} أذكار الجمعة ({s.friday_time})",
                            callback_data=f"gctrl:adhk_toggle:friday:{chat_id}",
                        )
                    ],
                ],
                back_callback=f"gctrl:back:{chat_id}",
                home_callback=None,
                close_callback=f"gctrl:close:{chat_id}",
                close_label="🔒 إغلاق",
            )
            await cq.message.edit_reply_markup(reply_markup=kb)

        elif action == "settings":
            group_repo = deps.group_repo
            gs = await group_repo.get(chat_id)
            if gs:
                text = (
                    f"⚙️ **إعدادات المجموعة**\n\n"
                    f"📍 المدينة: {gs.city}\n"
                    f"📐 الطريقة: {gs.method}\n"
                    f"📊 العصر: {gs.asr_method}\n"
                    f"🔔 الأذان التلقائي: {'✅' if gs.stream_quran_on else '❌'}\n"
                    f"🎵 مصدر الأذان: {gs.azan_source}\n"
                )
            else:
                text = "⚙️ **إعدادات المجموعة**\n\nلم يتم ضبط الإعدادات بعد.\nاستخدم /azan_setup لاختيار مدينة."
            await cq.message.edit_text(
                text,
                reply_markup=markup_with_bottom_controls(
                    [],
                    back_callback=f"gctrl:back:{chat_id}",
                    home_callback=None,
                    close_callback=f"gctrl:close:{chat_id}",
                    close_label="🔒 إغلاق",
                ),
            )

        elif action == "back":
            await _edit_control_panel(cq, deps)

        elif action == "close":
            await cq.message.delete()
            await cq.answer()
            return

        await cq.answer()


def _quran_playback_kb(chat_id: int, paused: bool, title: str = ""):
    from pyrogram.types import InlineKeyboardButton

    return markup_with_bottom_controls(
        [
            [
                InlineKeyboardButton("⏹️ إيقاف", callback_data=f"gctrl:stop:{chat_id}"),
            ],
        ],
        back_callback=f"gctrl:back:{chat_id}",
        home_callback=None,
        close_callback=f"gctrl:close:{chat_id}",
        close_label="🔒 إغلاق",
    )


async def _show_radio_panel(cq, chat_id, radio_service):
    from bot.data.sources import QURANIC_RECITERS
    from bot.data.surahs import SURAHS
    from bot.services.quran_radio import estimate_duration

    state = radio_service.get_state(chat_id)
    if not state:
        await cq.message.edit_text("❌ الراديو غير نشط")
        return
    surah_num = state.queue[state.current_index]
    surah_name = SURAHS.get(surah_num, f"{surah_num}")
    reciter_name = QURANIC_RECITERS.get(state.reciter_key, {}).get(
        "name", state.reciter_key
    )
    dur = estimate_duration(surah_num)
    status = "⏸️ متوقف" if state.paused else "▶️ يعمل"
    text = (
        f"📻 **راديو القرآن**\n\n"
        f"{status}\n🎙️ {reciter_name}\n📖 {surah_num} - {surah_name}\n⏱ ~{dur} دقيقة\n"
        f"{'🔀 عشوائي' if state.shuffle else '🔀 تسلسلي'}"
    )
    from bot.handlers.quran_radio_handler import _radio_keyboard

    await cq.message.edit_text(
        text, reply_markup=_radio_keyboard(chat_id, state.paused, state.shuffle)
    )
