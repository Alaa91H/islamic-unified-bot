from datetime import datetime


def test_calculate_times_returns_all_prayers():
    from bot.prayer.calculator import PrayerTimeCalculator

    calc = PrayerTimeCalculator(
        latitude=21.4225,
        longitude=39.8264,
        timezone=3,
        method="makkah",
    )
    times = calc.calculate_times(datetime(2026, 6, 18))
    for key in ("fajr", "sunrise", "dhuhr", "asr", "maghrib", "isha"):
        assert key in times, f"missing {key}"
        # تنسيق HH:MM
        assert len(times[key]) == 5 and times[key][2] == ":"


def test_calculate_times_returns_hhmm_for_all_methods():
    from bot.prayer.calculator import PrayerTimeCalculator

    for method in ("karachi", "isna", "egypt", "algiers", "dubai", "mwl"):
        calc = PrayerTimeCalculator(
            latitude=30.04,
            longitude=31.23,
            timezone=2,
            method=method,
        )
        times = calc.calculate_times(datetime(2026, 1, 15))
        for p in ("fajr", "dhuhr", "maghrib", "isha"):
            assert times[p][2] == ":", f"{method}/{p} bad format"


def test_hanafi_asr_is_later_than_standard():
    from bot.prayer.calculator import PrayerTimeCalculator

    def asr(method):
        calc = PrayerTimeCalculator(
            latitude=24.71,
            longitude=46.67,
            timezone=3,
            method="isna",
            asr_method=method,
        )
        return calc.calculate_times(datetime(2026, 6, 18))["asr"]

    def to_min(t):
        h, m = t.split(":")
        return int(h) * 60 + int(m)

    assert to_min(asr("hanafi")) >= to_min(asr("standard"))


def test_get_city_coords_makkah():
    from bot.prayer.calculator import CityCoordinates

    c = CityCoordinates.get_city_coords("مكة المكرمة")
    assert c is not None
    assert c["tz"] == 3
    assert c["country"] == "السعودية"
    assert c["method"] == "makkah"


def test_get_city_coords_unknown_returns_none():
    from bot.prayer.calculator import CityCoordinates

    assert CityCoordinates.get_city_coords("مدينة_وهمية") is None


def test_get_recommended_method_returns_method_for_known_city():
    from bot.prayer.calculator import CityCoordinates

    assert CityCoordinates.get_recommended_method("مكة المكرمة") == "makkah"
    assert CityCoordinates.get_recommended_method("القاهرة") == "egypt"
    assert CityCoordinates.get_recommended_method("نيويورك") == "isna"


def test_get_recommended_method_falls_back_for_unknown():
    from bot.prayer.calculator import CityCoordinates

    assert CityCoordinates.get_recommended_method("مدينة_وهمية") == "mwl"


def test_search_cities_finds_match():
    from bot.prayer.calculator import CityCoordinates

    assert "مكة المكرمة" in CityCoordinates.search_cities("مكة")
    assert "القاهرة" in CityCoordinates.search_cities("قاهرة")


def test_get_all_cities_returns_dict():
    from bot.prayer.calculator import CityCoordinates

    cities = CityCoordinates.get_all_cities()
    assert isinstance(cities, dict)
    assert len(cities) >= 30


def test_get_method_name():
    from bot.prayer.calculator import PrayerTimeCalculator

    calc = PrayerTimeCalculator(21.4, 39.8, 3, method="makkah")
    assert "أم القرى" in calc.get_method_name()


def test_mwl_method_is_recognized():
    from bot.prayer.calculator import PrayerTimeCalculator

    calc = PrayerTimeCalculator(21.4, 39.8, 3, method="mwl")
    assert "رابطة العالم الإسلامي" in calc.get_method_name()
    times = calc.calculate_times(datetime(2026, 6, 18))
    assert all(p in times for p in PrayerTimeCalculator.PRAYERS)
