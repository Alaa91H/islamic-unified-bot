#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import math
from datetime import datetime
from typing import Dict, Optional, Tuple

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
            "isha_angle": 19.5,
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
    }

    # الصلوات المطلوبة
    PRAYERS = ["fajr", "sunrise", "dhuhr", "asr", "sunset", "maghrib", "isha"]
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
        method: str = "isna",
        asr_method: str = "standard",
    ):
        self.latitude = math.radians(latitude)
        self.longitude_val = longitude
        self.timezone = timezone
        self.method = method
        self.asr_method = asr_method
        self.method_config = self.CALCULATION_METHODS.get(
            method, self.CALCULATION_METHODS["isna"]
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
        e = math.radians(23.439291 - 0.0130042 * D)

        declination = math.degrees(math.asin(math.sin(e) * math.sin(L)))

        y = math.tan(e / 2) ** 2
        # eqtime in minutes
        eqtime = 4 * math.degrees(
            y * math.sin(2 * L) - 2 * 0.0167 * math.sin(g) * math.cos(L)
        )
        return declination, eqtime

    def calculate_times(self, date: datetime) -> Dict[str, str]:
        jdate = self._jdate(date)
        declination, eqtime = self._sun_declination_and_eqtime(jdate)

        latitude_rad = self.latitude
        declination_rad = math.radians(declination)

        # dhuhr = 12 + timezone - lon/15 - eqtime/60
        dhuhr_hour = 12 + self.timezone - self.longitude_val / 15 - eqtime / 60

        def get_hour_angle(angle_or_factor, is_asr=False):
            if is_asr:
                # angle_or_factor is the asr factor (1 or 2)
                # arccot(factor + tan|lat-dec|)
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

        return times

    def _decimal_to_time(self, decimal_hour: float) -> str:
        decimal_hour = decimal_hour % 24
        hours = int(decimal_hour)
        minutes = round((decimal_hour - hours) * 60)
        if minutes == 60:
            hours = (hours + 1) % 24
            minutes = 0
        return f"{hours:02d}:{minutes:02d}"

    def get_method_name(self) -> str:
        return self.method_config["name"]


class PrayerTimeAPI:
    @staticmethod
    async def fetch_from_aladhan(
        latitude: float, longitude: float, date: datetime, method: int = 2
    ) -> Optional[Dict]:
        if not _AIOHTTP_AVAILABLE:
            return None
        url = f"http://api.aladhan.com/v1/timings/{date.strftime('%d-%m-%Y')}"
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
        except Exception:
            return None


class CityCoordinates:
    CITIES = {
        "مكة المكرمة": {"lat": 21.4225, "lng": 39.8264, "tz": 3, "country": "السعودية"},
        "المدينة المنورة": {
            "lat": 24.5047,
            "lng": 39.5692,
            "tz": 3,
            "country": "السعودية",
        },
        "الرياض": {"lat": 24.7136, "lng": 46.6753, "tz": 3, "country": "السعودية"},
        "جدة": {"lat": 21.5433, "lng": 39.1728, "tz": 3, "country": "السعودية"},
        "الدمام": {"lat": 26.4124, "lng": 50.1971, "tz": 3, "country": "السعودية"},
        "القاهرة": {"lat": 30.0444, "lng": 31.2357, "tz": 2, "country": "مصر"},
        "الإسكندرية": {"lat": 31.2001, "lng": 29.9187, "tz": 2, "country": "مصر"},
        "الجيزة": {"lat": 30.0131, "lng": 31.2089, "tz": 2, "country": "مصر"},
        "بغداد": {"lat": 33.3128, "lng": 44.3615, "tz": 3, "country": "العراق"},
        "بيروت": {"lat": 33.8886, "lng": 35.4955, "tz": 2, "country": "لبنان"},
        "دمشق": {"lat": 33.5186, "lng": 36.2765, "tz": 2, "country": "سوريا"},
        "عمّان": {"lat": 31.9454, "lng": 35.9284, "tz": 2, "country": "الأردن"},
        "الدوحة": {"lat": 25.2854, "lng": 51.5310, "tz": 3, "country": "قطر"},
        "دبي": {"lat": 25.2048, "lng": 55.2708, "tz": 4, "country": "الإمارات"},
        "أبو ظبي": {"lat": 24.4539, "lng": 54.3773, "tz": 4, "country": "الإمارات"},
        "مسقط": {"lat": 23.6100, "lng": 58.5400, "tz": 4, "country": "عمان"},
        "الكويت": {"lat": 29.3759, "lng": 47.9774, "tz": 3, "country": "الكويت"},
        "الرباط": {"lat": 34.0209, "lng": -6.8416, "tz": 0, "country": "المغرب"},
        "الجزائر": {"lat": 36.7372, "lng": 3.0869, "tz": 1, "country": "الجزائر"},
        "تونس": {"lat": 36.8065, "lng": 10.1686, "tz": 1, "country": "تونس"},
        "الخرطوم": {"lat": 15.5007, "lng": 32.5599, "tz": 2, "country": "السودان"},
        "إسطنبول": {"lat": 41.0082, "lng": 28.9784, "tz": 3, "country": "تركيا"},
        "أنقرة": {"lat": 39.9334, "lng": 32.8597, "tz": 3, "country": "تركيا"},
        "باكستان/كراتشي": {
            "lat": 24.8607,
            "lng": 67.0011,
            "tz": 5,
            "country": "باكستان",
        },
        "لاهور": {"lat": 31.5497, "lng": 74.3436, "tz": 5, "country": "باكستان"},
        "إسلام آباد": {"lat": 33.6844, "lng": 73.1566, "tz": 5, "country": "باكستان"},
        "الدار البيضاء": {"lat": 33.5731, "lng": -7.5898, "tz": 0, "country": "المغرب"},
        "نيويورك": {
            "lat": 40.7128,
            "lng": -74.0060,
            "tz": -5,
            "country": "الولايات المتحدة",
        },
        "لندن": {"lat": 51.5074, "lng": -0.1278, "tz": 0, "country": "المملكة المتحدة"},
        "باريس": {"lat": 48.8566, "lng": 2.3522, "tz": 1, "country": "فرنسا"},
        "برلين": {"lat": 52.5200, "lng": 13.4050, "tz": 1, "country": "ألمانيا"},
        "جاكرتا": {"lat": -6.2088, "lng": 106.8456, "tz": 7, "country": "إندونيسيا"},
        "كوالالمبور": {"lat": 3.1390, "lng": 101.6869, "tz": 8, "country": "ماليزيا"},
        "طوكيو": {"lat": 35.6762, "lng": 139.6503, "tz": 9, "country": "اليابان"},
        "سنغافورة": {"lat": 1.3521, "lng": 103.8198, "tz": 8, "country": "سنغافورة"},
    }

    @classmethod
    def get_city_coords(cls, city_name: str) -> Optional[Dict]:
        return cls.CITIES.get(city_name)

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
