"""مسار Bot API تجريبي ومدروس لنقل أوامر Telegram البسيطة إلى aiogram.

لا يبدأ هذا المسار مع Pyrogram في الوقت نفسه، لأن long polling لنفس bot token
يسبب تعارض تحديثات. لا يعرض الـpilot إلا callbacks التي ينفذها Router الحالي.
"""

from __future__ import annotations


def _home_keyboard():
    """لوحة pilot لا تعرض إلا callbacks التي ينفذها Router الحالي."""
    from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📖 القرآن الكريم", callback_data="quran_text:home"
                ),
            ],
            [InlineKeyboardButton(text="📿 الأذكار", callback_data="adhkar:home")],
            [InlineKeyboardButton(text="🤲 الأدعية", callback_data="dua:home")],
            [
                InlineKeyboardButton(
                    text="📅 التاريخ الهجري", callback_data="hijri:today"
                )
            ],
            [InlineKeyboardButton(text="🕋 اتجاه القبلة", callback_data="qibla:help")],
            [InlineKeyboardButton(text="🌙 رمضان", callback_data="ramadan:today")],
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


def _quran_text_keyboard():
    """لوحة اختيار السور لمسار aiogram النصي فقط، بلا عناصر بث غير مهاجرة."""
    from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

    buttons = []
    row = []
    for surah in range(1, 115):
        row.append(
            InlineKeyboardButton(text=str(surah), callback_data=f"qts:{surah}:0")
        )
        if len(row) == 10:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    buttons.append(
        [InlineKeyboardButton(text="🔙 الرئيسية", callback_data="back_to_start")]
    )
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def _parse_qts_callback(data: str) -> tuple[int, int, bool] | None:
    """تحقق من callback لقراءة القرآن قبل الوصول إلى بيانات السور."""
    parts = data.split(":")
    if len(parts) not in {3, 4} or parts[0] != "qts":
        return None
    if len(parts) == 4 and parts[3] != "tafsir":
        return None
    try:
        surah, page = int(parts[1]), int(parts[2])
    except ValueError:
        return None
    if not 1 <= surah <= 114 or page < 0:
        return None
    return surah, page, len(parts) == 4


def _quran_info_keyboard(surah: int):
    from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📖 عرض الآيات", callback_data=f"qts:{surah}:1"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔍 تفسير السورة", callback_data=f"qts:{surah}:1:tafsir"
                )
            ],
            [InlineKeyboardButton(text="🔙 السور", callback_data="quran_text:home")],
            [InlineKeyboardButton(text="⌂ الرئيسية", callback_data="back_to_start")],
        ]
    )


