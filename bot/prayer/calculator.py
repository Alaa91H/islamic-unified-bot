from __future__ import annotations

import os
import time


def _get_logger():
    import logging

    return logging.getLogger(__name__)


class PrayerTimeCalculator:
    __slots__ = (
        "latitude",
        "longitude_val",
        "timezone",
        "_dst",
        "_city_name",
        "method",
        "asr_method",
        "method_config",
        "_calc_cache",
    )

    CALCULATION_METHODS = {
        "karachi": {
            "name": "جامعة الملك عبدالعزيز - كراتشي (University of Islamic Sciences, Karachi)",
            "fajr_angle": 18,
            "isha_angle": 18,
        },
        "makkah": {
            "name": "أم القرى (Umm Al-Qura University)",
            "fajr_angle": 18.5,
            "isha_angle": 90,
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

    PRAYERS = [
        "fajr",
        "sunrise",
        "dhuhr",
        "asr",
        "sunset",
        "maghrib",
        "isha",
        "imsak",
        "midnight",
    ]
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
        import math

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
        self._calc_cache = {}

    def _jdate(self, date) -> float:
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

    def _sun_declination_and_eqtime(self, jdate: float):
        import math

        D = jdate - 2451545.0
        g = math.radians((357.52910 + 0.98564724 * D) % 360)
        q = math.radians((280.46645 + 0.9856474 * D) % 360)
        L = math.radians(
            (
                (math.degrees(q) + 1.914602 * math.sin(g) - 0.020708 * math.sin(2 * g))
                % 360
            )
        )
        T = D / 36525
        e = math.radians(23.439291 - 0.0130042 * T)
        declination = math.degrees(math.asin(math.sin(e) * math.sin(L)))
        y = math.tan(e / 2) ** 2
        eqtime = 4 * math.degrees(
            y * math.sin(2 * L) - 2 * 0.0167 * math.sin(g) * math.cos(L)
        )
        return declination, eqtime

    @staticmethod
    def _is_dst(date) -> bool:
        m = date.month
        return 4 <= m <= 10

    def calculate_times(self, date):
        import math

        date_key = date.strftime("%Y%m%d")
        if date_key in self._calc_cache:
            return self._calc_cache[date_key]

        jdate = self._jdate(date)
        declination, eqtime = self._sun_declination_and_eqtime(jdate)
        latitude_rad = self.latitude
        declination_rad = math.radians(declination)
        tz = self.timezone
        if self._dst:
            tz += 1
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
        ha_fajr = get_hour_angle(-self.method_config["fajr_angle"])
        times["fajr"] = self._decimal_to_time(dhuhr_hour - ha_fajr / 15)
        ha_sunrise = get_hour_angle(-0.833)
        times["sunrise"] = self._decimal_to_time(dhuhr_hour - ha_sunrise / 15)
        times["dhuhr"] = self._decimal_to_time(dhuhr_hour)
        asr_factor = 1.0 if self.asr_method == "standard" else 2.0
        ha_asr = get_hour_angle(asr_factor, is_asr=True)
        times["asr"] = self._decimal_to_time(dhuhr_hour + ha_asr / 15)
        ha_sunset = get_hour_angle(-0.833)
        times["sunset"] = self._decimal_to_time(dhuhr_hour + ha_sunset / 15)
        times["maghrib"] = times["sunset"]

        if self.method == "makkah":
            times["isha"] = self._decimal_to_time(dhuhr_hour + ha_sunset / 15 + 1.5)
        else:
            ha_isha = get_hour_angle(-self.method_config["isha_angle"])
            times["isha"] = self._decimal_to_time(dhuhr_hour + ha_isha / 15)

        fajr_dec = dhuhr_hour - ha_fajr / 15
        imsak_dec = fajr_dec - 10 / 60
        times["imsak"] = self._decimal_to_time(imsak_dec)

        maghrib_dec = dhuhr_hour + ha_sunset / 15
        midnight_dec = (maghrib_dec + fajr_dec) / 2
        if midnight_dec > 24:
            midnight_dec -= 24
        times["midnight"] = self._decimal_to_time(midnight_dec)

        city_name = self._city_name
        if city_name:
            cities = CityCoordinates._load_cities()
            if city_name in cities:
                corr = cities[city_name].get("corrections", {})
                for prayer, offset_min in corr.items():
                    if prayer in times:
                        dec = self._time_to_decimal(times[prayer])
                        dec += offset_min / 60
                        times[prayer] = self._decimal_to_time(dec)

        if len(self._calc_cache) >= 3:
            self._calc_cache.clear()
        self._calc_cache[date_key] = times
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
        latitude: float, longitude: float, date, method: int = 2
    ):
        try:
            import aiohttp
        except ImportError:
            return None
        url = f"https://api.aladhan.com/v1/timings/{date.strftime('%d-%m-%Y')}"
        params = {"latitude": latitude, "longitude": longitude, "method": method}
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url, params=params, timeout=aiohttp.ClientTimeout(total=5)
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        if data.get("code") == 200:
                            return data["data"]["timings"]
                    return None
        except Exception as e:
            _get_logger().warning("Aladhan API error: %s", e)
            return None


class OnlinePrayerTimes:
    __slots__ = ("_cache",)

    def __init__(self):
        self._cache = {}

    async def fetch_aladhan(self, city: str, country: str, date, method: int = 2):
        cache_key = f"aladhan:{city}:{country}:{date.strftime('%Y%m%d')}"
        cached = self._get_cached(cache_key)
        if cached is not None:
            return cached
        try:
            import aiohttp
        except ImportError:
            _get_logger().warning("aiohttp not available for Aladhan API")
            return None
        url = "https://api.aladhan.com/v1/timingsByCity"
        params = {
            "city": city,
            "country": country,
            "method": method,
            "date": date.strftime("%d-%m-%Y"),
        }
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url, params=params, timeout=aiohttp.ClientTimeout(total=5)
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        if data.get("code") == 200:
                            result = self._normalize_timings(data["data"]["timings"])
                            self._set_cache(cache_key, result)
                            return result
                    return None
        except Exception as e:
            _get_logger().warning("Aladhan by-city API error: %s", e)
            return None

    async def fetch_muslimsalat(
        self, city: str, country: str, date, method: str = "mwl"
    ):
        cache_key = f"muslimsalat:{city}:{country}:{date.strftime('%Y%m%d')}"
        cached = self._get_cached(cache_key)
        if cached is not None:
            return cached
        try:
            import aiohttp
        except ImportError:
            _get_logger().warning("aiohttp not available for MuslimSalat API")
            return None
        url = f"https://api.muslimsalat.com/{city}.json"
        params = {
            "key": "",
            "date": date.strftime("%Y-%m-%d"),
            "method": method,
        }
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url, params=params, timeout=aiohttp.ClientTimeout(total=5)
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        items = data.get("items", [])
                        if items:
                            timings = items[0]
                            result = self._normalize_timings(timings)
                            self._set_cache(cache_key, result)
                            return result
                    return None
        except Exception as e:
            _get_logger().warning("MuslimSalat API error: %s", e)
            return None

    async def fetch_all(self, city: str, country: str, date, method: int = 2):
        aladhan_result = await self.fetch_aladhan(city, country, date, method)
        muslimsalat_result = await self.fetch_muslimsalat(city, country, date)
        return {"aladhan": aladhan_result, "muslimsalat": muslimsalat_result}

    def _normalize_timings(self, timings: dict):
        mapping = {
            "Fajr": "fajr",
            "Sunrise": "sunrise",
            "Dhuhr": "dhuhr",
            "Asr": "asr",
            "Sunset": "sunset",
            "Maghrib": "maghrib",
            "Isha": "isha",
            "Imsak": "imsak",
            "Midnight": "midnight",
        }
        result = {}
        for api_key, local_key in mapping.items():
            if api_key in timings:
                val = timings[api_key]
                if len(val) >= 5:
                    result[local_key] = val[:5]
        return result

    def _get_cached(self, key: str):
        if key in self._cache:
            entry = self._cache[key]
            if time.time() - entry["ts"] < 3600:
                return entry["data"]
            del self._cache[key]
        return None

    def _set_cache(self, key: str, data: dict):
        if len(self._cache) > 500:
            self._cache.clear()
        self._cache[key] = {"data": data, "ts": time.time()}


class PrayerTimeVerifier:
    CONFIDENCE_HIGH = "high"
    CONFIDENCE_MEDIUM = "medium"
    CONFIDENCE_LOW = "low"

    @staticmethod
    def verify(
        local_times: dict, aladhan_times: dict = None, muslimsalat_times: dict = None
    ):
        logger = _get_logger()
        prayers = ["fajr", "sunrise", "dhuhr", "asr", "maghrib", "isha"]

        def to_min(t):
            if t and len(t) >= 5 and t[2] == ":":
                h, m = t.split(":")
                return int(h) * 60 + int(m)
            return None

        consensus = {}
        discrepancies = []
        sources_count = 0
        all_sources = {}

        if local_times:
            sources_count += 1
            all_sources["local"] = local_times
        if aladhan_times:
            sources_count += 1
            all_sources["aladhan"] = aladhan_times
        if muslimsalat_times:
            sources_count += 1
            all_sources["muslimsalat"] = muslimsalat_times

        for prayer in prayers:
            values = {}
            for src_name, src_data in all_sources.items():
                if prayer in src_data:
                    v = to_min(src_data[prayer])
                    if v is not None:
                        values[src_name] = v

            if not values:
                continue

            counts = {}
            for v in values.values():
                counts[v] = counts.get(v, 0) + 1

            max_count = max(counts.values())
            if max_count >= 2:
                chosen_val = [v for v, c in counts.items() if c == max_count][0]
                chosen_sources = [s for s, v in values.items() if v == chosen_val]
                chosen_src = chosen_sources[0]
            else:
                chosen_src = (
                    "aladhan" if "aladhan" in values else list(values.keys())[0]
                )
                chosen_val = values[chosen_src]

            if len(set(values.values())) > 1:
                for src_name, val in values.items():
                    if val != chosen_val:
                        discrepancies.append(
                            f"{prayer}: {chosen_src}={chosen_val} vs {src_name}={val}"
                        )

            for src_name, val in values.items():
                if src_name == chosen_src:
                    time_str = f"{val // 60:02d}:{val % 60:02d}"
                    if time_str[2] != ":":
                        time_str = f"{val // 60:02d}:{val % 60:02d}"
                    consensus[prayer] = time_str
                    break
            else:
                consensus[prayer] = f"{chosen_val // 60:02d}:{chosen_val % 60:02d}"

        if discrepancies:
            for d in discrepancies:
                logger.warning("Prayer time discrepancy: %s", d)

        if sources_count >= 2 and max_count >= 2:
            confidence = PrayerTimeVerifier.CONFIDENCE_HIGH
        elif sources_count >= 2:
            confidence = PrayerTimeVerifier.CONFIDENCE_MEDIUM
        else:
            confidence = PrayerTimeVerifier.CONFIDENCE_LOW

        for extra in ["imsak", "midnight"]:
            if local_times and extra in local_times:
                consensus[extra] = local_times[extra]

        return {
            "times": consensus,
            "confidence": confidence,
            "discrepancies": discrepancies,
            "sources_used": sources_count,
        }


_JSON_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "cities.json")


