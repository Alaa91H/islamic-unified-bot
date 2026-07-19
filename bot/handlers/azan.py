from datetime import datetime

from bot.decorators import safe_handler
from bot.handlers.ui import markup_with_bottom_controls


def city_selection_keyboard():
    from pyrogram.types import InlineKeyboardButton
    from bot.prayer.calculator import CityCoordinates

    cities = CityCoordinates.get_all_cities()
    kb = []
    city_list = list(cities.keys())
    for i in range(0, len(city_list), 2):
        row = []
        row.append(
            InlineKeyboardButton(
                city_list[i], callback_data=f"azan_city:{city_list[i]}"
            )
        )
        if i + 1 < len(city_list):
            row.append(
                InlineKeyboardButton(
                    city_list[i + 1], callback_data=f"azan_city:{city_list[i + 1]}"
                )
            )
        kb.append(row)
    return markup_with_bottom_controls(
        kb, back_callback="back_to_start", home_callback=None
    )


def method_selection_keyboard(city: str):
    from pyrogram.types import InlineKeyboardButton
    from bot.prayer.calculator import CityCoordinates

    recommended = CityCoordinates.get_recommended_method(city)
    methods = [
        ("🇸🇦 كراتشي", "karachi"),
        ("🇸🇦 أم القرى", "makkah"),
        ("🇺🇸 ISNA", "isna"),
        ("🇪🇬 مصر", "egypt"),
        ("🇩🇿 الجزائر", "algiers"),
        ("🇦🇪 دبي", "dubai"),
        ("🌍 رابطة العالم الإسلامي", "mwl"),
    ]
    kb = []
    for label, key in methods:
        mark = "⭐ " if key == recommended else ""
        kb.append(
            [
                InlineKeyboardButton(
                    f"{mark}{label}", callback_data=f"azan_method:{city}:{key}"
                )
            ]
        )
    return markup_with_bottom_controls(
        kb, back_callback="azan_home", back_label="🔙 الأذان"
    )


def settings_keyboard():
    from pyrogram.types import InlineKeyboardButton

    return markup_with_bottom_controls(
        [
            [
                InlineKeyboardButton(
                    "🔔 إعدادات التنبيهات", callback_data="azan_notif_settings"
                )
            ],
            [
                InlineKeyboardButton(
                    "🎵 إعدادات البث", callback_data="azan_stream_settings"
                )
            ],
            [
                InlineKeyboardButton(
                    "⏰ الصلوات المفعلة", callback_data="azan_prayer_sel"
                )
            ],
            [InlineKeyboardButton("📊 طريقة العصر", callback_data="azan_asr_menu")],
            [InlineKeyboardButton("🌍 تغيير المدينة", callback_data="azan_home")],
        ],
        back_callback="azan_home",
        back_label="🔙 الأذان",
    )


