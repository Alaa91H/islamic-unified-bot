"""اختيارات ومعلومات إسلامية محلية حتمية قابلة لإعادة الاستخدام والاختبار."""

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date
from random import Random


@dataclass(frozen=True)
class DailySelection:
    """محتوى الجرعة اليومية الناتج من تاريخ ميلادي ومصادر محلية ثابتة."""

    surah_number: int
    surah_name: str
    dua_name: str
    dua: Mapping[str, str]


def ramadan_status(hijri: tuple[int, int, int] | None) -> str:
    """أنشئ حالة رمضان الحسابية من تاريخ هجري محلي تقديري."""

    if hijri is None:
        return ""
    day, month, year = hijri
    if month == 9:
        return f"✅ **اليوم {day} من رمضان {year} هـ** 🌙\n"
    days_until_ramadan = ((9 - month + 12) % 12) * 30
    ramadan_year = year + (1 if month > 9 else 0)
    return f"📅 رمضان {ramadan_year} هـ بعد ~{days_until_ramadan} يوم\n"


def daily_selection(
    day: date,
    surahs: Mapping[int, str],
    duas: Mapping[str, Mapping[str, str]],
) -> DailySelection:
    """اختر سورة ودعاءً حتميين لليوم من المصادر المحلية."""

    if not surahs or not duas:
        raise ValueError("daily sources must not be empty")
    rng = Random(day.toordinal())
    surah_number = rng.randint(1, 114)
    dua_items = list(duas.items())
    dua_name, dua = rng.choice(dua_items)
    return DailySelection(
        surah_number=surah_number,
        surah_name=surahs.get(surah_number, ""),
        dua_name=dua_name,
        dua=dua,
    )
