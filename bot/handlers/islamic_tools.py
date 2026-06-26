import json
import math
import os
import random as _random
from collections import defaultdict
from datetime import date, timedelta

from bot.data.duas import DUA_CATEGORIES, DUA_CATEGORY_KEYS, ARABIC_MONTHS
from bot.data.sources import QURANIC_RECITERS
from bot.data.surahs import SURAHS, SURAH_INFO
from bot.data.glossary import GLOSSARY, GLOSSARY_KEYS
from bot.data.zakat import ZAKAT_GUIDE, ZAKAT_CATEGORIES, calculate_zakat, get_nisab_gold, get_nisab_silver, RAMADAN_DUAS
from bot.decorators import safe_handler

_usage_counts: dict = defaultdict(int)
_USAGE_FILE = os.path.join(os.path.dirname(__file__), "..", "..", "data", "usage_counts.json")
_LOCALES_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "locales")
_LOCALES_CACHE: dict = {}

try:
    with open(_USAGE_FILE, encoding="utf-8") as _f:
        _loaded = json.load(_f)
        for _k, _v in _loaded.items():
            _usage_counts[_k] = _v
except (FileNotFoundError, json.JSONDecodeError):
    pass


def _load_locale(lang: str) -> dict:
    if lang in _LOCALES_CACHE:
        return _LOCALES_CACHE[lang]
    path = os.path.join(_LOCALES_DIR, f"{lang}.json")
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
            _LOCALES_CACHE[lang] = data
            return data
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _track_usage(cmd: str) -> None:
    _usage_counts[cmd] += 1
    try:
        with open(_USAGE_FILE, "w", encoding="utf-8") as _f:
            json.dump(dict(_usage_counts), _f, ensure_ascii=False)
    except (OSError, PermissionError):
        pass


EPOCH = date(622, 7, 16)

KAABA_LAT = 21.4225
KAABA_LON = 39.8262


def _to_hijri(d: date):
    days = (d - EPOCH).days
    if days < 0:
        return None
    year = days // 354 + 1
    month = (days % 354) // 29
    day = (days % 29) + 1
    return day, month, year


def _qibla_direction(lat: float, lon: float) -> float:
    lat1, lon1 = math.radians(lat), math.radians(lon)
    lat2, lon2 = math.radians(KAABA_LAT), math.radians(KAABA_LON)
    dlon = lon2 - lon1
    x = math.sin(dlon) * math.cos(lat2)
    y = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(dlon)
    bearing = math.degrees(math.atan2(x, y))
    return (bearing + 360) % 360


def _compass(degrees: float) -> str:
    directions = [
        (0, "N"), (22.5, "NNE"), (45, "NE"), (67.5, "ENE"),
        (90, "E"), (112.5, "ESE"), (135, "SE"), (157.5, "SSE"),
        (180, "S"), (202.5, "SSW"), (225, "SW"), (247.5, "WSW"),
        (270, "W"), (292.5, "WNW"), (315, "NW"), (337.5, "NNW"),
    ]
    for angle, label in directions:
        if degrees < angle + 11.25:
            return label
    return "N"


