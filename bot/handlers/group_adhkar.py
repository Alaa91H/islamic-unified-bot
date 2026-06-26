from bot.decorators import admin_only, safe_handler

_BOOL_MAP = {
    "1": True,
    "true": True,
    "نعم": True,
    "تشغيل": True,
    "0": False,
    "false": False,
    "لا": False,
    "تعطيل": False,
}


def _parse_bool(v: str):
    return _BOOL_MAP.get(v.strip().lower())


def register(app, deps) -> None:
    from pyrogram import filters
    from pyrogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup

    from bot.db.repositories.adhkar_settings import AdhkarSettings

    repo = deps.adhkar_repo

    def _settings_keyboard(s, chat_id):
        return InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        f"{'✅' if s.interval_enabled else '❌'} الذكر الدوري ({s.interval_minutes}د)",
                        callback_data=f"adhk_toggle:interval:{chat_id}",
                    )
                ],
                [
                    InlineKeyboardButton(
                        "⏱ تغيير المدة", callback_data=f"adhk_setmin:{chat_id}"
                    )
                ],
                [
                    InlineKeyboardButton(
                        f"{'✅' if s.morning_enabled else '❌'} أذكار الصباح ({s.morning_time})",
                        callback_data=f"adhk_toggle:morning:{chat_id}",
                    )
                ],
                [
                    InlineKeyboardButton(
                        f"{'✅' if s.evening_enabled else '❌'} أذكار المساء ({s.evening_time})",
                        callback_data=f"adhk_toggle:evening:{chat_id}",
                    )
                ],
                [
                    InlineKeyboardButton(
                        f"{'✅' if s.friday_enabled else '❌'} أذكار الجمعة ({s.friday_time})",
                        callback_data=f"adhk_toggle:friday:{chat_id}",
                    )
                ],
                [InlineKeyboardButton("🔒 إغلاق", callback_data="adhk_close")],
            ]
        )

    @app.on_message(filters.group & filters.command("adhkar"))
    @admin_only(app)
    @safe_handler()
    async def adhkar_cmd(client, message):
        chat_id = message.chat.id
        s = await repo.get(chat_id) or AdhkarSettings(chat_id=chat_id)
        await message.reply_text(
            "🕌 **إعدادات الأذكار**\n\n"
            "تحكم في إرسال الأذكار للمجموعة:\n"
            "• **الدوري**: ذكر عشوائي كل فترة\n"
            "• **الصباح**: أذكار الصباح يومياً\n"
            "• **المساء**: أذكار المساء يومياً\n"
            "• **الجمعة**: أذكار خاصة يوم الجمعة",
            reply_markup=_settings_keyboard(s, chat_id),
        )

    @app.on_callback_query(filters.regex("^adhk_toggle:"))
    @admin_only(app)
    @safe_handler()
    async def adhk_toggle(client, cq: CallbackQuery):
        _, key, chat_id_str = cq.data.split(":")
        chat_id = int(chat_id_str)
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
        await cq.message.edit_reply_markup(reply_markup=_settings_keyboard(s, chat_id))
        await cq.answer("✅ تم التحديث")

    @app.on_callback_query(filters.regex("^adhk_setmin:"))
    @admin_only(app)
    @safe_handler()
    async def adhk_setmin_prompt(client, cq: CallbackQuery):
        _, chat_id_str = cq.data.split(":")
        chat_id = int(chat_id_str)
        s = await repo.get(chat_id) or AdhkarSettings(chat_id=chat_id)
        await cq.message.edit_text(
            f"⏱ **المدة الحالية**: {s.interval_minutes} دقيقة\n\n"
            "أرسل عدد الدقائق الجديد (مثال: `30`)\n"
            "أو أرسل `/cancel` للإلغاء",
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "🔙 رجوع", callback_data=f"adhk_back:{chat_id}"
                        )
                    ]
                ]
            ),
        )

        try:
            answer = await client.ask(
                cq.message.chat.id,
                "أرسل عدد الدقائق الجديد (مثال: `30`)\nأو أرسل `/cancel` للإلغاء",
                timeout=60,
                filters=filters.text,
            )
        except TimeoutError:
            await cq.message.reply_text("❌ انتهت المهلة")
            return

        txt = answer.text.strip()
        if txt == "/cancel":
            await answer.reply_text("✅ أُلغيت")
            return
        try:
            mins = int(txt)
            if mins < 1:
                raise ValueError
        except ValueError:
            await answer.reply_text("❌ الرجاء إدخال رقم صحيح (دقائق)")
            return
        s = await repo.get(chat_id) or AdhkarSettings(chat_id=chat_id)
        s.interval_minutes = mins
        await repo.upsert(s)
        await answer.reply_text(f"✅ تم تعيين المدة إلى {mins} دقيقة")

    @app.on_callback_query(filters.regex("^adhk_back:"))
    @safe_handler()
    async def adhk_back(client, cq: CallbackQuery):
        _, chat_id_str = cq.data.split(":")
        chat_id = int(chat_id_str)
        s = await repo.get(chat_id) or AdhkarSettings(chat_id=chat_id)
        await cq.message.edit_text(
            "🕌 **إعدادات الأذكار**",
            reply_markup=_settings_keyboard(s, chat_id),
        )

    @app.on_callback_query(filters.regex("^adhk_close$"))
    @safe_handler()
    async def adhk_close(client, cq: CallbackQuery):
        await cq.message.delete()
