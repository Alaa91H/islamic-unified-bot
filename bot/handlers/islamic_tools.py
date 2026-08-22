import contextlib
import json
import os
from collections import defaultdict
from datetime import date, datetime, timedelta

from bot.decorators import safe_handler
from bot.islamic_calendar import to_hijri
from bot.islamic_content import daily_selection, ramadan_status
from bot.qibla import calculate_qibla
from bot.time_utils import city_local_time, utc_now

_usage_counts: dict = defaultdict(int)
_USAGE_FILE = os.path.join(
    os.path.dirname(__file__), "..", "..", "data", "usage_counts.json"
)
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


def _to_hijri(d: date):
    """توافق مؤقت مع استيرادات المنطق السابقة داخل معالج Pyrogram."""
    return to_hijri(d)


def register(app, deps) -> None:
    from pyrogram import filters

    @app.on_message(filters.command("hijri"))
    @safe_handler()
    async def hijri_cmd(client, message):
        from bot.data.duas import ARABIC_MONTHS

        _track_usage("hijri")
        today = utc_now().date()
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
            await message.reply_text(
                "❌ استخدم: `/qibla [اسم المدينة]`\nمثال: `/qibla الرياض`"
            )
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
        result = calculate_qibla(lat, lon)

        text = (
            f"🕋 **اتجاه القبلة**\n\n"
            f"📍 **المدينة:** {query}\n"
            f"🧭 **الاتجاه:** {result.bearing_degrees:.1f}° ({result.compass})\n"
            f"📏 **المسافة:** {result.distance_km:.0f} كم عن مكة\n\n"
        )
        await message.reply_text(text)

    @app.on_message(filters.command("dua"))
    @safe_handler()
    async def dua_cmd(client, message):
        from bot.data.duas import DUA_CATEGORIES, DUA_CATEGORY_KEYS

        args = message.command[1:]
        if args:
            cat = " ".join(args)
            if cat in DUA_CATEGORIES:
                info = DUA_CATEGORIES[cat]
                text = f"🤲 **{cat}**\n\n_{info['dua']}_\n\n📚 {info['source']}"
                await message.reply_text(text)
                return
            close = [k for k in DUA_CATEGORY_KEYS if cat in k]
            if close:
                await message.reply_text(
                    f"⚠️ لم أجد '{cat}'. هل تقصد:\n"
                    + "\n".join(f"• /dua {k}" for k in close[:5])
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
        _TASBIHAT = {
            "سبحان الله": 0,
            "الحمد لله": 0,
            "لا إله إلا الله": 0,
            "الله أكبر": 0,
            "أستغفر الله": 0,
        }
        args = message.command[1:]
        if args and args[0] == "help":
            await message.reply_text(
                "🔄 **مسبحة إلكترونية**\n\n**الاستخدام في المجموعة:**\n"
                "• `/tasbih` - عرض المسبحة\n• `/tasbih سبحان الله` - زيادة الذكر\n"
                "• `/tasbih reset` - تصفير العدّ\n• `/tasbih help` - هذه التعليمات"
            )
            return

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
        from bot.data.zakat import (
            ZAKAT_CATEGORIES,
            ZAKAT_GUIDE,
            calculate_zakat,
            get_nisab_gold,
            get_nisab_silver,
        )

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
                if amount <= 0:
                    raise ValueError
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
                await message.reply_text(
                    "⚠️ هل تقصد:\n" + "\n".join(f"• /zakat {k}" for k in close[:5])
                )
            else:
                await message.reply_text("❌ تصنيف غير موجود. استخدم `/zakat`")

    @app.on_message(filters.command("ramadan"))
    @safe_handler()
    async def ramadan_cmd(client, message):
        from bot.data.zakat import RAMADAN_DUAS

        _track_usage("ramadan")
        today = utc_now().date()
        h = _to_hijri(today)
        ramadan_info = ramadan_status(h)
        dua_lines = "\n\n".join(
            f"**{d['name']}:**\n_{d['dua']}_\n📚 {d['source']}" for d in RAMADAN_DUAS
        )
        await message.reply_text(
            f"🌙 **رمضان مبارك**\n\n{ramadan_info}"
            f"**مواقيت:**\n• السحور: قبل الفجر بـ 10-20 د\n• الإمساك: أذان الفجر\n"
            f"• الإفطار: أذان المغرب\n\n**أدعية رمضانية:**\n\n{dua_lines}"
        )

    @app.on_message(filters.command("memorize"))
    @safe_handler()
    async def memorize_cmd(client, message):
        from bot.data.surahs import SURAHS

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
                with contextlib.suppress(ValueError):
                    page = max(0, int(args[1]) - 1)
            items_per_page = 30
            items = list(SURAHS.items())
            total_pages = (len(items) + items_per_page - 1) // items_per_page
            if page >= total_pages:
                page = total_pages - 1
            start = page * items_per_page
            end = min(start + items_per_page, len(items))
            lines = "\n".join(f"{n}. {name}" for n, name in items[start:end])
            nav = f"الصفحة {page + 1}/{total_pages}"
            if page > 0:
                nav += f"\n`/memorize list {page}` للسابقة"
            if page < total_pages - 1:
                nav += f"\n`/memorize list {page + 2}` للتالية"
            await message.reply_text(
                f"📚 **السور ({start + 1}-{end}):**\n{lines}\n\n{nav}"
            )
            del items
            return
        if args[0] == "random":
            num = _random.randint(1, 114)
        else:
            try:
                num = int(args[0])
                if not 1 <= num <= 114:
                    raise ValueError
            except ValueError:
                await message.reply_text("❌ رقم 1-114")
                return
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
            await message.reply_text(
                "📊 **إحصائيات البوت**\n\nلم يتم تسجيل استخدام بعد.\n_إحصاءات الاستخدام في الذاكرة._"
            )
            return
        sorted_cmds = sorted(_usage_counts.items(), key=lambda x: -x[1])
        lines = "\n".join(f"• `/{cmd}`: {count}" for cmd, count in sorted_cmds[:15])
        await message.reply_text(
            f"📊 **إحصائيات البوت**\n\n**الإجمالي:** {total} أمر\n\n**الأكثر استخداماً:**\n{lines}"
        )

    @app.on_message(filters.command("jummah"))
    @safe_handler()
    async def jummah_cmd(client, message):
        from bot.data.duas import ARABIC_MONTHS

        _track_usage("jummah")
        today = utc_now()
        friday = 4
        days_ahead = (friday - today.weekday()) % 7
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

    @app.on_message(filters.command("calendar"))
    @safe_handler()
    async def calendar_cmd(client, message):
        _track_usage("calendar")
        from bot.data.duas import ARABIC_MONTHS

        today = utc_now().date()
        h = _to_hijri(today)
        h_str = ""
        if h:
            h_str = f"{h[0]} {ARABIC_MONTHS[h[1]]} {h[2]} هـ"
        await message.reply_text(
            f"📅 **التقويم الإسلامي**\n\n"
            f"• التاريخ الهجري: {h_str}\n"
            f"• التاريخ الميلادي: {today.strftime('%Y-%m-%d')}\n\n"
            f"**المناسبات الإسلامية القادمة:**\n"
            f"• رمضان: حسب الرؤية\n"
            f"• الأضحى: 10 ذو الحجة\n"
            f"• الفطر: 1 شوال\n"
            f"• عرفة: 9 ذو الحجة\n"
            f"• المولد النبوي: 12 ربيع الأول\n"
            f"• الإسراء والمعراج: 27 رجب\n"
            f"• منتصف شعبان: 15 شعبان\n\n"
            f"اكتب /hijri لتحديث التاريخ الحالي"
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
        from bot.data.duas import ARABIC_MONTHS, DUA_CATEGORIES
        from bot.data.surahs import SURAHS

        _track_usage("daily")
        today = utc_now().date()
        h = _to_hijri(today)
        h_str = ""
        if h:
            h_str = f"{h[0]} {ARABIC_MONTHS[h[1]]} {h[2]} هـ"
        selection = daily_selection(today, SURAHS, DUA_CATEGORIES)
        await message.reply_text(
            f"💎 **جرعتك اليومية**\n"
            f"📅 {today.strftime('%A, %d %B %Y')}\n{h_str}\n\n"
            f"**📖 سورة اليوم:** {selection.surah_number} - {selection.surah_name}\n"
            f"استمع: `/quran {selection.surah_number}` | اقرأ: `/quran_text {selection.surah_number}`\n\n"
            f"**🤲 دعاء اليوم:** {selection.dua_name}\n_{selection.dua['dua']}_\n📚 {selection.dua['source']}\n\n"
            f"_تتغير الجرعة اليومية تلقائياً كل يوم_"
        )

    @app.on_message(filters.command("monthly"))
    @safe_handler()
    async def monthly_cmd(client, message):
        from bot.prayer.calculator import CityCoordinates, PrayerTimeCalculator

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
            await message.reply_text(
                "❌ استخدم: `/monthly [اسم المدينة]`\nأو قم بإعداد مدينتك عبر `/azan_setup`"
            )
            return
        coords = CityCoordinates.get_city_coords(city_name)
        if not coords:
            await message.reply_text(f"❌ المدينة '{city_name}' غير موجودة")
            return
        local_now = city_local_time(utc_now(), city_name, coords)
        year, month = local_now.year, local_now.month
        method = coords.get("method", "mwl")
        calc = PrayerTimeCalculator(
            coords["lat"],
            coords["lng"],
            coords["tz"],
            method,
            dst=coords.get("dst", False),
            city_name=city_name,
        )
        lines = [f"📅 **جدول {city_name} - {month}/{year}**\n", "─────"]
        if month == 12:
            last_day = datetime(year + 1, 1, 1) - timedelta(days=1)
        else:
            last_day = datetime(year, month + 1, 1) - timedelta(days=1)
        for d in range(1, last_day.day + 1, 3):
            dates_to_calc = [
                datetime(
                    year,
                    month,
                    min(d + i, last_day.day),
                    tzinfo=local_now.tzinfo,
                )
                for i in range(3)
            ]
            row = ""
            for dt in dates_to_calc:
                times = calc.calculate_times(dt)
                row += f"**{dt.day}:** F{times.get('fajr', '?')} M{times.get('maghrib', '?')} "
            lines.append(row)
        lines.append("─────\n_F: فجر, M: مغرب_")
        await message.reply_text("\n".join(lines))

    @app.on_message(filters.command("prayer"))
    @safe_handler()
    async def prayer_cmd(client, message):
        from bot.prayer.calculator import CityCoordinates, PrayerTimeCalculator

        _track_usage("prayer")
        args = message.command[1:]
        if not args:
            await message.reply_text(
                "❌ استخدم: `/prayer [اسم المدينة]`\nمثال: `/prayer مكة`\nأو: `/prayer list` لقائمة المدن"
            )
            return
        if args[0] == "list":
            cities = list(CityCoordinates.CITIES.keys())
            lines = "\n".join(f"• {c}" for c in cities[:30])
            await message.reply_text(
                f"📌 **المدن المتاحة ({len(cities)}):**\n{lines}\n\n_استخدم /prayer [اسم المدينة]_"
            )
            return
        city = " ".join(args)
        coords = CityCoordinates.get_city_coords(city)
        if not coords:
            results = CityCoordinates.search_cities(city)
            if results:
                await message.reply_text(
                    "⚠️ هل تقصد:\n" + "\n".join(f"• {r}" for r in results[:5])
                )
            else:
                await message.reply_text(f"❌ المدينة '{city}' غير موجودة")
            return
        calc = PrayerTimeCalculator(
            coords["lat"],
            coords["lng"],
            coords["tz"],
            coords.get("method", "mwl"),
            dst=coords.get("dst", False),
            city_name=city,
        )
        local_now = city_local_time(utc_now(), city, coords)
        times = calc.calculate_times(local_now)
        text = f"🕌 **أوقات الصلاة**\n📍 {city}, {coords.get('country', '')}\n📐 {calc.get_method_name()}\n─────\n"
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
        supported = {
            "ar": "العربية",
            "en": "English",
            "ur": "اردو",
            "id": "Bahasa Indonesia",
        }
        if lang not in supported:
            await message.reply_text(
                f"❌ اللغة '{lang}' غير مدعومة. اللغات: ar, en, ur, id"
            )
            return
        msg = f"✅ تم اختيار {supported[lang]}"
        if message.from_user and message.chat.type == "private":
            user_repo = deps.user_repo
            user_id = message.from_user.id
            settings = await user_repo.get(user_id)
            if settings:
                settings.language = lang
                await user_repo.upsert(settings)
                msg += " (تم الحفظ)"
        await message.reply_text(msg)

    @app.on_message(filters.command("download"))
    @safe_handler()
    async def download_cmd(client, message):
        from bot.data.sources import QURANIC_RECITERS
        from bot.data.surahs import SURAHS

        _track_usage("download")
        args = message.command[1:]
        if not args:
            await message.reply_text(
                "📥 **تحميل القرآن MP3**\n\nاختر القارئ:\n"
                + "\n".join(
                    f"• /download {k} - {v['name']}"
                    for k, v in list(QURANIC_RECITERS.items())[:5]
                )
            )
            return
        r_key = args[0]
        reciter = QURANIC_RECITERS.get(r_key)
        if not reciter:
            close = [k for k in QURANIC_RECITERS if r_key in k]
            if close:
                await message.reply_text(
                    "⚠️ هل تقصد: " + ", ".join(f"/download {k}" for k in close[:5])
                )
            else:
                await message.reply_text(f"❌ القارئ '{r_key}' غير موجود")
            return
        if len(args) > 1:
            try:
                s = int(args[1])
                if not 1 <= s <= 114:
                    raise ValueError
                name = SURAHS.get(s, str(s))
                url = f"{reciter['stream_url']}{s:03d}.mp3"
                await message.reply_text(
                    f"📥 **تحميل {name} ({s})**\n🎙️ {reciter['name']}\n\n📎 {url}"
                )
                return
            except ValueError:
                await message.reply_text("❌ رقم السورة 1-114")
                return
        top_surahs = list(reciter.get("available_surahs", list(range(1, 115)))[:10])
        info = "\n".join(f"/download {r_key} {n} - {SURAHS.get(n)}" for n in top_surahs)
        await message.reply_text(
            f"🎙️ **{reciter['name']}**\n{info}\n\n_جميع السور 1-114 متاحة_"
        )

    @app.on_message(filters.command("surah"))
    @safe_handler()
    async def surah_cmd(client, message):
        from bot.data.surahs import SURAH_INFO, SURAHS

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
            await message.reply_text(
                f"📚 **السور (1-20):**\n{lines}\n\n_استخدم /surah [رقم]_"
            )
            return
        try:
            n = int(args[0])
            if not 1 <= n <= 114:
                raise ValueError
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
        from bot.data.glossary import GLOSSARY, GLOSSARY_KEYS

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
            await message.reply_text(
                "⚠️ هل تقصد:\n" + "\n".join(f"• /glossary {k}" for k in close[:5])
            )
        else:
            await message.reply_text(f"❌ مصطلح '{term}' غير موجود")

    @app.on_message(filters.command("search"))
    @safe_handler()
    async def search_cmd(client, message):
        from bot.data.duas import DUA_CATEGORY_KEYS
        from bot.data.glossary import GLOSSARY_KEYS
        from bot.data.surahs import SURAH_INFO, SURAHS

        _track_usage("search")
        args = message.command[1:]
        if not args:
            await message.reply_text(
                "🔍 **بحث شامل**\n\nابحث في المدن والسور والأدعية والمصطلحات.\nمثال: `/search مكة`"
            )
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
                results.append(
                    f"📖 سورة {num} - {name} ({info.get('ayas', '?')} آية) /surah {num}"
                )
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
        more = f"\n...و{len(results) - 15} نتيجة أخرى" if len(results) > 15 else ""
        await message.reply_text(
            f"🔍 **نتائج البحث عن '{query}'** ({len(results)}):\n\n{lines}{more}"
        )
