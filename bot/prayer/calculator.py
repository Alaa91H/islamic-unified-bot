#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
import math
from datetime import datetime
from typing import Dict, Optional, Tuple

logger = logging.getLogger(__name__)

try:
    import aiohttp

    _AIOHTTP_AVAILABLE = True
except ImportError:
    _AIOHTTP_AVAILABLE = False


class PrayerTimeCalculator:
    """حاسبة أوقات الصلاة المتقدمة - Advanced Prayer Times Calculator"""

    # طرق الحساب المختلفة
    CALCULATION_METHODS = {
        "karachi": {
            "name": "جامعة الملك عبدالعزيز - كراتشي (University of Islamic Sciences, Karachi)",
            "fajr_angle": 18,
            "isha_angle": 18,
        },
        "makkah": {
            "name": "أم القرى (Umm Al-Qura University)",
            "fajr_angle": 18.5,
            "isha_angle": 90,  # 90 دقيقة بعد المغرب
        },
        "isna": {
            "name": "جمعية الشمال الأمريكية (Islamic Society of North America)",
            "fajr_angle": 15,
            "isha_angle": 15,
        },
        "egypt": {
            "name": "الهيئة المصرية (Egyptian General Authority)",
            "fajr_angle": 19.5,
            "isha_angle": 17.5,
        },
        "algiers": {
            "name": "أوقات الجزائر (Algiers, Community of Algers)",
            "fajr_angle": 18,
            "isha_angle": 17,
        },
        "dubai": {
            "name": "إمارة دبي (General Authority of Islamic Affairs, Dubai)",
            "fajr_angle": 18.5,
            "isha_angle": 19.5,
        },
        "mwl": {
            "name": "رابطة العالم الإسلامي (Muslim World League)",
            "fajr_angle": 18,
            "isha_angle": 17,
        },
    }

    # الصلوات المطلوبة
    PRAYERS = ["fajr", "sunrise", "dhuhr", "asr", "sunset", "maghrib", "isha", "imsak", "midnight"]
    PRAYER_NAMES = {
        "fajr": "🌅 الفجر",
        "sunrise": "🌄 الشروق",
        "dhuhr": "☀️ الظهر",
        "asr": "⛅ العصر",
        "sunset": "🌅 الغروب",
        "maghrib": "🌆 المغرب",
        "isha": "🌙 العشاء",
    }

    def __init__(
        self,
        latitude: float,
        longitude: float,
        timezone: int = 0,
        method: str = "mwl",
        asr_method: str = "standard",
        dst: bool = False,
        city_name: str = "",
    ):
        self.latitude = math.radians(latitude)
        self.longitude_val = longitude
        self.timezone = timezone
        self._dst = dst
        self._city_name = city_name
        self.method = method
        self.asr_method = asr_method
        self.method_config = self.CALCULATION_METHODS.get(
            method, self.CALCULATION_METHODS["mwl"]
        )

    def _jdate(self, date: datetime) -> float:
        a = (14 - date.month) // 12
        y = date.year + 4800 - a
        m = date.month + 12 * a - 3
        return (
            date.day
            + (153 * m + 2) // 5
            + 365 * y
            + y // 4
            - y // 100
            + y // 400
            - 32045.5
        )

    def _sun_declination_and_eqtime(self, jdate: float) -> Tuple[float, float]:
        D = jdate - 2451545.0
        g = math.radians((357.52910 + 0.98564724 * D) % 360)
        q = math.radians((280.46645 + 0.9856474 * D) % 360)
        L = math.radians(
            (
                (math.degrees(q) + 1.914602 * math.sin(g) - 0.020708 * math.sin(2 * g))
                % 360
            )
        )
        T = D / 36525  # قرون منذ J2000
        e = math.radians(23.439291 - 0.0130042 * T)

        declination = math.degrees(math.asin(math.sin(e) * math.sin(L)))

        y = math.tan(e / 2) ** 2
        # eqtime in minutes
        eqtime = 4 * math.degrees(
            y * math.sin(2 * L) - 2 * 0.0167 * math.sin(g) * math.cos(L)
        )
        return declination, eqtime

    @staticmethod
    def _is_dst(date: datetime) -> bool:
        """مصر وبعض الدول: DST من أبريل إلى أكتوبر (آخر جمعة أبريل - آخر خميس أكتوبر)."""
        m = date.month
        return 4 <= m <= 10  # تقريب كافٍ للدقة المطلوبة

    def calculate_times(self, date: datetime) -> Dict[str, str]:
        jdate = self._jdate(date)
        declination, eqtime = self._sun_declination_and_eqtime(jdate)

        latitude_rad = self.latitude
        declination_rad = math.radians(declination)

        tz = self.timezone
        if self._dst:
            tz += 1

        # dhuhr = 12 + timezone - lon/15 - eqtime/60
        dhuhr_hour = 12 + tz - self.longitude_val / 15 - eqtime / 60

        def get_hour_angle(angle_or_factor, is_asr=False):
            if is_asr:
                term = angle_or_factor + math.tan(abs(latitude_rad - declination_rad))
                cos_ha = (
                    math.sin(math.atan(1 / term))
                    - math.sin(latitude_rad) * math.sin(declination_rad)
                ) / (math.cos(latitude_rad) * math.cos(declination_rad))
            else:
                angle_rad = math.radians(angle_or_factor)
                cos_ha = (
                    math.sin(angle_rad)
                    - math.sin(latitude_rad) * math.sin(declination_rad)
                ) / (math.cos(latitude_rad) * math.cos(declination_rad))

            cos_ha = max(-1, min(1, cos_ha))
            return math.degrees(math.acos(cos_ha))

        times = {}

        # الفجر
        ha_fajr = get_hour_angle(-self.method_config["fajr_angle"])
        times["fajr"] = self._decimal_to_time(dhuhr_hour - ha_fajr / 15)

        # الشروق
        ha_sunrise = get_hour_angle(-0.833)
        times["sunrise"] = self._decimal_to_time(dhuhr_hour - ha_sunrise / 15)

        # الظهر
        times["dhuhr"] = self._decimal_to_time(dhuhr_hour)

        # العصر
        asr_factor = 1.0 if self.asr_method == "standard" else 2.0
        ha_asr = get_hour_angle(asr_factor, is_asr=True)
        times["asr"] = self._decimal_to_time(dhuhr_hour + ha_asr / 15)

        # الغروب
        ha_sunset = get_hour_angle(-0.833)
        times["sunset"] = self._decimal_to_time(dhuhr_hour + ha_sunset / 15)

        # المغرب
        times["maghrib"] = times["sunset"]

        # العشاء
        if self.method == "makkah":
            times["isha"] = self._decimal_to_time(dhuhr_hour + ha_sunset / 15 + 1.5)
        else:
            ha_isha = get_hour_angle(-self.method_config["isha_angle"])
            times["isha"] = self._decimal_to_time(dhuhr_hour + ha_isha / 15)

        # الإمساك = الفجر - 10 دقائق
        fajr_dec = dhuhr_hour - ha_fajr / 15
        imsak_dec = fajr_dec - 10 / 60
        times["imsak"] = self._decimal_to_time(imsak_dec)

        # منتصف الليل = (المغرب + الفجر) / 2 (بعد ضبط الالتفاف)
        maghrib_dec = dhuhr_hour + ha_sunset / 15
        midnight_dec = (maghrib_dec + fajr_dec) / 2
        if midnight_dec > 24:
            midnight_dec -= 24
        times["midnight"] = self._decimal_to_time(midnight_dec)

        # تطبيق التصحيحات الدقيقة للمدينة
        city_name = self._city_name
        if city_name and city_name in CityCoordinates.CITIES:
            corr = CityCoordinates.CITIES[city_name].get("corrections", {})
            for prayer, offset_min in corr.items():
                if prayer in times:
                    dec = self._time_to_decimal(times[prayer])
                    dec += offset_min / 60
                    times[prayer] = self._decimal_to_time(dec)

        return times

    def _decimal_to_time(self, decimal_hour: float) -> str:
        decimal_hour = decimal_hour % 24
        hours = int(decimal_hour)
        minutes = round((decimal_hour - hours) * 60)
        if minutes == 60:
            hours = (hours + 1) % 24
            minutes = 0
        return f"{hours:02d}:{minutes:02d}"

    @staticmethod
    def _time_to_decimal(time_str: str) -> float:
        h, m = map(int, time_str.split(":"))
        return h + m / 60

    def get_method_name(self) -> str:
        return self.method_config["name"]