def register(app, deps) -> None:
    from pyrogram import filters
    from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

    settings = deps.settings

    @app.on_message(filters.command("hijri"))
    @safe_handler()
    async def hijri_cmd(client, message):
        _track_usage("hijri")
        today = date.today()
        h = _to_hijri(today)
        if not h:
            await message.reply_text("❌ تعذر حساب التاريخ الهجري")
            return
        day, month, year = h
        text = (
            f"📅 **التاريخ الهجري**\n\n"
            f"اليوم: {today.strftime('%A')}\n"
            f"ميلادي: {today.strftime('%d %B %Y')}\n"
            f"هجري: {day} {ARABIC_MONTHS[month]} {year} هـ\n"
        )
        await message.reply_text(text)

    @app.on_message(filters.command("qibla"))
    @safe_handler()
    async def qibla_cmd(client, message):
        from bot.prayer.calculator import get_city_coords, search_cities

        args = message.command[1:]
        if not args:
            await message.reply_text("❌ استخدم: `/qibla [اسم المدينة]`\nمثال: `/qibla الرياض`")
            return
        query = " ".join(args)
        coords = get_city_coords(query)

        if coords is None:
            results = search_cities(query)
            if results:
                names = "\n".join(f"• {n}" for n in results[:5])
                await message.reply_text(
                    f"⚠️ لم أجد '{query}' بالتحديد. هل تقصد:\n{names}\n\n"
                    f"استخدم `/qibla [الاسم الدقيق]`"
                )
            else:
                await message.reply_text(f"❌ لم أجد مدينة '{query}'")
            return

        lat, lon = coords
        bearing = _qibla_direction(lat, lon)
        direction = _compass(bearing)

        # distance to Kaaba (great-circle)
        dlat = math.radians(KAABA_LAT - lat)
        dlon = math.radians(KAABA_LON - lon)
        a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat)) * math.cos(math.radians(KAABA_LAT)) * math.sin(dlon / 2) ** 2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        dist_km = 6371 * c

        text = (
            f"🕋 **اتجاه القبلة**\n\n"
            f"📍 **المدينة:** {query}\n"
            f"🧭 **الاتجاه:** {bearing:.1f}° ({direction})\n"
            f"📏 **المسافة:** {dist_km:.0f} كم عن مكة\n\n"
        )
        await message.reply_text(text)

    @app.on_message(filters.command("dua"))
    @safe_handler()
    async def dua_cmd(client, message):
        args = message.command[1:]
        if args:
            cat = " ".join(args)
            if cat in DUA_CATEGORIES:
                info = DUA_CATEGORIES[cat]
                text = (
                    f"🤲 **{cat}**\n\n"
                    f"_{info['dua']}_\n\n"
                    f"📚 {info['source']}"
                )
                await message.reply_text(text)
                return
            close = [k for k in DUA_CATEGORY_KEYS if cat in k]
            if close:
                await message.reply_text(
                    f"⚠️ لم أجد '{cat}'. هل تقصد:\n" + "\n".join(f"• /dua {k}" for k in close[:5])
                )
                return
            await message.reply_text("❌ تصنيف غير موجود. استخدم `/dua` لعرض القائمة")
            return

        lines = "\n".join(f"• /dua {k}" for k in DUA_CATEGORY_KEYS)
        await message.reply_text(f"🤲 **الأدعية الجامعة**\n\nاختر تصنيفاً:\n\n{lines}")

    @app.on_message(filters.group & filters.command("tasbih"))
    @safe_handler()
    async def tasbih_cmd(client, message):
        _track_usage("tasbih")
        _TASBIHAT = {"سبحان الله": 0, "الحمد لله": 0, "لا إله إلا الله": 0, "الله أكبر": 0, "أستغفر الله": 0}
        args = message.command[1:]
        if args and args[0] == "help":
            await message.reply_text(
                "🔄 **مسبحة إلكترونية**\n\n**الاستخدام في المجموعة:**\n"
                "• `/tasbih` - عرض المسبحة\n• `/tasbih سبحان الله` - زيادة الذكر\n"
                "• `/tasbih reset` - تصفير العدّ\n• `/tasbih help` - هذه التعليمات"
            )
            return
        from bot.db.repositories.group_settings import GroupSettingsRepo
        repo = deps.group_repo
        chat_id = message.chat.id
        settings = await repo.get(chat_id)
        state_key = "tasbih_counts"
        counts = {}
        if settings and state_key in settings.__dict__:
            counts = settings.__dict__[state_key]
        if args and args[0] in _TASBIHAT:
            dhikr = args[0]
            counts[dhikr] = counts.get(dhikr, 0) + 1
            total = sum(counts.values())
            text = f"🔄 **{dhikr}** — {counts[dhikr]}\nالمجموع: {total}"
            if settings:
                setattr(settings, state_key, counts)
                await repo.upsert(settings)
            await message.reply_text(text)
            return
        if args and args[0] == "reset":
            counts = {}
            if settings:
                setattr(settings, state_key, counts)
                await repo.upsert(settings)
            await message.reply_text("✅ تم تصفير المسبحة")
            return
        lines = "\n".join(f"• {k}: {counts.get(k, 0)}" for k in _TASBIHAT)
        total = sum(counts.values())
        await message.reply_text(
            f"🔄 **المسبحة**\n\n{lines}\n\n**المجموع:** {total}\n\n"
            f"**للزيادة:** `/tasbih سبحان الله`\n**للتصفير:** `/tasbih reset`"
        )

    @app.on_message(filters.command("zakat"))
    @safe_handler()
    async def zakat_cmd(client, message):
        _track_usage("zakat")
        args = message.command[1:]
        if not args:
            lines = "\n".join(f"• /zakat {k}" for k in ZAKAT_CATEGORIES)
            await message.reply_text(
                f"🧮 **حاسبة الزكاة**\n\nاختر نوع الزكاة:\n{lines}\n\n"
                f"أو استخدم:\n`/zakat حساب [المبلغ]`\n`/zakat ذهب [سعر الجرام] [الوزن]`"
            )
            return
        if args[0] == "حساب" and len(args) > 1:
            try:
                amount = float(args[1].replace(",", ""))
                if amount <= 0: raise ValueError
                result = calculate_zakat(amount)
                await message.reply_text(
                    f"🧮 **حاسبة الزكاة**\n\n💰 **المبلغ:** {amount:,.0f}\n"
                    f"📊 **النسبة:** 2.5%\n✅ **الزكاة الواجبة:** {result['zakat_due']:,.2f}\n\n"
                    f"_نصاب الذهب: ≈{get_nisab_gold(300):,.0f} (عند 300/جم)_\n_نصاب الفضة: ≈{get_nisab_silver(5):,.0f} (عند 5/جم)_"
                )
                return
            except ValueError:
                await message.reply_text("❌ مبلغ غير صحيح. مثال: `/zakat حساب 10000`")
                return
        cat = " ".join(args)
        if cat in ZAKAT_GUIDE:
            info = ZAKAT_GUIDE[cat]
            await message.reply_text(
                f"🧮 **زكاة {cat}**\n\n**الشرط:** {info['condition']}\n"
                f"**المقدار:** {info['rate']}\n\n**الدليل:**\n{info['evidence']}"
            )
        else:
            close = [k for k in ZAKAT_CATEGORIES if cat in k]
            if close:
                await message.reply_text(f"⚠️ هل تقصد:\n" + "\n".join(f"• /zakat {k}" for k in close[:5]))
            else:
                await message.reply_text("❌ تصنيف غير موجود. استخدم `/zakat`")

    @app.on_message(filters.command("ramadan"))
    @safe_handler()
    async def ramadan_cmd(client, message):
        _track_usage("ramadan")
        today = date.today()
        h = _to_hijri(today)
        ramadan_info = ""
        if h:
            _, m, y = h
            if m == 9:
                ramadan_info = f"✅ **اليوم {h[0]} من رمضان {y} هـ** 🌙\n"
            else:
                days = ((9 - m + 12) % 12) * 30
                ramadan_info = f"📅 رمضان {y + (1 if m > 9 else 0)} هـ بعد ~{days} يوم\n"
        dua_lines = "\n\n".join(f"**{d['name']}:**\n_{d['dua']}_\n📚 {d['source']}" for d in RAMADAN_DUAS)
        await message.reply_text(
            f"🌙 **رمضان مبارك**\n\n{ramadan_info}"
            f"**مواقيت:**\n• السحور: قبل الفجر بـ 10-20 د\n• الإمساك: أذان الفجر\n"
            f"• الإفطار: أذان المغرب\n\n**أدعية رمضانية:**\n\n{dua_lines}"
        )

    @app.on_message(filters.command("memorize"))
    @safe_handler()
    async def memorize_cmd(client, message):
        _track_usage("memorize")
        import random as _random
        args = message.command[1:]
        if not args:
            num = _random.randint(1, 114)
            await message.reply_text(
                f"📖 **تسميع القرآن**\n\nاكتب `/memorize {num}` لاختبار سورة\n"
                f"اكتب `/memorize random` لسورة عشوائية\nاكتب `/memorize help` للمساعدة\n"
                f"**السور:** 1-114"
            )
            return
        if args[0] == "help":
            await message.reply_text(
                "📖 **المساعدة:**\n• `/memorize` - عرض التعليمات\n"
                "• `/memorize [رقم]` - اختبار سورة\n• `/memorize random` - سورة عشوائية\n"
                "• `/memorize list` - قائمة السور"
            )
            return
        if args[0] == "list":
            page = 0
            if len(args) > 1:
                try: page = max(0, int(args[1]) - 1)
                except: pass
            items_per_page = 30
            items = list(SURAHS.items())
            total_pages = (len(items) + items_per_page - 1) // items_per_page
            if page >= total_pages: page = total_pages - 1
            start = page * items_per_page
            end = min(start + items_per_page, len(items))
            lines = "\n".join(f"{n}. {name}" for n, name in items[start:end])
            nav = f"الصفحة {page + 1}/{total_pages}"
            if page > 0: nav += f"\n`/memorize list {page}` للسابقة"
            if page < total_pages - 1: nav += f"\n`/memorize list {page + 2}` للتالية"
            await message.reply_text(f"📚 **السور ({start + 1}-{end}):**\n{lines}\n\n{nav}")
            return
        if args[0] == "random":
            num = _random.randint(1, 114)
        else:
            try:
                num = int(args[0])
                if not 1 <= num <= 114: raise ValueError
            except ValueError:
                await message.reply_text("❌ رقم 1-114"); return
        name = SURAHS.get(num, f"{num}")
        await message.reply_text(
            f"📖 **تسميع سورة {name} ({num})**\n\n"
            f"🔹 اقرأ السورة من المصحف\n🔹 استمع: `/quran {num}`\n🔹 بث في المجموعة: `/quran {num}`"
        )

    @app.on_message(filters.command("stats"))
    @safe_handler()
    async def stats_cmd(client, message):
        _track_usage("stats")
        total = sum(_usage_counts.values())
        if total == 0:
            await message.reply_text("📊 **إحصائيات البوت**\n\nلم يتم تسجيل استخدام بعد.\n_إحصاءات الاستخدام في الذاكرة._")
            return
        sorted_cmds = sorted(_usage_counts.items(), key=lambda x: -x[1])
        lines = "\n".join(f"• `/{cmd}`: {count}" for cmd, count in sorted_cmds[:15])
        await message.reply_text(
            f"📊 **إحصائيات البوت**\n\n**الإجمالي:** {total} أمر\n\n**الأكثر استخداماً:**\n{lines}"
        )

    @app.on_message(filters.command("jummah"))
    @safe_handler()
    async def jummah_cmd(client, message):
        _track_usage("jummah")
        from datetime import datetime as _dt
        today = _dt.now()
        friday = 4  # Monday=0, Friday=4
        days_ahead = (friday - today.weekday()) % 7
        next_friday = today.day + days_ahead
        hijri = _to_hijri(today)
        h_str = ""
        if hijri:
            h_str = f"{hijri[0]} {ARABIC_MONTHS[hijri[1]]} {hijri[2]} هـ"
        await message.reply_text(
            f"📅 **الجمعة**\n\n"
            f"اليوم: {today.strftime('%A')}\n"
            f"{h_str}\n"
            f"الجمعة القادمة: بعد {days_ahead} يوم\n\n"
            "**سنن الجمعة:**\n"
            "• الاغتسال والتطيب\n• قراءة سورة الكهف\n"
            "• الإكثار من الصلاة على النبي ﷺ\n"
            "• التبكير إلى المسجد\n"
            "• الدعاء في ساعة الإجابة"
        )

    @app.on_message(filters.command("commands"))
    @safe_handler()
    async def all_commands_cmd(client, message):
        _track_usage("commands")
        text = (
            "📋 **جميع أوامر البوت الإسلامي الموحد**\n\n"
            "**📖 القرآن:**\n/quran - قائمة القرآن\n/quran_text - نص + تفسير\n/quran_search [كلمة] - بحث\n"
            "/quran [رقم] - بث سورة (مجموعات)\n/stop - إيقاف البث\n/radio - راديو القرآن\n\n"
            "**📚 الحديث:**\n/hadith - مكتبة الحديث (6 كتب)\n/hadith [كتاب] [رقم] - حديث محدد\n\n"
            "**🤲 الأذكار والأدعية:**\n/adhkar - الأذكار (24 تصنيفاً)\n/dua - الأدعية الجامعة (20)\n"
            "/tasbih - مسبحة إلكترونية\n/names - أسماء الله الحسنى\n\n"
            "**🧮 الزكاة:**\n/zakat - معلومات الزكاة\n/zakat حساب [المبلغ] - حساب الزكاة\n\n"
            "**🕌 الصلاة والقبلة:**\n/azan_setup - إعداد المدينة\n/azan_times - أوقات الصلاة\n"
            "/azan_next - الصلاة التالية\n/prayer [مدينة] - أوقات أي مدينة\n"
            "/qibla [مدينة] - اتجاه القبلة\n/hijri - التاريخ الهجري\n"
            "/ramadan - أدعية ومواقيت رمضان\n\n"
            "**📖 تسميع:**\n/memorize [رقم] - اختبار حفظ سورة\n/memorize list - قائمة السور\n\n"
            "**📅 المناسبات:**\n/calendar - المناسبات الإسلامية\n/jummah - سنن الجمعة\n\n"
            "**📥 التحميل:**\n/download - روابط MP3 للقرآن (9 قرّاء)\n/download [القارئ] [رقم] - سورة محددة\n\n"
            "**📖 معلومات السور:**\n/surah [رقم] - معلومات السورة (آيات + نوع)\n\n"
            "**🔍 بحث:**\n/search [كلمة] - بحث في المدن والسور والأدعية والمصطلحات\n\n"
            "**📊 أخرى:**\n/stats - إحصائيات البوت\n/daily - جرعتك اليومية\n"
            "/language - تغيير اللغة\n/help - التعليمات\n/start - القائمة الرئيسية"
        )
        await message.reply_text(text)

    @app.on_message(filters.command("daily"))
    @safe_handler()
    async def daily_cmd(client, message):
        _track_usage("daily")
        today = date.today()
        h = _to_hijri(today)
        h_str = ""
        if h:
            h_str = f"{h[0]} {ARABIC_MONTHS[h[1]]} {h[2]} هـ"
        seed = today.toordinal()
        _rng = _random.Random(seed)
        surah_num = _rng.randint(1, 114)
        surah_name = SURAHS.get(surah_num, "")
        duas_list = list(DUA_CATEGORIES.values())
        dua_item = _rng.choice(duas_list)
        dua_name = list(DUA_CATEGORIES.keys())[list(DUA_CATEGORIES.values()).index(dua_item)]
        await message.reply_text(
            f"💎 **جرعتك اليومية**\n"
            f"📅 {today.strftime('%A, %d %B %Y')}\n{h_str}\n\n"
            f"**📖 سورة اليوم:** {surah_num} - {surah_name}\n"
            f"استمع: `/quran {surah_num}` | اقرأ: `/quran_text {surah_num}`\n\n"
            f"**🤲 دعاء اليوم:** {dua_name}\n_{dua_item['dua']}_\n📚 {dua_item['source']}\n\n"
            f"_تتغير الجرعة اليومية تلقائياً كل يوم_"
        )

    @app.on_message(filters.command("monthly"))
    @safe_handler()
    async def monthly_cmd(client, message):
        _track_usage("monthly")
        args = message.command[1:]
        city_name = " ".join(args) if args else None
        if not city_name and message.from_user:
            user_repo = deps.user_repo
            user_id = message.from_user.id
            user_settings = await user_repo.get(user_id)
            if user_settings:
                city_name = user_settings.city
        if not city_name:
            await message.reply_text("❌ استخدم: `/monthly [اسم المدينة]`\nأو قم بإعداد مدينتك عبر `/azan_setup`")
            return
        coords = CityCoordinates.get_city_coords(city_name)
        if not coords:
            await message.reply_text(f"❌ المدينة '{city_name}' غير موجودة")
            return
        today = datetime.now()
        year, month = today.year, today.month
        method = coords.get("method", "mwl")
        calc = PrayerTimeCalculator(coords["lat"], coords["lng"], coords["tz"], method, dst=coords.get("dst",False), city_name=city_name)
        lines = [f"📅 **جدول {city_name} - {month}/{year}**\n", "─────"]
        first_day = datetime(year, month, 1)
        if month == 12:
            last_day = datetime(year+1, 1, 1) - timedelta(days=1)
        else:
            last_day = datetime(year, month+1, 1) - timedelta(days=1)
        for d in range(1, last_day.day + 1, 3):
            dates_to_calc = [datetime(year, month, min(d+i, last_day.day)) for i in range(3)]
            row = ""
            for dt in dates_to_calc:
                times = calc.calculate_times(dt)
                row += f"**{dt.day}:** F{times.get('fajr','?')} M{times.get('maghrib','?')} "
            lines.append(row)
        lines.append("─────\n_F: فجر, M: مغرب_")
        await message.reply_text("\n".join(lines))

    @app.on_message(filters.command("prayer"))
    @safe_handler()
    async def prayer_cmd(client, message):
        _track_usage("prayer")
        from bot.prayer.calculator import CityCoordinates, PrayerTimeCalculator
        from datetime import datetime
        args = message.command[1:]
        if not args:
            await message.reply_text("❌ استخدم: `/prayer [اسم المدينة]`\nمثال: `/prayer مكة`\nأو: `/prayer list` لقائمة المدن")
            return
        if args[0] == "list":
            cities = list(CityCoordinates.CITIES.keys())
            lines = "\n".join(f"• {c}" for c in cities[:30])
            await message.reply_text(f"📌 **المدن المتاحة ({len(cities)}):**\n{lines}\n\n_استخدم /prayer [اسم المدينة]_")
            return
        city = " ".join(args)
        coords = CityCoordinates.get_city_coords(city)
        if not coords:
            results = CityCoordinates.search_cities(city)
            if results:
                await message.reply_text(f"⚠️ هل تقصد:\n" + "\n".join(f"• {r}" for r in results[:5]))
            else:
                await message.reply_text(f"❌ المدينة '{city}' غير موجودة")
            return
        calc = PrayerTimeCalculator(coords["lat"], coords["lng"], coords["tz"], coords.get("method","mwl"), dst=coords.get("dst",False), city_name=city)
        times = calc.calculate_times(datetime.now())
        text = f"🕌 **أوقات الصلاة**\n📍 {city}, {coords.get('country','')}\n📐 {calc.get_method_name()}\n─────\n"
        for p in ["imsak","fajr","sunrise","dhuhr","asr","sunset","maghrib","isha","midnight"]:
            if p in times:
                name = PrayerTimeCalculator.PRAYER_NAMES.get(p, p)
                text += f"{name} • {times[p]}\n"
        await message.reply_text(text)

    @app.on_message(filters.command("language"))
    @safe_handler()
    async def language_cmd(client, message):
        _track_usage("language")
        await message.reply_text(
            "🌐 **تغيير اللغة**\n\nاختر اللغة:\n\n• العربية - `/lang ar`\n"
            "• English - `/lang en`\n• اردو - `/lang ur`\n• Bahasa Indonesia - `/lang id`"
        )

    @app.on_message(filters.command("lang"))
    @safe_handler()
    async def lang_set_cmd(client, message):
        _track_usage("lang")
        args = message.command[1:]
        if not args:
            await message.reply_text("❌ اختر: /lang ar, /lang en, /lang ur, /lang id")
            return
        lang = args[0].lower()
        supported = {"ar": "العربية", "en": "English", "ur": "اردو", "id": "Bahasa Indonesia"}
        if lang not in supported:
            await message.reply_text(f"❌ اللغة '{lang}' غير مدعومة. اللغات: ar, en, ur, id")
            return
        locale = _load_locale(lang) if lang != "ar" else {}
        msg = f"✅ تم اختيار {supported[lang]}"
        if message.from_user and message.chat.type == "private":
            user_repo = deps.user_repo
            user_id = message.from_user.id
            settings = await user_repo.get(user_id)
            if settings:
                setattr(settings, "language", lang)
                await user_repo.upsert(settings)
                msg += " (تم الحفظ)"
        await message.reply_text(msg)

    @app.on_message(filters.command("download"))
    @safe_handler()
    async def download_cmd(client, message):
        _track_usage("download")
        args = message.command[1:]
        if not args:
            await message.reply_text(
                "📥 **تحميل القرآن MP3**\n\nاختر القارئ:\n" +
                "\n".join(f"• /download {k} - {v['name']}" for k, v in list(QURANIC_RECITERS.items())[:5])
            )
            return
        r_key = args[0]
        reciter = QURANIC_RECITERS.get(r_key)
        if not reciter:
            close = [k for k in QURANIC_RECITERS if r_key in k]
            if close:
                await message.reply_text("⚠️ هل تقصد: " + ", ".join(f"/download {k}" for k in close[:5]))
            else:
                await message.reply_text(f"❌ القارئ '{r_key}' غير موجود")
            return
        if len(args) > 1:
            try:
                s = int(args[1])
                if not 1 <= s <= 114: raise ValueError
                name = SURAHS.get(s, str(s))
                url = f"{reciter['stream_url']}{s:03d}.mp3"
                await message.reply_text(f"📥 **تحميل {name} ({s})**\n🎙️ {reciter['name']}\n\n📎 {url}")
                return
            except ValueError:
                await message.reply_text("❌ رقم السورة 1-114")
                return
        top_surahs = list(reciter.get('available_surahs', list(range(1,115)))[:10])
        info = "\n".join(f"/download {r_key} {n} - {SURAHS.get(n)}" for n in top_surahs)
        await message.reply_text(f"🎙️ **{reciter['name']}**\n{info}\n\n_جميع السور 1-114 متاحة_")

    @app.on_message(filters.command("surah"))
    @safe_handler()
    async def surah_cmd(client, message):
        _track_usage("surah")
        args = message.command[1:]
        if not args:
            await message.reply_text(
                "📖 **معلومات السور**\n\n"
                "استخدم: `/surah [رقم السورة]`\n"
                "مثال: `/surah 1` لسورة الفاتحة\n"
                "أو: `/surah list` لقائمة السور"
            )
            return
        if args[0] == "list":
            lines = "\n".join(f"{n}. {name}" for n, name in list(SURAHS.items())[:20])
            await message.reply_text(f"📚 **السور (1-20):**\n{lines}\n\n_استخدم /surah [رقم]_")
            return
        try:
            n = int(args[0])
            if not 1 <= n <= 114: raise ValueError
        except ValueError:
            await message.reply_text("❌ رقم السورة 1-114")
            return
        name = SURAHS.get(n, "")
        info = SURAH_INFO.get(n, {})
        ayas = info.get("ayas", "?")
        rtype = info.get("type", "?")
        meaning = info.get("meaning", "")
        await message.reply_text(
            f"📖 **{n} - {name}**\n\n"
            f"• عدد الآيات: {ayas}\n"
            f"• النوع: {rtype}\n"
            f"• معنى الاسم: {meaning}\n\n"
            f"🔊 للاستماع: /quran {n}\n"
            f"📥 للتحميل: /download abdul_basit {n}"
        )

    @app.on_message(filters.command("glossary"))
    @safe_handler()
    async def glossary_cmd(client, message):
        _track_usage("glossary")
        args = message.command[1:]
        if not args:
            lines = "\n".join(f"• {k}" for k in GLOSSARY_KEYS[:30])
            await message.reply_text(
                f"📖 **القاموس الإسلامي**\n\n"
                f"اكتب `/glossary [المصطلح]`\nمثال: `/glossary الصلاة`\n\n"
                f"**المصطلحات:**\n{lines}\n\n"
                f"_يوجد {len(GLOSSARY_KEYS)} مصطلحاً_"
            )
            return
        term = " ".join(args)
        if term in GLOSSARY:
            await message.reply_text(f"📖 **{term}**\n\n{GLOSSARY[term]}")
            return
        close = [k for k in GLOSSARY_KEYS if term in k]
        if close:
            await message.reply_text(f"⚠️ هل تقصد:\n" + "\n".join(f"• /glossary {k}" for k in close[:5]))
        else:
            await message.reply_text(f"❌ مصطلح '{term}' غير موجود")

    @app.on_message(filters.command("search"))
    @safe_handler()
    async def search_cmd(client, message):
        _track_usage("search")
        args = message.command[1:]
        if not args:
            await message.reply_text("🔍 **بحث شامل**\n\nابحث في المدن والسور والأدعية والمصطلحات.\nمثال: `/search مكة`")
            return
        query = " ".join(args).lower()
        results = []
        from bot.prayer.calculator import CityCoordinates
        for city in CityCoordinates.CITIES:
            if query in city.lower():
                results.append(f"📍 مدينة: {city} (/prayer {city})")
        for num, name in SURAHS.items():
            if query in name.lower() or query in str(num):
                info = SURAH_INFO.get(num, {})
                results.append(f"📖 سورة {num} - {name} ({info.get('ayas','?')} آية) /surah {num}")
        for key in DUA_CATEGORY_KEYS:
            if query in key.lower():
                results.append(f"🤲 دعاء: {key} (/dua {key})")
        for key in GLOSSARY_KEYS:
            if query in key.lower():
                results.append(f"📖 مصطلح: {key} (/glossary {key})")
        if not results:
            await message.reply_text(f"🔍 لا توجد نتائج لـ '{query}'")
            return
        lines = "\n".join(results[:15])
        more = f"\n...و{len(results)-15} نتيجة أخرى" if len(results) > 15 else ""
        await message.reply_text(f"🔍 **نتائج البحث عن '{query}'** ({len(results)}):\n\n{lines}{more}")
