"""دوال الوقت الموحدة للبوت.

كل وقت داخلي يُمثَّل كـ datetime واعٍ بالمنطقة الزمنية. تستعمل المدن التي تحمل
معرّف IANA مباشرة، بينما تبقى بيانات المدن القديمة ذات الإزاحة الرقمية مدعومة
لمنع كسر الإعدادات الموجودة أثناء ترحيل قاعدة بيانات المدن.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta, timezone, tzinfo
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

UTC = UTC

# المدن الأكثر استعمالاً والموجودة بصيغ عربية/إنجليزية في ملف البيانات الحالي.
# تعد هذه طبقة انتقالية إلى أن يُضاف حقل `timezone` إلى جميع سجلات cities.json.
_CITY_TIMEZONES = {
    "مكة المكرمة": "Asia/Riyadh",
    "مكة": "Asia/Riyadh",
    "المدينة المنورة": "Asia/Riyadh",
    "الرياض": "Asia/Riyadh",
    "جدة": "Asia/Riyadh",
    "الدمام": "Asia/Riyadh",
    "القاهرة": "Africa/Cairo",
    "الإسكندرية": "Africa/Cairo",
    "دبي": "Asia/Dubai",
    "أبو ظبي": "Asia/Dubai",
    "الدوحة": "Asia/Qatar",
    "الكويت": "Asia/Kuwait",
    "مسقط": "Asia/Muscat",
    "المنامة": "Asia/Bahrain",
    "عمان": "Asia/Amman",
    "القدس": "Asia/Jerusalem",
    "بيروت": "Asia/Beirut",
    "بغداد": "Asia/Baghdad",
    "إسطنبول": "Europe/Istanbul",
    "طهران": "Asia/Tehran",
    "كراتشي": "Asia/Karachi",
    "دكا": "Asia/Dhaka",
    "كوالالمبور": "Asia/Kuala_Lumpur",
    "جاكرتا": "Asia/Jakarta",
    "لندن": "Europe/London",
    "باريس": "Europe/Paris",
    "برلين": "Europe/Berlin",
    "نيويورك": "America/New_York",
    "لوس أنجلوس": "America/Los_Angeles",
    "تورونتو": "America/Toronto",
    "Makkah": "Asia/Riyadh",
    "Medina": "Asia/Riyadh",
    "Riyadh": "Asia/Riyadh",
    "Jeddah": "Asia/Riyadh",
    "Cairo": "Africa/Cairo",
    "Dubai": "Asia/Dubai",
    "Doha": "Asia/Qatar",
    "Kuwait": "Asia/Kuwait",
    "Muscat": "Asia/Muscat",
    "Amman": "Asia/Amman",
    "Istanbul": "Europe/Istanbul",
    "Tehran": "Asia/Tehran",
    "Karachi": "Asia/Karachi",
    "Dhaka": "Asia/Dhaka",
    "Jakarta": "Asia/Jakarta",
    "Kuala Lumpur": "Asia/Kuala_Lumpur",
    "London": "Europe/London",
    "Paris": "Europe/Paris",
    "Berlin": "Europe/Berlin",
    "New York": "America/New_York",
    "Los Angeles": "America/Los_Angeles",
    "Toronto": "America/Toronto",
}


def utc_now() -> datetime:
    """إرجاع الوقت الحالي ككائن واعٍ بمنطقة UTC."""
    return datetime.now(UTC)


def ensure_utc(value: datetime) -> datetime:
    """تحويل الوقت إلى UTC مع التعامل المتوافق مع القيمة القديمة الساذجة."""
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def timezone_for_city(city_name: str, coordinates: dict[str, Any]) -> tzinfo:
    """إرجاع المنطقة الزمنية الحقيقية للمدينة أو fallback ثابتًا متوافقًا."""
    timezone_name = (
        coordinates.get("timezone")
        or coordinates.get("tz_name")
        or _CITY_TIMEZONES.get(city_name)
    )
    if timezone_name:
        try:
            return ZoneInfo(str(timezone_name))
        except ZoneInfoNotFoundError:
            pass

    offset = float(coordinates.get("tz") or 0)
    # نحافظ على السلوك السابق للبيانات القديمة فقط. لا تستعمل هذه الطبقة عند توفر IANA.
    if coordinates.get("dst", False):
        offset += 1
    return timezone(timedelta(hours=offset), name=f"UTC{offset:+g}")


def city_local_time(
    now: datetime, city_name: str, coordinates: dict[str, Any]
) -> datetime:
    """تحويل وقت UTC أو وقت ساذج قديم إلى الوقت المحلي الواعي للمدينة."""
    return ensure_utc(now).astimezone(timezone_for_city(city_name, coordinates))


def offset_hours(value: datetime) -> float:
    """إرجاع إزاحة الوقت الواعي بالساعات لاستخدامها في الحساب الفلكي."""
    offset = value.utcoffset()
    if offset is None:
        return 0.0
    return offset.total_seconds() / 3600