class PrayerTimeAPI:
    @staticmethod
    async def fetch_from_aladhan(
        latitude: float, longitude: float, date: datetime, method: int = 2
    ) -> Optional[Dict]:
        if not _AIOHTTP_AVAILABLE:
            return None
        url = f"https://api.aladhan.com/v1/timings/{date.strftime('%d-%m-%Y')}"
        params = {"latitude": latitude, "longitude": longitude, "method": method}
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url, params=params, timeout=aiohttp.ClientTimeout(total=10)
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        if data.get("code") == 200:
                            return data["data"]["timings"]
                    return None
        except Exception as e:
            logger.warning("Aladhan API error: %s", e)
            return None


class CityCoordinates:
    CITIES = {
        "مكة المكرمة": {
            "lat": 21.4225, "lng": 39.8264, "tz": 3, "country": "السعودية", "method": "makkah",
            "dst": False, "corrections": {"fajr": 2, "sunrise": 1, "dhuhr": 2, "asr": 1, "maghrib": 1, "isha": 2},
        },
        "المدينة المنورة": {
            "lat": 24.5047, "lng": 39.5692, "tz": 3, "country": "السعودية", "method": "makkah",
            "dst": False, "corrections": {"fajr": 2, "sunrise": 0, "dhuhr": 2, "asr": 0, "maghrib": 0, "isha": 0},
        },
        "الرياض": {
            "lat": 24.7136, "lng": 46.6753, "tz": 3, "country": "السعودية", "method": "makkah",
            "dst": False, "corrections": {"fajr": 2, "sunrise": 0, "dhuhr": 0, "asr": 1, "maghrib": 0, "isha": 0},
        },
        "جدة": {
            "lat": 21.5433, "lng": 39.1728, "tz": 3, "country": "السعودية", "method": "makkah",
            "dst": False, "corrections": {"fajr": 2, "sunrise": 0, "dhuhr": 1, "asr": 2, "maghrib": 0, "isha": 0},
        },
        "الدمام": {
            "lat": 26.4124, "lng": 50.1971, "tz": 3, "country": "السعودية", "method": "makkah",
            "dst": False, "corrections": {"fajr": 0, "sunrise": 0, "dhuhr": 0, "asr": 1, "maghrib": 1, "isha": 1},
        },
        "القاهرة": {
            "lat": 30.0444, "lng": 31.2357, "tz": 2, "country": "مصر", "method": "egypt",
            "dst": True, "corrections": {"fajr": 2, "sunrise": 2, "dhuhr": 1, "asr": 2, "maghrib": 0, "isha": 2},
        },
        "الإسكندرية": {
            "lat": 31.2001, "lng": 29.9187, "tz": 2, "country": "مصر", "method": "egypt",
            "dst": True, "corrections": {"fajr": 2, "sunrise": 0, "dhuhr": 1, "asr": 2, "maghrib": 0, "isha": 2},
        },
        "الجيزة": {
            "lat": 30.0131, "lng": 31.2089, "tz": 2, "country": "مصر", "method": "egypt",
            "dst": True, "corrections": {"fajr": 1, "sunrise": 2, "dhuhr": 0, "asr": 2, "maghrib": 0, "isha": 2},
        },
        "بغداد": {
            "lat": 33.3128, "lng": 44.3615, "tz": 3, "country": "العراق", "method": "karachi",
            "dst": False, "corrections": {"fajr": -1, "sunrise": 0, "dhuhr": -1, "asr": -1, "maghrib": 0, "isha": 0},
        },
        "بيروت": {
            "lat": 33.8886, "lng": 35.4955, "tz": 2, "country": "لبنان", "method": "egypt",
            "dst": True, "corrections": {"fajr": -1, "sunrise": 0, "dhuhr": 0, "asr": 0, "maghrib": 0, "isha": 0},
        },
        "دمشق": {
            "lat": 33.5186, "lng": 36.2765, "tz": 2, "country": "سوريا", "method": "egypt",
            "dst": True, "corrections": {"fajr": -1, "sunrise": 0, "dhuhr": 0, "asr": 0, "maghrib": 0, "isha": 0},
        },
        "عمّان": {
            "lat": 31.9454, "lng": 35.9284, "tz": 2, "country": "الأردن", "method": "egypt",
            "dst": True, "corrections": {"fajr": -1, "sunrise": 0, "dhuhr": 0, "asr": 0, "maghrib": 0, "isha": 0},
        },
        "الدوحة": {
            "lat": 25.2854, "lng": 51.5310, "tz": 3, "country": "قطر", "method": "makkah",
            "dst": False, "corrections": {"fajr": -2, "sunrise": -2, "dhuhr": -2, "asr": -2, "maghrib": -2, "isha": -2},
        },
        "دبي": {
            "lat": 25.2048, "lng": 55.2708, "tz": 4, "country": "الإمارات", "method": "dubai",
            "dst": False, "corrections": {"fajr": 2, "sunrise": 2, "dhuhr": 2, "asr": 2, "maghrib": 2, "isha": 2},
        },
        "أبو ظبي": {
            "lat": 24.4539, "lng": 54.3773, "tz": 4, "country": "الإمارات", "method": "dubai",
            "dst": False, "corrections": {"fajr": 2, "sunrise": 2, "dhuhr": 2, "asr": 2, "maghrib": 2, "isha": 2},
        },
        "مسقط": {
            "lat": 23.6100, "lng": 58.5400, "tz": 4, "country": "عمان", "method": "karachi",
            "dst": False, "corrections": {"fajr": 2, "sunrise": 2, "dhuhr": 2, "asr": 2, "maghrib": 2, "isha": 2},
        },
        "الكويت": {
            "lat": 29.3759, "lng": 47.9774, "tz": 3, "country": "الكويت", "method": "makkah",
            "dst": False, "corrections": {"fajr": 2, "sunrise": 1, "dhuhr": 2, "asr": 1, "maghrib": 1, "isha": 2},
        },
        "الرباط": {
            "lat": 34.0209, "lng": -6.8416, "tz": 0, "country": "المغرب", "method": "algiers",
            "dst": True, "corrections": {"fajr": 1, "sunrise": 0, "dhuhr": 1, "asr": 1, "maghrib": 1, "isha": 1},
        },
        "الجزائر": {
            "lat": 36.7372, "lng": 3.0869, "tz": 1, "country": "الجزائر", "method": "algiers",
            "dst": False, "corrections": {"fajr": 1, "sunrise": 0, "dhuhr": 1, "asr": 1, "maghrib": 0, "isha": 1},
        },
        "تونس": {
            "lat": 36.8065, "lng": 10.1686, "tz": 1, "country": "تونس", "method": "algiers",
            "dst": False, "corrections": {"fajr": 1, "sunrise": 0, "dhuhr": 1, "asr": 0, "maghrib": 0, "isha": 1},
        },
        "الخرطوم": {
            "lat": 15.5007, "lng": 32.5599, "tz": 2, "country": "السودان", "method": "egypt",
            "dst": False, "corrections": {"fajr": 1, "sunrise": 0, "dhuhr": 1, "asr": 1, "maghrib": 0, "isha": 1},
        },
        "إسطنبول": {
            "lat": 41.0082, "lng": 28.9784, "tz": 3, "country": "تركيا", "method": "isna",
            "dst": True, "corrections": {"fajr": 2, "sunrise": 1, "dhuhr": 2, "asr": 1, "maghrib": 1, "isha": 2},
        },
        "أنقرة": {
            "lat": 39.9334, "lng": 32.8597, "tz": 3, "country": "تركيا", "method": "isna",
            "dst": True, "corrections": {"fajr": 2, "sunrise": 1, "dhuhr": 2, "asr": 1, "maghrib": 1, "isha": 2},
        },
        "باكستان/كراتشي": {
            "lat": 24.8607, "lng": 67.0011, "tz": 5, "country": "باكستان", "method": "karachi",
            "dst": False, "corrections": {"fajr": 1, "sunrise": 0, "dhuhr": 1, "asr": 1, "maghrib": 0, "isha": 1},
        },
        "لاهور": {
            "lat": 31.5497, "lng": 74.3436, "tz": 5, "country": "باكستان", "method": "karachi",
            "dst": False, "corrections": {"fajr": 1, "sunrise": 0, "dhuhr": 1, "asr": 0, "maghrib": 0, "isha": 1},
        },
        "إسلام آباد": {
            "lat": 33.6844, "lng": 73.1566, "tz": 5, "country": "باكستان", "method": "karachi",
            "dst": False, "corrections": {"fajr": 0, "sunrise": 0, "dhuhr": 1, "asr": 0, "maghrib": 0, "isha": 1},
        },
        "الدار البيضاء": {
            "lat": 33.5731, "lng": -7.5898, "tz": 0, "country": "المغرب", "method": "algiers",
            "dst": True, "corrections": {"fajr": 1, "sunrise": 0, "dhuhr": 1, "asr": 0, "maghrib": 1, "isha": 1},
        },
        "نيويورك": {
            "lat": 40.7128, "lng": -74.0060, "tz": -5, "country": "الولايات المتحدة", "method": "isna",
            "dst": True, "corrections": {"fajr": 2, "sunrise": 1, "dhuhr": 2, "asr": 1, "maghrib": 1, "isha": 2},
        },
        "لندن": {
            "lat": 51.5074, "lng": -0.1278, "tz": 0, "country": "المملكة المتحدة", "method": "isna",
            "dst": True, "corrections": {"fajr": 2, "sunrise": 1, "dhuhr": 2, "asr": 1, "maghrib": 1, "isha": 2},
        },
        "باريس": {
            "lat": 48.8566, "lng": 2.3522, "tz": 1, "country": "فرنسا", "method": "isna",
            "dst": True, "corrections": {"fajr": 2, "sunrise": 1, "dhuhr": 2, "asr": 1, "maghrib": 1, "isha": 2},
        },
        "برلين": {
            "lat": 52.5200, "lng": 13.4050, "tz": 1, "country": "ألمانيا", "method": "isna",
            "dst": True, "corrections": {"fajr": 2, "sunrise": 1, "dhuhr": 2, "asr": 1, "maghrib": 1, "isha": 2},
        },
        "جاكرتا": {
            "lat": -6.2088, "lng": 106.8456, "tz": 7, "country": "إندونيسيا", "method": "karachi",
            "dst": False, "corrections": {"fajr": 1, "sunrise": 0, "dhuhr": 1, "asr": 0, "maghrib": 0, "isha": 1},
        },
        "كوالالمبور": {
            "lat": 3.1390, "lng": 101.6869, "tz": 8, "country": "ماليزيا", "method": "karachi",
            "dst": False, "corrections": {"fajr": 1, "sunrise": 0, "dhuhr": 1, "asr": 0, "maghrib": 0, "isha": 1},
        },
        "طوكيو": {
            "lat": 35.6762, "lng": 139.6503, "tz": 9, "country": "اليابان", "method": "isna",
            "dst": False, "corrections": {"fajr": 2, "sunrise": 1, "dhuhr": 1, "asr": 1, "maghrib": 0, "isha": 1},
        },
        "سنغافورة": {
            "lat": 1.3521, "lng": 103.8198, "tz": 8, "country": "سنغافورة", "method": "karachi",
            "dst": False, "corrections": {"fajr": 1, "sunrise": 0, "dhuhr": 1, "asr": 0, "maghrib": 0, "isha": 1},
        },
        "مراكش": {
            "lat": 31.6346, "lng": -8.0083, "tz": 0, "country": "المغرب", "method": "algiers",
            "dst": True, "corrections": {"fajr": 1, "sunrise": 0, "dhuhr": 1, "asr": 0, "maghrib": 1, "isha": 1},
        },
        "صنعاء": {
            "lat": 15.3694, "lng": 44.1910, "tz": 3, "country": "اليمن", "method": "makkah",
            "dst": False, "corrections": {"fajr": 2, "sunrise": 1, "dhuhr": 2, "asr": 1, "maghrib": 1, "isha": 2},
        },
        "عدن": {
            "lat": 12.7855, "lng": 45.0381, "tz": 3, "country": "اليمن", "method": "makkah",
            "dst": False, "corrections": {"fajr": 2, "sunrise": 1, "dhuhr": 1, "asr": 1, "maghrib": 1, "isha": 1},
        },
        "الموصل": {
            "lat": 36.3569, "lng": 43.1667, "tz": 3, "country": "العراق", "method": "karachi",
            "dst": False, "corrections": {"fajr": 0, "sunrise": 0, "dhuhr": 0, "asr": 0, "maghrib": 0, "isha": 0},
        },
        "حلب": {
            "lat": 36.2028, "lng": 37.1348, "tz": 2, "country": "سوريا", "method": "egypt",
            "dst": True, "corrections": {"fajr": 0, "sunrise": 0, "dhuhr": 0, "asr": 0, "maghrib": 0, "isha": 0},
        },
        "غزة": {
            "lat": 31.5017, "lng": 34.4668, "tz": 2, "country": "فلسطين", "method": "egypt",
            "dst": True, "corrections": {"fajr": 0, "sunrise": 0, "dhuhr": 0, "asr": 0, "maghrib": 0, "isha": 0},
        },
        "القدس": {
            "lat": 31.7683, "lng": 35.2137, "tz": 2, "country": "فلسطين", "method": "egypt",
            "dst": True, "corrections": {"fajr": 0, "sunrise": 0, "dhuhr": 0, "asr": 0, "maghrib": 0, "isha": 0},
        },
        "منامة": {
            "lat": 26.2235, "lng": 50.5876, "tz": 3, "country": "البحرين", "method": "makkah",
            "dst": False, "corrections": {"fajr": 2, "sunrise": 1, "dhuhr": 2, "asr": 1, "maghrib": 1, "isha": 2},
        },
        "طرابلس": {
            "lat": 32.8872, "lng": 13.1913, "tz": 2, "country": "ليبيا", "method": "egypt",
            "dst": True, "corrections": {"fajr": 1, "sunrise": 0, "dhuhr": 1, "asr": 1, "maghrib": 0, "isha": 1},
        },
        "تونس العاصمة": {
            "lat": 36.8065, "lng": 10.1686, "tz": 1, "country": "تونس", "method": "algiers",
            "dst": False, "corrections": {"fajr": 1, "sunrise": 0, "dhuhr": 1, "asr": 0, "maghrib": 0, "isha": 1},
        },
        "مقديشو": {
            "lat": 2.0469, "lng": 45.3182, "tz": 3, "country": "الصومال", "method": "makkah",
            "dst": False, "corrections": {"fajr": 2, "sunrise": 1, "dhuhr": 2, "asr": 1, "maghrib": 1, "isha": 2},
        },
        "دكار": {
            "lat": 14.7167, "lng": -17.4677, "tz": 0, "country": "السنغال", "method": "algiers",
            "dst": False, "corrections": {"fajr": 1, "sunrise": 0, "dhuhr": 1, "asr": 0, "maghrib": 0, "isha": 1},
        },
        "كابول": {
            "lat": 34.5553, "lng": 69.2075, "tz": 4.5, "country": "أفغانستان", "method": "karachi",
            "dst": False, "corrections": {"fajr": 1, "sunrise": 0, "dhuhr": 1, "asr": 0, "maghrib": 0, "isha": 1},
        },
        "أربيل": {
            "lat": 36.1911, "lng": 44.0094, "tz": 3, "country": "العراق", "method": "karachi",
            "dst": False, "corrections": {"fajr": 0, "sunrise": 0, "dhuhr": 0, "asr": 0, "maghrib": 0, "isha": 0},
        },
        "عمان": {
            "lat": 23.5880, "lng": 58.3829, "tz": 4, "country": "عمان", "method": "karachi",
            "dst": False, "corrections": {"fajr": 2, "sunrise": 2, "dhuhr": 2, "asr": 2, "maghrib": 2, "isha": 2},
        },
        "خارطوم": {
            "lat": 15.5007, "lng": 32.5599, "tz": 2, "country": "السودان", "method": "egypt",
            "dst": False, "corrections": {"fajr": 1, "sunrise": 0, "dhuhr": 1, "asr": 1, "maghrib": 0, "isha": 1},
        },
        "كراتشي": {
            "lat": 24.8607, "lng": 67.0011, "tz": 5, "country": "باكستان", "method": "karachi",
            "dst": False, "corrections": {"fajr": 1, "sunrise": 0, "dhuhr": 1, "asr": 1, "maghrib": 0, "isha": 1},
        },
        "دلهي": {
            "lat": 28.6139, "lng": 77.2090, "tz": 5.5, "country": "الهند", "method": "karachi",
            "dst": False, "corrections": {"fajr": 1, "sunrise": 0, "dhuhr": 1, "asr": 0, "maghrib": 0, "isha": 1},
        },
        "مومباي": {
            "lat": 19.0760, "lng": 72.8777, "tz": 5.5, "country": "الهند", "method": "karachi",
            "dst": False, "corrections": {"fajr": 1, "sunrise": 0, "dhuhr": 1, "asr": 0, "maghrib": 0, "isha": 1},
        },
        "دكا": {
            "lat": 23.8103, "lng": 90.4125, "tz": 6, "country": "بنغلاديش", "method": "karachi",
            "dst": False, "corrections": {"fajr": 1, "sunrise": 0, "dhuhr": 1, "asr": 0, "maghrib": 0, "isha": 1},
        },
        "لاغوس": {
            "lat": 6.5244, "lng": 3.3792, "tz": 1, "country": "نيجيريا", "method": "egypt",
            "dst": False, "corrections": {"fajr": 1, "sunrise": 0, "dhuhr": 1, "asr": 0, "maghrib": 0, "isha": 1},
        },
        "كيب تاون": {
            "lat": -33.9249, "lng": 18.4241, "tz": 2, "country": "جنوب أفريقيا", "method": "isna",
            "dst": False, "corrections": {"fajr": 2, "sunrise": 1, "dhuhr": 2, "asr": 1, "maghrib": 1, "isha": 2},
        },
        "القيروان": {
            "lat": 35.6783, "lng": 10.1009, "tz": 1, "country": "تونس", "method": "algiers",
            "dst": False, "corrections": {"fajr": 1, "sunrise": 0, "dhuhr": 1, "asr": 0, "maghrib": 0, "isha": 1},
        },
        "فاس": {
            "lat": 34.0333, "lng": -5.0000, "tz": 0, "country": "المغرب", "method": "algiers",
            "dst": True, "corrections": {"fajr": 1, "sunrise": 0, "dhuhr": 1, "asr": 0, "maghrib": 1, "isha": 1},
        },
    }

    @classmethod
    def get_city_coords(cls, city_name: str) -> Optional[Dict]:
        return cls.CITIES.get(city_name)

    @classmethod
    def get_recommended_method(cls, city_name: str) -> str:
        city = cls.CITIES.get(city_name)
        if city and "method" in city:
            return city["method"]
        return "mwl"

    @classmethod
    def search_cities(cls, query: str) -> list:
        query = query.lower()
        results = []
        for city, data in cls.CITIES.items():
            if query in city.lower():
                results.append(city)
        return results

    @classmethod
    def get_all_cities(cls) -> Dict:
        return cls.CITIES