def _quran_page_keyboard(surah: int, page: int, total_pages: int, show_tafsir: bool):
    from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

    navigation = []
    suffix = ":tafsir" if show_tafsir else ""
    if page > 1:
        navigation.append(
            InlineKeyboardButton(
                text="⬅️ السابق", callback_data=f"qts:{surah}:{page - 1}{suffix}"
            )
        )
    if page < total_pages:
        navigation.append(
            InlineKeyboardButton(
                text="التالي ➡️", callback_data=f"qts:{surah}:{page + 1}{suffix}"
            )
        )
    toggle_label = "🔍 إخفاء التفسير" if show_tafsir else "🔍 إظهار التفسير"
    toggle_data = f"qts:{surah}:{page}" + ("" if show_tafsir else ":tafsir")
    rows = [navigation] if navigation else []
    rows.extend(
        [
            [InlineKeyboardButton(text=toggle_label, callback_data=toggle_data)],
            [
                InlineKeyboardButton(
                    text="ℹ️ معلومات السورة", callback_data=f"qts:{surah}:0"
                )
            ],
            [InlineKeyboardButton(text="🔙 السور", callback_data="quran_text:home")],
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _adhkar_categories_keyboard():
    """لوحة فئات الأذكار لمسار aiogram النصي فقط."""
    from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

    from bot.data.adhkar import ADHKAR_CATEGORIES

    rows = [
        [InlineKeyboardButton(text=title, callback_data=f"adhkar:category:{key}")]
        for key, title in ADHKAR_CATEGORIES.items()
    ]
    rows.append(
        [InlineKeyboardButton(text="🔙 الرئيسية", callback_data="back_to_start")]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _adhkar_items_keyboard(category: str):
    """لوحة أذكار فئة مؤكدة أو None لفئة غير صالحة."""
    from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

    from bot.data.adhkar import ADHKAR

    items = ADHKAR.get(category, [])
    if not items:
        return None
    rows = [
        [
            InlineKeyboardButton(
                text=f"{index + 1}. {item['title'][:35]}",
                callback_data=f"adhkar:item:{category}:{index}",
            )
        ]
        for index, item in enumerate(items)
    ]
    rows.extend(
        [
            [InlineKeyboardButton(text="🔙 الفئات", callback_data="adhkar:home")],
            [InlineKeyboardButton(text="⌂ الرئيسية", callback_data="back_to_start")],
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _adhkar_item_detail(category: str, index: int) -> tuple[str, object] | None:
    """أعد تفاصيل الذكر ولوحة العودة أو None لمعرف غير صالح."""
    from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

    from bot.data.adhkar import ADHKAR

    items = ADHKAR.get(category, [])
    if not 0 <= index < len(items):
        return None
    item = items[index]
    text = (
        f"🕌 **{item['title']}**\n\n"
        f"📝 **النص:**\n{item['text']}\n\n"
        f"✨ **الفضل:**\n{item['benefit']}"
    )
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🔙 الفئة", callback_data=f"adhkar:category:{category}"
                )
            ],
            [InlineKeyboardButton(text="⌂ الرئيسية", callback_data="back_to_start")],
        ]
    )
    return text, keyboard


def _parse_adhkar_callback(data: str) -> tuple[str, str, int | None] | None:
    """تحقق من callback الأذكار وحمّل فقط فئات وعناصر البيانات المحلية الصحيحة."""
    from bot.data.adhkar import ADHKAR, ADHKAR_CATEGORIES

    parts = data.split(":")
    if parts == ["adhkar", "home"]:
        return "home", "", None
    if len(parts) == 3 and parts[:2] == ["adhkar", "category"]:
        category = parts[2]
        if category in ADHKAR_CATEGORIES and ADHKAR.get(category):
            return "category", category, None
        return None
    if len(parts) == 4 and parts[:2] == ["adhkar", "item"]:
        category = parts[2]
        try:
            index = int(parts[3])
        except ValueError:
            return None
        if category in ADHKAR and 0 <= index < len(ADHKAR[category]):
            return "item", category, index
    return None


def _dua_categories_keyboard():
    """لوحة الأدعية الثابتة لمسار aiogram النصي فقط."""
    from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

    from bot.data.duas import DUA_CATEGORY_KEYS

    rows = [
        [InlineKeyboardButton(text=category, callback_data=f"dua:show:{category}")]
        for category in DUA_CATEGORY_KEYS
    ]
    rows.append(
        [InlineKeyboardButton(text="🔙 الرئيسية", callback_data="back_to_start")]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _parse_dua_callback(data: str) -> str | None:
    """تحقق من callback الأدعية قبل قراءة بياناته المحلية."""
    from bot.data.duas import DUA_CATEGORIES

    if data == "dua:home":
        return ""
    parts = data.split(":", 2)
    if len(parts) == 3 and parts[:2] == ["dua", "show"]:
        category = parts[2]
        if category in DUA_CATEGORIES:
            return category
    return None


def _dua_detail(category: str) -> str | None:
    """أعد نص الدعاء الموثق أو None لفئة غير صالحة."""
    from bot.data.duas import DUA_CATEGORIES

    info = DUA_CATEGORIES.get(category)
    if info is None:
        return None
    return f"🤲 **{category}**\n\n_{info['dua']}_\n\n📚 {info['source']}"


def _hijri_text(today) -> str:
    """أنشئ نص التاريخ الهجري من التاريخ الحالي دون اعتماد على Telegram."""
    from bot.data.duas import ARABIC_MONTHS
    from bot.islamic_calendar import to_hijri

    hijri = to_hijri(today)
    if hijri is None:
        return "❌ تعذر حساب التاريخ الهجري"
    day, month, year = hijri
    return (
        "📅 **التاريخ الهجري**\n\n"
        f"اليوم: {today.strftime('%A')}\n"
        f"ميلادي: {today.strftime('%d %B %Y')}\n"
        f"هجري: {day} {ARABIC_MONTHS[month]} {year} هـ\n"
    )


def _qibla_help_text() -> str:
    """نص مساعدة القبلة لمسار aiogram دون أي callback إدخال حر."""

    return "🕋 **اتجاه القبلة**\n\nاستخدم الأمر: `/qibla [اسم المدينة]`\nمثال: `/qibla الرياض`"


def _qibla_text(city: str) -> str:
    """أعد نتيجة القبلة من مدينة محلية أو رسالة مساعدة/اقتراح محددة."""
    from bot.prayer.calculator import CityCoordinates
    from bot.qibla import calculate_qibla

    city = city.strip()
    if not city:
        return _qibla_help_text()
    coordinates = CityCoordinates.get_city_coords(city)
    if coordinates is None:
        suggestions = CityCoordinates.search_cities(city)
        if suggestions:
            names = "\n".join(f"• {name}" for name in suggestions[:5])
            return (
                f"⚠️ لم أجد '{city}' بالتحديد. هل تقصد:\n{names}\n\n"
                "استخدم `/qibla [الاسم الدقيق]`"
            )
        return f"❌ لم أجد مدينة '{city}'"
    latitude = coordinates.get("lat")
    longitude = coordinates.get("lng")
    if latitude is None or longitude is None:
        return f"❌ لا تتوفر إحداثيات صالحة لمدينة '{city}'"
    result = calculate_qibla(float(latitude), float(longitude))
    return (
        "🕋 **اتجاه القبلة**\n\n"
        f"📍 **المدينة:** {city}\n"
        f"🧭 **الاتجاه:** {result.bearing_degrees:.1f}° ({result.compass})\n"
        f"📏 **المسافة:** {result.distance_km:.0f} كم عن مكة"
    )


def _ramadan_text(today) -> str:
    """أنشئ محتوى رمضان المحلي لمسار aiogram من دون استدعاء خارجي."""
    from bot.data.zakat import RAMADAN_DUAS
    from bot.islamic_calendar import to_hijri
    from bot.islamic_content import ramadan_status

    ramadan_info = ramadan_status(to_hijri(today))
    dua_lines = "\n\n".join(
        f"**{dua['name']}:**\n_{dua['dua']}_\n📚 {dua['source']}"
        for dua in RAMADAN_DUAS
    )
    return (
        f"🌙 **رمضان مبارك**\n\n{ramadan_info}"
        "**مواقيت:**\n• السحور: قبل الفجر بـ 10-20 د\n• الإمساك: أذان الفجر\n"
        f"• الإفطار: أذان المغرب\n\n**أدعية رمضانية:**\n\n{dua_lines}"
    )


def create_main_menu_router():
    """أنشئ Router للأوامر النصية فقط دون اعتماد على Pyrogram أو MTProto."""
    from aiogram import F, Router
    from aiogram.filters import Command, CommandStart

    from bot.handlers.main_menu import (
        ABOUT_TEXT,
        GROUP_HELP,
        PRIVATE_HELP,
        WELCOME_TEXT,
    )

    router = Router(name="main-menu-pilot")

    async def show_quran_landing(message, *, edit: bool = False):
        text = "📖 **القرآن الكريم - النص والتفسير**\n\nاختر رقم السورة لعرض آياتها:"
        if edit:
            await message.edit_text(text, reply_markup=_quran_text_keyboard())
        else:
            await message.answer(text, reply_markup=_quran_text_keyboard())

    async def show_adhkar_landing(message, *, edit: bool = False):
        text = "📿 **الأذكار الإسلامية الشاملة**\n\nاختر الفئة:"
        if edit:
            await message.edit_text(text, reply_markup=_adhkar_categories_keyboard())
        else:
            await message.answer(text, reply_markup=_adhkar_categories_keyboard())

    async def show_dua_landing(message, *, edit: bool = False):
        text = "🤲 **الأدعية الجامعة**\n\nاختر تصنيفاً:"
        if edit:
            await message.edit_text(text, reply_markup=_dua_categories_keyboard())
        else:
            await message.answer(text, reply_markup=_dua_categories_keyboard())

    async def show_hijri(message, *, edit: bool = False):
        from bot.time_utils import utc_now

        text = _hijri_text(utc_now().date())
        if edit:
            await message.edit_text(text, reply_markup=_home_keyboard())
        else:
            await message.answer(text, reply_markup=_home_keyboard())

    async def show_ramadan(message, *, edit: bool = False):
        from bot.time_utils import utc_now

        text = _ramadan_text(utc_now().date())
        if edit:
            await message.edit_text(text, reply_markup=_home_keyboard())
        else:
            await message.answer(text, reply_markup=_home_keyboard())

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

    @router.message(Command("quran_text"))
    async def quran_text_command(message):
        await show_quran_landing(message)

    @router.message(Command("adhkar"))
    async def adhkar_command(message):
        await show_adhkar_landing(message)

    @router.message(Command("dua"))
    async def dua_command(message):
        await show_dua_landing(message)

    @router.message(Command("hijri"))
    async def hijri_command(message):
        await show_hijri(message)

    @router.message(Command("qibla"))
    async def qibla_command(message):
        raw_text = message.text or ""
        city = raw_text.partition(" ")[2]
        await message.answer(_qibla_text(city), reply_markup=_home_keyboard())

    @router.message(Command("ramadan"))
    async def ramadan_command(message):
        await show_ramadan(message)

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

    @router.callback_query(F.data == "quran_text:home")
    async def quran_text_home_callback(callback):
        if callback.message:
            await show_quran_landing(callback.message, edit=True)
        await callback.answer()

    @router.callback_query(F.data == "hijri:today")
    async def hijri_callback(callback):
        if callback.message:
            await show_hijri(callback.message, edit=True)
        await callback.answer()

    @router.callback_query(F.data == "qibla:help")
    async def qibla_help_callback(callback):
        if callback.message:
            await callback.message.edit_text(
                _qibla_help_text(), reply_markup=_home_keyboard()
            )
        await callback.answer()

    @router.callback_query(F.data == "ramadan:today")
    async def ramadan_callback(callback):
        if callback.message:
            await show_ramadan(callback.message, edit=True)
        await callback.answer()

    @router.callback_query(F.data.startswith("adhkar:"))
    async def adhkar_callback(callback):
        parsed = _parse_adhkar_callback(callback.data or "")
        if parsed is None or callback.message is None:
            await callback.answer("طلب غير صالح", show_alert=True)
            return
        kind, category, index = parsed
        if kind == "home":
            await show_adhkar_landing(callback.message, edit=True)
            await callback.answer()
            return
        if kind == "category":
            from bot.data.adhkar import ADHKAR_CATEGORIES

            keyboard = _adhkar_items_keyboard(category)
            if keyboard is None:
                await callback.answer("فئة غير صالحة", show_alert=True)
                return
            await callback.message.edit_text(
                f"📿 **{ADHKAR_CATEGORIES[category]}:**", reply_markup=keyboard
            )
            await callback.answer()
            return
        detail = _adhkar_item_detail(category, index or 0)
        if detail is None:
            await callback.answer("ذكر غير صالح", show_alert=True)
            return
        text, keyboard = detail
        await callback.message.edit_text(text, reply_markup=keyboard)
        await callback.answer()

    @router.callback_query(F.data.startswith("dua:"))
    async def dua_callback(callback):
        category = _parse_dua_callback(callback.data or "")
        if category is None or callback.message is None:
            await callback.answer("طلب غير صالح", show_alert=True)
            return
        if not category:
            await show_dua_landing(callback.message, edit=True)
            await callback.answer()
            return
        text = _dua_detail(category)
        if text is None:
            await callback.answer("دعاء غير صالح", show_alert=True)
            return
        from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="🔙 الأدعية", callback_data="dua:home")],
                [
                    InlineKeyboardButton(
                        text="⌂ الرئيسية", callback_data="back_to_start"
                    )
                ],
            ]
        )
        await callback.message.edit_text(text, reply_markup=keyboard)
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

    @router.callback_query(F.data.startswith("qts:"))
    async def quran_text_callback(callback):
        from bot.data.quran_data import AYAH_COUNTS, get_ayah_text, get_tafsir
        from bot.data.surahs import SURAHS

        parsed = _parse_qts_callback(callback.data or "")
        if parsed is None or callback.message is None:
            await callback.answer("طلب غير صالح", show_alert=True)
            return
        surah, page, show_tafsir = parsed
        total = AYAH_COUNTS.get(surah, 0)
        total_pages = (total + 9) // 10
        if total == 0 or page > total_pages:
            await callback.answer("سورة أو صفحة غير صالحة", show_alert=True)
            return
        name = SURAHS.get(surah, "")
        if page == 0:
            await callback.message.edit_text(
                f"📖 **سورة {name}**\n───\n"
                f"• رقم السورة: {surah}\n• عدد الآيات: {total}\n\n"
                "اختر من القائمة:",
                reply_markup=_quran_info_keyboard(surah),
            )
            await callback.answer()
            return

        start = (page - 1) * 10 + 1
        end = min(start + 9, total)
        lines = []
        for ayah in range(start, end + 1):
            text = await get_ayah_text(surah, ayah)
            if text:
                lines.append(f"**{ayah}** - {text}")
                if show_tafsir:
                    tafsir = await get_tafsir(surah, ayah)
                    if tafsir:
                        lines.append(f"  _{tafsir}_\n")
        content = f"📖 **{name}** - صفحة {page}\n───\n" + "\n".join(lines)
        await callback.message.edit_text(
            content[:4000],
            reply_markup=_quran_page_keyboard(surah, page, total_pages, show_tafsir),
        )
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
