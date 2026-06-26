#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
وحدة أوامر الأذان - Azan Commands Module
تحتوي على جميع أوامر وميزات نظام الأذان
"""

import logging

from pyrogram import Client, filters
from pyrogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from azan_manager import (
    AzanNotificationManager,
    AzanScheduler,
    AzanStreamer,
)
from bot.prayer.calculator import CityCoordinates, PrayerTimeCalculator

logger = logging.getLogger(__name__)

# إنشاء نوى الأنظمة
azan_scheduler = AzanScheduler()
azan_streamer = AzanStreamer()
notification_manager = AzanNotificationManager()

# ============================================================================
# أوامر الأذان الرئيسية
# ============================================================================


async def register_azan_commands(app: Client):
    """تسجيل أوامر الأذان مع البوت"""

    # ========================================================================
    # الأمر: /azan_setup - إعداد الأذان
    # ========================================================================

    @app.on_message(filters.command("azan_setup") & filters.private)
    async def azan_setup(client: Client, message: Message):
        """إعداد نظام الأذان"""

        # عرض المدن المتاحة
        cities = CityCoordinates.get_all_cities()

        keyboard = []
        city_list = list(cities.keys())

        for i in range(0, len(city_list), 2):
            row = []
            if i < len(city_list):
                city = city_list[i]
                row.append(
                    InlineKeyboardButton(city, callback_data=f"azan_select_city:{city}")
                )
            if i + 1 < len(city_list):
                city = city_list[i + 1]
                row.append(
                    InlineKeyboardButton(city, callback_data=f"azan_select_city:{city}")
                )
            keyboard.append(row)

        reply_markup = InlineKeyboardMarkup(keyboard)

        await message.reply_text(
            "🕌 *اختر مدينتك لإعداد أوقات الأذان*\n\n"
            "_سيتم تحديد التوقيت الزمني تلقائياً حسب المدينة_",
            reply_markup=reply_markup,
        )

    # ========================================================================
    # معالج: اختيار المدينة
    # ========================================================================

    @app.on_callback_query(filters.regex("^azan_select_city:"))
    async def select_city_handler(client: Client, callback_query: CallbackQuery):
        """معالج اختيار المدينة"""
        user_id = callback_query.from_user.id
        city = callback_query.data.split(":", 1)[1]

        city_coords = CityCoordinates.get_city_coords(city)
        if not city_coords:
            await callback_query.answer("❌ المدينة غير متاحة", show_alert=True)
            return

        # إضافة المستخدم
        azan_scheduler.add_user(user_id, city)

        keyboard = [
            [
                InlineKeyboardButton(
                    "🇸🇦 كراتشي", callback_data=f"azan_select_method:{city}:karachi"
                ),
                InlineKeyboardButton(
                    "🇸🇦 أم القرى", callback_data=f"azan_select_method:{city}:makkah"
                ),
            ],
            [
                InlineKeyboardButton(
                    "🇺🇸 ISNA", callback_data=f"azan_select_method:{city}:isna"
                ),
                InlineKeyboardButton(
                    "🇪🇬 مصر", callback_data=f"azan_select_method:{city}:egypt"
                ),
            ],
            [
                InlineKeyboardButton(
                    "🇩🇿 الجزائر", callback_data=f"azan_select_method:{city}:algiers"
                ),
                InlineKeyboardButton(
                    "🇦🇪 دبي", callback_data=f"azan_select_method:{city}:dubai"
                ),
            ],
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)

        await callback_query.edit_message_text(
            f"✅ *تم اختيار: {city}*\n"
            f"🌍 الدولة: {city_coords['country']}\n"
            f"🕐 التوقيت: UTC{city_coords['tz']:+d}\n\n"
            "*اختر طريقة الحساب:*",
            reply_markup=reply_markup,
        )

    # ========================================================================
    # معالج: اختيار طريقة الحساب
    # ========================================================================

    @app.on_callback_query(filters.regex("^azan_select_method:"))
    async def select_method_handler(client: Client, callback_query: CallbackQuery):
        """معالج اختيار طريقة الحساب"""
        user_id = callback_query.from_user.id
        parts = callback_query.data.split(":")
        city = parts[1]
        method = parts[2]

        azan_scheduler.update_user_settings(user_id, method=method)

        method_info = PrayerTimeCalculator.CALCULATION_METHODS[method]

        keyboard = [
            [
                InlineKeyboardButton(
                    "المشاهدة", callback_data=f"azan_view_settings:{user_id}"
                )
            ],
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)

        await callback_query.edit_message_text(
            f"✅ *تم الإعداد بنجاح!*\n\n"
            f"📍 المدينة: {city}\n"
            f"📐 طريقة الحساب: {method_info['name']}\n\n"
            "_يمكنك الآن استخدام أوامر الأذان_\n"
            "اكتب /azan_times لعرض أوقات الصلاة\n"
            "اكتب /azan_settings لتخصيص الإعدادات",
            reply_markup=reply_markup,
        )

    # ========================================================================
    # الأمر: /azan_times - عرض أوقات الصلاة
    # ========================================================================

    @app.on_message(filters.command("azan_times") & filters.private)
    async def azan_times(client: Client, message: Message):
        """عرض أوقات الصلاة اليوم"""
        user_id = message.from_user.id

        settings = azan_scheduler.get_user_settings(user_id)
        if not settings:
            await message.reply_text(
                "❌ لم تقم بإعداد الأذان بعد\n" "اكتب /azan_setup للبدء"
            )
            return

        times = azan_scheduler.get_prayer_times(user_id)
        if not times:
            await message.reply_text("❌ خطأ في جلب أوقات الصلاة")
            return

        # بناء الرسالة
        text = "🕌 *أوقات الصلاة*\n"
        text += f"📍 {times['city']}, {times['country']}\n"
        text += f"📅 {times['date']}\n"
        text += f"📐 {times['method']}\n"
        text += "─" * 40 + "\n\n"

        prayers_order = ["fajr", "sunrise", "dhuhr", "asr", "sunset", "maghrib", "isha"]

        for prayer in prayers_order:
            if prayer in times:
                prayer_name = PrayerTimeCalculator.PRAYER_NAMES.get(prayer, prayer)
                prayer_time = times[prayer]
                text += f"{prayer_name} • {prayer_time}\n"

        keyboard = [
            [InlineKeyboardButton("🔄 تحديث", callback_data="azan_refresh_times")],
            [InlineKeyboardButton("⚙️ الإعدادات", callback_data="azan_settings_menu")],
            [InlineKeyboardButton("📻 تفعيل البث", callback_data="azan_enable_stream")],
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)

        await message.reply_text(text, parse_mode="Markdown", reply_markup=reply_markup)

    # ========================================================================
    # الأمر: /azan_settings - إعدادات الأذان
    # ========================================================================

    @app.on_message(filters.command("azan_settings") & filters.private)
    async def azan_settings(client: Client, message: Message):
        """عرض وتعديل إعدادات الأذان"""
        user_id = message.from_user.id

        settings = azan_scheduler.get_user_settings(user_id)
        if not settings:
            await message.reply_text(
                "❌ لم تقم بإعداد الأذان بعد\n" "اكتب /azan_setup للبدء"
            )
            return

        keyboard = [
            [
                InlineKeyboardButton(
                    "🔔 إعدادات التنبيهات", callback_data="azan_notification_settings"
                )
            ],
            [
                InlineKeyboardButton(
                    "🎵 إعدادات البث", callback_data="azan_stream_settings"
                )
            ],
            [
                InlineKeyboardButton(
                    "⏰ الصلوات المفعلة", callback_data="azan_prayer_selection"
                )
            ],
            [
                InlineKeyboardButton(
                    "🌍 تغيير المدينة", callback_data="azan_change_city"
                )
            ],
            [
                InlineKeyboardButton(
                    "📐 تغيير طريقة الحساب", callback_data="azan_change_method"
                )
            ],
            [InlineKeyboardButton("↩️ عودة", callback_data="azan_back_main")],
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)

        text = "⚙️ *إعدادات الأذان*\n\n"
        text += f"📍 المدينة: {settings.city}\n"
        text += f"🕐 التوقيت: {settings.timezone_name}\n"
        text += f"📐 الطريقة: {settings.method}\n"
        text += f"📊 طريقة العصر: {'Standard' if settings.asr_method == 'standard' else 'Hanafi'}\n\n"
        text += f"🔔 التنبيهات: {'✅ مفعلة' if settings.notification_enabled else '❌ معطلة'}\n"
        text += f"⏰ المقدمة: {'✅ مفعلة' if settings.prelude_enabled else '❌ معطلة'} ({settings.prelude_time} دقيقة)\n"
        text += f"🎵 البث: {'✅ مفعل' if settings.stream_enabled else '❌ معطل'}\n\n"
        text += f"🙏 الصلوات المفعلة: {', '.join(settings.enabled_prayers)}\n"

        await message.reply_text(text, parse_mode="Markdown", reply_markup=reply_markup)

    # ========================================================================
    # معالج: إعدادات التنبيهات
    # ========================================================================

    @app.on_callback_query(filters.regex("^azan_notification_settings"))
    async def notification_settings_handler(
        client: Client, callback_query: CallbackQuery
    ):
        """معالج إعدادات التنبيهات"""
        user_id = callback_query.from_user.id
        settings = azan_scheduler.get_user_settings(user_id)

        notif_status = "✅ مفعلة" if settings.notification_enabled else "❌ معطلة"
        prelude_status = "✅ مفعلة" if settings.prelude_enabled else "❌ معطلة"

        keyboard = [
            [
                InlineKeyboardButton(
                    f"التنبيهات {notif_status}",
                    callback_data="azan_toggle_notifications",
                )
            ],
            [
                InlineKeyboardButton(
                    f"المقدمة {prelude_status}", callback_data="azan_toggle_prelude"
                )
            ],
            [
                InlineKeyboardButton(
                    "⏱️ وقت المقدمة", callback_data="azan_set_prelude_time"
                )
            ],
            [InlineKeyboardButton("↩️ عودة", callback_data="azan_settings_menu")],
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)

        await callback_query.edit_message_text(
            "🔔 *إعدادات التنبيهات*\n\n"
            f"التنبيهات: {notif_status}\n"
            f"المقدمة: {prelude_status}\n"
            f"وقت المقدمة: {settings.prelude_time} دقيقة",
            reply_markup=reply_markup,
        )

    # ========================================================================
    # معالج: تفعيل/تعطيل التنبيهات
    # ========================================================================

    @app.on_callback_query(filters.regex("^azan_toggle_notifications"))
    async def toggle_notifications_handler(
        client: Client, callback_query: CallbackQuery
    ):
        """معالج تفعيل/تعطيل التنبيهات"""
        user_id = callback_query.from_user.id
        settings = azan_scheduler.get_user_settings(user_id)

        new_status = not settings.notification_enabled
        azan_scheduler.update_user_settings(user_id, notification_enabled=new_status)

        status_text = "✅ تم تفعيل" if new_status else "❌ تم تعطيل"
        await callback_query.answer(f"{status_text} التنبيهات", show_alert=True)

        # إعادة تحميل الصفحة
        await callback_query.edit_message_text(
            f"🔔 *إعدادات التنبيهات*\n\n"
            f"التنبيهات: {'✅ مفعلة' if new_status else '❌ معطلة'}\n"
            f"المقدمة: {'✅ مفعلة' if settings.prelude_enabled else '❌ معطلة'}\n"
            f"وقت المقدمة: {settings.prelude_time} دقيقة",
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            f"التنبيهات {'✅ مفعلة' if new_status else '❌ معطلة'}",
                            callback_data="azan_toggle_notifications",
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            f"المقدمة {'✅ مفعلة' if settings.prelude_enabled else '❌ معطلة'}",
                            callback_data="azan_toggle_prelude",
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            "⏱️ وقت المقدمة", callback_data="azan_set_prelude_time"
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            "↩️ عودة", callback_data="azan_settings_menu"
                        )
                    ],
                ]
            ),
        )

    # ========================================================================
    # معالج: تفعيل/تعطيل المقدمة
    # ========================================================================

    @app.on_callback_query(filters.regex("^azan_toggle_prelude"))
    async def toggle_prelude_handler(client: Client, callback_query: CallbackQuery):
        """معالج تفعيل/تعطيل المقدمة"""
        user_id = callback_query.from_user.id
        settings = azan_scheduler.get_user_settings(user_id)

        new_status = not settings.prelude_enabled
        azan_scheduler.update_user_settings(user_id, prelude_enabled=new_status)

        status_text = "✅ تم تفعيل" if new_status else "❌ تم تعطيل"
        await callback_query.answer(f"{status_text} المقدمة", show_alert=True)

        # إعادة تحميل الصفحة
        await callback_query.edit_message_text(
            f"🔔 *إعدادات التنبيهات*\n\n"
            f"التنبيهات: {'✅ مفعلة' if settings.notification_enabled else '❌ معطلة'}\n"
            f"المقدمة: {'✅ مفعلة' if new_status else '❌ معطلة'}\n"
            f"وقت المقدمة: {settings.prelude_time} دقيقة",
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            f"التنبيهات {'✅ مفعلة' if settings.notification_enabled else '❌ معطلة'}",
                            callback_data="azan_toggle_notifications",
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            f"المقدمة {'✅ مفعلة' if new_status else '❌ معطلة'}",
                            callback_data="azan_toggle_prelude",
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            "⏱️ وقت المقدمة", callback_data="azan_set_prelude_time"
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            "↩️ عودة", callback_data="azan_settings_menu"
                        )
                    ],
                ]
            ),
        )

    # ========================================================================
    # معالج: إعدادات البث
    # ========================================================================

    @app.on_callback_query(filters.regex("^azan_stream_settings"))
    async def stream_settings_handler(client: Client, callback_query: CallbackQuery):
        """معالج إعدادات البث"""
        user_id = callback_query.from_user.id
        settings = azan_scheduler.get_user_settings(user_id)

        stream_status = "✅ مفعل" if settings.stream_enabled else "❌ معطل"

        keyboard = [
            [
                InlineKeyboardButton(
                    f"البث {stream_status}", callback_data="azan_toggle_stream"
                )
            ],
            [
                InlineKeyboardButton(
                    "⏹️ توقيت الإيقاف", callback_data="azan_set_stop_before"
                )
            ],
            [
                InlineKeyboardButton(
                    "📻 مدة البث", callback_data="azan_set_stream_duration"
                )
            ],
            [InlineKeyboardButton("↩️ عودة", callback_data="azan_settings_menu")],
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)

        await callback_query.edit_message_text(
            "🎵 *إعدادات البث*\n\n"
            f"البث: {stream_status}\n"
            f"توقيت الإيقاف قبل الأذان: {settings.stream_stop_before} ثانية\n"
            f"مدة البث: {settings.stream_duration} ثانية",
            reply_markup=reply_markup,
        )

    # ========================================================================
    # معالج: تفعيل/تعطيل البث
    # ========================================================================

    @app.on_callback_query(filters.regex("^azan_toggle_stream"))
    async def toggle_stream_handler(client: Client, callback_query: CallbackQuery):
        """معالج تفعيل/تعطيل البث"""
        user_id = callback_query.from_user.id
        settings = azan_scheduler.get_user_settings(user_id)

        new_status = not settings.stream_enabled
        azan_scheduler.update_user_settings(user_id, stream_enabled=new_status)

        status_text = "✅ تم تفعيل" if new_status else "❌ تم تعطيل"
        await callback_query.answer(f"{status_text} البث", show_alert=True)

        # إعادة تحميل الصفحة
        await callback_query.edit_message_text(
            f"🎵 *إعدادات البث*\n\n"
            f"البث: {'✅ مفعل' if new_status else '❌ معطل'}\n"
            f"توقيت الإيقاف قبل الأذان: {settings.stream_stop_before} ثانية\n"
            f"مدة البث: {settings.stream_duration} ثانية",
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            f"البث {'✅ مفعل' if new_status else '❌ معطل'}",
                            callback_data="azan_toggle_stream",
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            "⏹️ توقيت الإيقاف", callback_data="azan_set_stop_before"
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            "📻 مدة البث", callback_data="azan_set_stream_duration"
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            "↩️ عودة", callback_data="azan_settings_menu"
                        )
                    ],
                ]
            ),
        )

    # ========================================================================
    # الأمر: /azan_next - الصلاة التالية
    # ========================================================================

    @app.on_message(filters.command("azan_next") & filters.private)
    async def azan_next(client: Client, message: Message):
        """عرض الصلاة التالية"""
        user_id = message.from_user.id

        settings = azan_scheduler.get_user_settings(user_id)
        if not settings:
            await message.reply_text(
                "❌ لم تقم بإعداد الأذان بعد\n" "اكتب /azan_setup للبدء"
            )
            return

        next_prayer = azan_scheduler.get_next_prayer(user_id)
        if not next_prayer:
            await message.reply_text("❌ لا توجد صلوات متبقية اليوم")
            return

        prayer_name = next_prayer["name"]
        prayer_time = next_prayer["time"]
        in_minutes = next_prayer.get("in_minutes", 0)
        is_tomorrow = next_prayer.get("tomorrow", False)

        date_text = "غداً" if is_tomorrow else "اليوم"

        text = f"{prayer_name}\n"
        text += f"⏰ {prayer_time} {date_text}\n"

        if not is_tomorrow and in_minutes >= 0:
            if in_minutes == 0:
                text += "⚠️ الآن! حان وقت الصلاة"
            elif in_minutes < 60:
                text += f"⏳ متبقي: {in_minutes} دقيقة"
            else:
                hours = in_minutes // 60
                mins = in_minutes % 60
                text += f"⏳ متبقي: {hours} ساعة و {mins} دقيقة"

        keyboard = [
            [InlineKeyboardButton("🔄 تحديث", callback_data="azan_refresh_next")],
            [
                InlineKeyboardButton(
                    "📅 أوقات اليوم", callback_data="azan_view_all_times"
                )
            ],
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)

        await message.reply_text(text, parse_mode="Markdown", reply_markup=reply_markup)

    # ========================================================================
    # الأمر: /azan_search - البحث عن مدينة
    # ========================================================================

    @app.on_message(filters.command("azan_search"))
    async def azan_search(client: Client, message: Message):
        """البحث عن مدينة"""
        if len(message.command) < 2:
            await message.reply_text(
                "الاستخدام: /azan_search <اسم المدينة>\n" "مثال: /azan_search مكة"
            )
            return

        query = " ".join(message.command[1:])
        cities = CityCoordinates.search_cities(query)

        if not cities:
            await message.reply_text(f"❌ لم يتم العثور على مدن تحتوي على '{query}'")
            return

        text = f"🔍 *نتائج البحث عن: {query}*\n\n"

        for city in cities[:10]:  # عرض أول 10 نتائج
            coords = CityCoordinates.get_city_coords(city)
            text += f"📍 {city} - {coords['country']}\n"

        await message.reply_text(text)

    # ========================================================================
    # معالج: عودة الأزرار
    # ========================================================================

    @app.on_callback_query(filters.regex("^azan_back_main"))
    async def back_main_handler(client: Client, callback_query: CallbackQuery):
        """معالج العودة للقائمة الرئيسية"""
        user_id = callback_query.from_user.id

        settings = azan_scheduler.get_user_settings(user_id)
        if not settings:
            await callback_query.answer("❌ لم تقم بإعداد الأذان", show_alert=True)
            return

        keyboard = [
            [InlineKeyboardButton("📅 أوقات الصلاة", callback_data="azan_view_times")],
            [
                InlineKeyboardButton(
                    "⏭️ الصلاة التالية", callback_data="azan_next_prayer"
                )
            ],
            [InlineKeyboardButton("⚙️ الإعدادات", callback_data="azan_settings_menu")],
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)

        await callback_query.edit_message_text(
            "🕌 *القائمة الرئيسية للأذان*\n\n"
            f"📍 المدينة: {settings.city}\n"
            f"🕐 التوقيت: {settings.timezone_name}",
            reply_markup=reply_markup,
        )

    # ========================================================================
    # معالج: الإعدادات (تحديث)
    # ========================================================================

    @app.on_callback_query(filters.regex("^azan_settings_menu"))
    async def settings_menu_handler(client: Client, callback_query: CallbackQuery):
        """معالج قائمة الإعدادات"""
        user_id = callback_query.from_user.id

        settings = azan_scheduler.get_user_settings(user_id)
        if not settings:
            await callback_query.answer("❌ لم تقم بإعداد الأذان", show_alert=True)
            return

        keyboard = [
            [
                InlineKeyboardButton(
                    "🔔 إعدادات التنبيهات", callback_data="azan_notification_settings"
                )
            ],
            [
                InlineKeyboardButton(
                    "🎵 إعدادات البث", callback_data="azan_stream_settings"
                )
            ],
            [
                InlineKeyboardButton(
                    "⏰ الصلوات المفعلة", callback_data="azan_prayer_selection"
                )
            ],
            [InlineKeyboardButton("↩️ عودة", callback_data="azan_back_main")],
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)

        await callback_query.edit_message_text(
            "⚙️ *إعدادات الأذان*", parse_mode="Markdown", reply_markup=reply_markup
        )


# ============================================================================
# تصدير الدالة
# ============================================================================

__all__ = [
    "register_azan_commands",
    "azan_scheduler",
    "azan_streamer",
    "notification_manager",
]