def register(app, deps) -> None:
    from pyrogram import filters

    user_repo = deps.user_repo

    @app.on_message(filters.command("azan_setup") & filters.private)
    @safe_handler()
    async def azan_setup_cmd(client, message):
        await message.reply_text(
            "🕌 **اختر مدينتك لإعداد أوقات الأذان**\n_سيتم تحديد التوقيت تلقائياً_",
            reply_markup=city_selection_keyboard(),
        )

    @app.on_callback_query(filters.regex("^azan_city:"))
    @safe_handler()
    async def city_handler(client, cq):
        from bot.prayer.calculator import CityCoordinates, PrayerTimeCalculator

        city = cq.data.split(":", 1)[1]
        coords = CityCoordinates.get_city_coords(city)
        if not coords:
            await cq.answer("❌ المدينة غير متاحة", show_alert=True)
            return
        recommended_method_key = CityCoordinates.get_recommended_method(city)
        rec_method = PrayerTimeCalculator.CALCULATION_METHODS[recommended_method_key][
            "name"
        ]
        await cq.message.edit_text(
            f"✅ **تم اختيار: {city}**\n"
            f"🌍 {coords['country']}\n"
            f"🕐 UTC{coords['tz']:+d}\n"
            f"⭐ الطريقة الموصى بها: {rec_method}\n\n"
            "**اختر طريقة الحساب:**",
            reply_markup=method_selection_keyboard(city),
        )

    @app.on_callback_query(filters.regex("^azan_method:"))
    @safe_handler()
    async def method_handler(client, cq):
        from bot.prayer.calculator import CityCoordinates, PrayerTimeCalculator
        from bot.db.repositories.user_settings import UserSettings

        parts = cq.data.split(":")
        city, method = parts[1], parts[2]
        user_id = cq.from_user.id
        coords = CityCoordinates.get_city_coords(city)

        settings = UserSettings(
            user_id=user_id,
            city=city,
            method=method,
            timezone=coords["tz"],
        )
        await user_repo.upsert(settings)

        method_name = PrayerTimeCalculator.CALCULATION_METHODS[method]["name"]
        await cq.message.edit_text(
            f"✅ **تم الإعداد بنجاح!**\n\n"
            f"📍 {city}\n📐 {method_name}\n\n"
            "اكتب /azan_times لعرض أوقات الصلاة\n"
            "اكتب /azan_settings لتخصيص الإعدادات",
        )

    @app.on_message(filters.command("azan_times") & filters.private)
    @safe_handler()
    async def azan_times_cmd(client, message):
        from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
        from bot.prayer.calculator import CityCoordinates, PrayerTimeCalculator

        user_id = message.from_user.id
        settings = await user_repo.get(user_id)
        if not settings:
            await message.reply_text("❌ لم تقم بالإعداد بعد.\nاكتب /azan_setup للبدء")
            return

        coords = CityCoordinates.get_city_coords(settings.city)
        if not coords:
            await message.reply_text("❌ المدينة غير معروفة")
            return

        calc = PrayerTimeCalculator(
            latitude=coords["lat"],
            longitude=coords["lng"],
            timezone=coords["tz"],
            method=settings.method,
            asr_method=settings.asr_method,
            dst=coords.get("dst", False),
            city_name=settings.city,
        )
        times = calc.calculate_times(datetime.now())

        text = f"🕌 **أوقات الصلاة**\n📍 {settings.city}, {coords['country']}\n"
        text += f"📐 {calc.get_method_name()}\n"
        text += "─" * 30 + "\n"
        for p in [
            "imsak",
            "fajr",
            "sunrise",
            "dhuhr",
            "asr",
            "sunset",
            "maghrib",
            "isha",
            "midnight",
        ]:
            if p in times:
                name = PrayerTimeCalculator.PRAYER_NAMES.get(p, p)
                text += f"{name} • {times[p]}\n"

        await message.reply_text(
            text,
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "⚙️ الإعدادات", callback_data="azan_settings_menu"
                        )
                    ],
                ]
            ),
        )

    @app.on_message(filters.command("azan_next") & filters.private)
    @safe_handler()
    async def azan_next_cmd(client, message):
        from bot.prayer.calculator import CityCoordinates, PrayerTimeCalculator

        user_id = message.from_user.id
        settings = await user_repo.get(user_id)
        if not settings:
            await message.reply_text("❌ لم تقم بالإعداد بعد.\nاكتب /azan_setup للبدء")
            return

        now = datetime.now()
        coords = CityCoordinates.get_city_coords(settings.city)
        if not coords:
            return

        calc = PrayerTimeCalculator(
            latitude=coords["lat"],
            longitude=coords["lng"],
            timezone=coords["tz"],
            method=settings.method,
            asr_method=settings.asr_method,
        )
        times = calc.calculate_times(now)
        now_hhmm = now.strftime("%H:%M")
        prayers = ["fajr", "dhuhr", "asr", "maghrib", "isha"]

        for p in prayers:
            if p in times and times[p] > now_hhmm:
                name = PrayerTimeCalculator.PRAYER_NAMES.get(p, p)
                h1, m1 = map(int, times[p].split(":"))
                h2, m2 = map(int, now_hhmm.split(":"))
                diff = (h1 * 60 + m1) - (h2 * 60 + m2)
                await message.reply_text(
                    f"{name}\n⏰ {times[p]}\n⏳ متبقي: {diff} دقيقة"
                )
                return

        await message.reply_text("❌ لا توجد صلوات متبقية اليوم")

    @app.on_message(filters.command("azan_search"))
    @safe_handler()
    async def azan_search_cmd(client, message):
        from bot.prayer.calculator import CityCoordinates

        if len(message.command) < 2:
            await message.reply_text("الاستخدام: /azan_search <اسم المدينة>")
            return
        query = " ".join(message.command[1:])
        results = CityCoordinates.search_cities(query)
        if not results:
            await message.reply_text(f"❌ لا توجد نتائج لـ '{query}'")
            return
        text = "🔍 **نتائج البحث:**\n" + "\n".join(f"📍 {c}" for c in results[:10])
        await message.reply_text(text)

    @app.on_message(filters.command("azan_settings") & filters.private)
    @safe_handler()
    async def azan_settings_cmd(client, message):
        user_id = message.from_user.id
        settings = await user_repo.get(user_id)
        if not settings:
            await message.reply_text("❌ لم تقم بالإعداد بعد.\nاكتب /azan_setup للبدء")
            return
        text = (
            f"⚙️ **إعدادات الأذان**\n\n"
            f"📍 {settings.city}\n"
            f"📐 {settings.method}\n"
            f"📊 العصر: {settings.asr_method}\n"
            f"🔔 التنبيهات: {'✅' if settings.notifications_on else '❌'}\n"
            f"⏰ المقدمة: {'✅' if settings.prelude_on else '❌'} ({settings.prelude_minutes}د)\n"
        )
        await message.reply_text(text, reply_markup=settings_keyboard())

    @app.on_callback_query(filters.regex("^azan_settings_menu$"))
    @safe_handler()
    async def settings_menu_handler(client, cq):
        await cq.message.edit_text(
            "⚙️ **إعدادات الأذان**", reply_markup=settings_keyboard()
        )

    @app.on_callback_query(filters.regex("^azan_home$"))
    @safe_handler()
    async def azan_home_handler(client, cq):
        await cq.message.edit_text(
            "🕌 **نظام الأذان وأوقات الصلاة**\n\n"
            "/azan_setup - إعداد مدينتك\n"
            "/azan_times - أوقات الصلاة اليوم\n"
            "/azan_next - الصلاة التالية\n"
            "/azan_settings - الإعدادات\n"
            "/azan_search [مدينة] - البحث",
            reply_markup=markup_with_bottom_controls(
                [], back_callback="back_to_start", home_callback=None
            ),
        )

    @app.on_callback_query(filters.regex("^azan_notif_settings"))
    @safe_handler()
    async def notif_settings_handler(client, cq):
        from pyrogram.types import InlineKeyboardButton

        user_id = cq.from_user.id
        s = await user_repo.get(user_id)
        if not s:
            return
        notif = "✅ مفعلة" if s.notifications_on else "❌ معطلة"
        prel = "✅ مفعلة" if s.prelude_on else "❌ معطلة"
        await cq.message.edit_text(
            f"🔔 **إعدادات التنبيهات**\nالتنبيهات: {notif}\nالمقدمة: {prel}\nوقت المقدمة: {s.prelude_minutes}د",
            reply_markup=markup_with_bottom_controls(
                [
                    [
                        InlineKeyboardButton(
                            f"التنبيهات {notif}", callback_data="azan_toggle_notif"
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            f"المقدمة {prel}", callback_data="azan_toggle_prelude"
                        )
                    ],
                ],
                back_callback="azan_settings_menu",
                back_label="🔙 الإعدادات",
            ),
        )

    @app.on_callback_query(filters.regex("^azan_toggle_notif"))
    @safe_handler()
    async def toggle_notif(client, cq):
        uid = cq.from_user.id
        s = await user_repo.get(uid)
        if s:
            await user_repo.update_partial(uid, notifications_on=not s.notifications_on)
            await cq.answer("✅ تم التبديل", show_alert=True)
        await notif_settings_handler(client, cq)

    @app.on_callback_query(filters.regex("^azan_toggle_prelude"))
    @safe_handler()
    async def toggle_prelude(client, cq):
        uid = cq.from_user.id
        s = await user_repo.get(uid)
        if s:
            await user_repo.update_partial(uid, prelude_on=not s.prelude_on)
            await cq.answer("✅ تم التبديل", show_alert=True)
        await notif_settings_handler(client, cq)

    @app.on_callback_query(filters.regex("^azan_stream_settings$"))
    @safe_handler()
    async def stream_settings_handler(client, cq):
        from bot.data.sources import AZAN_SOURCES

        uid = cq.from_user.id
        s = await user_repo.get(uid)
        if not s:
            return
        source = s.azan_source or "traditional"
        lines = ["🎵 **إعدادات البث**\n", f"مصدر الأذان الحالي: **{source}**\n"]
        for key, info in AZAN_SOURCES.items():
            lines.append(f"• {info.get('name', key)}")
        await cq.message.edit_text(
            "\n".join(lines),
            reply_markup=markup_with_bottom_controls(
                [], back_callback="azan_settings_menu", back_label="🔙 الإعدادات"
            ),
        )

    @app.on_callback_query(filters.regex("^azan_prayer_sel$"))
    @safe_handler()
    async def prayer_sel_handler(client, cq):
        from pyrogram.types import InlineKeyboardButton

        uid = cq.from_user.id
        s = await user_repo.get(uid)
        if not s:
            return
        enabled = s.enabled_prayers or ["fajr", "dhuhr", "asr", "maghrib", "isha"]
        prayer_list = [
            ("fajr", "🌅 الفجر"),
            ("dhuhr", "☀️ الظهر"),
            ("asr", "⛅ العصر"),
            ("maghrib", "🌆 المغرب"),
            ("isha", "🌙 العشاء"),
        ]
        kb = []
        for key, label in prayer_list:
            mark = "✅" if key in enabled else "❌"
            kb.append(
                [
                    InlineKeyboardButton(
                        f"{mark} {label}", callback_data=f"azan_toggle_prayer:{key}"
                    )
                ]
            )
        await cq.message.edit_text(
            "⏰ **اختر الصلوات المفعلة للتنبيه:**",
            reply_markup=markup_with_bottom_controls(
                kb, back_callback="azan_settings_menu", back_label="🔙 الإعدادات"
            ),
        )

    @app.on_callback_query(filters.regex("^azan_toggle_prayer:"))
    @safe_handler()
    async def toggle_prayer_handler(client, cq):
        uid = cq.from_user.id
        prayer = cq.data.split(":", 1)[1]
        s = await user_repo.get(uid)
        if not s:
            return
        enabled = list(s.enabled_prayers or ["fajr", "dhuhr", "asr", "maghrib", "isha"])
        if prayer in enabled:
            if len(enabled) > 1:
                enabled.remove(prayer)
        else:
            enabled.append(prayer)
        await user_repo.update_partial(uid, enabled_prayers=enabled)
        await cq.answer(f"✅ تم تبديل {prayer}")
        await prayer_sel_handler(client, cq)

    @app.on_callback_query(filters.regex("^azan_asr_menu$"))
    @safe_handler()
    async def asr_menu_handler(client, cq):
        from pyrogram.types import InlineKeyboardButton

        uid = cq.from_user.id
        s = await user_repo.get(uid)
        current = s.asr_method if s else "standard"
        methods = [("standard", "قياسي (شافعي)"), ("hanafi", "حنفي")]
        kb = []
        for key, label in methods:
            mark = "✅" if key == current else ""
            kb.append(
                [
                    InlineKeyboardButton(
                        f"{mark} {label}", callback_data=f"azan_asr_method:{key}"
                    )
                ]
            )
        await cq.message.edit_text(
            "📊 **طريقة حساب العصر**\n\nاختر الطريقة:",
            reply_markup=markup_with_bottom_controls(
                kb, back_callback="azan_settings_menu", back_label="🔙 الإعدادات"
            ),
        )

    @app.on_callback_query(filters.regex("^azan_asr_method:"))
    @safe_handler()
    async def asr_method_handler(client, cq):
        uid = cq.from_user.id
        method = cq.data.split(":", 1)[1]
        await user_repo.update_partial(uid, asr_method=method)
        await cq.answer(f"✅ تم تغيير العصر إلى {method}")
        s = await user_repo.get(uid)
        text = (
            f"⚙️ **إعدادات الأذان**\n\n"
            f"📍 {s.city}\n"
            f"📐 {s.method}\n"
            f"📊 العصر: {s.asr_method}\n"
            f"🔔 التنبيهات: {'✅' if s.notifications_on else '❌'}\n"
            f"⏰ المقدمة: {'✅' if s.prelude_on else '❌'} ({s.prelude_minutes}د)\n"
        )
        await cq.message.edit_text(text, reply_markup=settings_keyboard())