def _load_json_cities():
    try:
        import json
    except ImportError:
        return None
    if not os.path.exists(_JSON_PATH):
        return None
    try:
        with open(_JSON_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def _load_orjson_cities():
    try:
        import orjson
    except ImportError:
        return None
    if not os.path.exists(_JSON_PATH):
        return None
    try:
        with open(_JSON_PATH, "rb") as f:
            return orjson.loads(f.read())
    except Exception:
        return None


def _read_cities_json():
    result = _load_orjson_cities()
    if result is not None:
        return result
    return _load_json_cities()


_CITY_CACHE = None


class CityCoordinates:
    CITIES_CACHE = None

    @classmethod
    def _load_cities(cls):
        global _CITY_CACHE
        if _CITY_CACHE is not None:
            return _CITY_CACHE
        data = _read_cities_json()
        if data is None:
            data = {}
        _CITY_CACHE = data
        return data

    @classmethod
    @property
    def CITIES(cls):
        return cls._load_cities()

    @classmethod
    def get_city_coords(cls, city_name: str):
        cities = cls._load_cities()
        return cities.get(city_name)

    @classmethod
    def get_recommended_method(cls, city_name: str) -> str:
        cities = cls._load_cities()
        city = cities.get(city_name)
        if city and "method" in city:
            return city["method"]
        return "mwl"

    @classmethod
    def search_cities(cls, query: str) -> list:
        query = query.lower()
        cities = cls._load_cities()
        results = []
        for city, data in cities.items():
            if query in city.lower():
                results.append(city)
        return results

    @classmethod
    def get_all_cities(cls) -> dict:
        return cls._load_cities()

    @classmethod
    async def get_city_coords_async(cls, city_name: str):
        cities = cls._load_cities()
        if city_name in cities:
            return cities[city_name]
        try:
            import aiohttp

            async with aiohttp.ClientSession() as session:
                url = "https://nominatim.openstreetmap.org/search"
                params = {
                    "q": city_name,
                    "format": "json",
                    "limit": 1,
                }
                headers = {"User-Agent": "IslamicUnifiedBot/1.0"}
                async with session.get(
                    url,
                    params=params,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=5),
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        if data and len(data) > 0:
                            lat = float(data[0]["lat"])
                            lng = float(data[0]["lon"])
                            display = data[0].get("display_name", "")
                            tz = round(lng / 15)
                            country_parts = display.split(", ")
                            country = (
                                country_parts[-1] if len(country_parts) > 1 else ""
                            )
                            return {
                                "lat": lat,
                                "lng": lng,
                                "tz": tz if tz >= -12 and tz <= 12 else 0,
                                "country": country,
                                "method": "mwl",
                                "dst": False,
                                "corrections": {
                                    "fajr": 0,
                                    "sunrise": 0,
                                    "dhuhr": 0,
                                    "asr": 0,
                                    "maghrib": 0,
                                    "isha": 0,
                                },
                            }
        except Exception:
            _get_logger().warning("Geocoding failed for %s", city_name)
        return None
