from datetime import datetime

from bot.prayer.calculator import CityCoordinates, PrayerTimeCalculator


class TestPrayerTimeCalculator:

    def setup_method(self):
        self.calc_makkah = PrayerTimeCalculator(
            latitude=21.3891, longitude=39.8579, timezone=3, method="makkah"
        )
        self.calc_isna = PrayerTimeCalculator(
            latitude=40.7128, longitude=-74.0060, timezone=-5, method="isna"
        )
        self.test_date = datetime(2024, 3, 15, 12, 0, 0)

    # --- calculate_times ---

    def test_calculate_times_returns_dict(self):
        result = self.calc_makkah.calculate_times(self.test_date)
        assert isinstance(result, dict)

    def test_calculate_times_contains_all_prayers(self):
        result = self.calc_makkah.calculate_times(self.test_date)
        required = {"fajr", "dhuhr", "asr", "maghrib", "isha"}
        assert required.issubset(
            result.keys()
        ), f"Missing prayers: {required - result.keys()}"

    def test_calculate_times_format_hh_mm(self):
        result = self.calc_makkah.calculate_times(self.test_date)
        for prayer, time_str in result.items():
            if prayer in ("fajr", "dhuhr", "asr", "maghrib", "isha"):
                parts = time_str.split(":")
                assert len(parts) == 2, f"{prayer} time '{time_str}' not HH:MM"
                h, m = int(parts[0]), int(parts[1])
                assert 0 <= h < 24, f"{prayer} hour out of range: {h}"
                assert 0 <= m < 60, f"{prayer} minute out of range: {m}"

    def test_prayer_times_logical_order(self):
        result = self.calc_makkah.calculate_times(self.test_date)

        def to_minutes(t):
            h, m = map(int, t.split(":"))
            return h * 60 + m

        fajr = to_minutes(result["fajr"])
        dhuhr = to_minutes(result["dhuhr"])
        asr = to_minutes(result["asr"])
        maghrib = to_minutes(result["maghrib"])
        isha = to_minutes(result["isha"])

        assert (
            fajr < dhuhr
        ), f"Fajr {result['fajr']} must be before Dhuhr {result['dhuhr']}"
        assert (
            dhuhr < asr
        ), f"Dhuhr {result['dhuhr']} must be before Asr {result['asr']}"
        assert (
            asr < maghrib
        ), f"Asr {result['asr']} must be before Maghrib {result['maghrib']}"
        assert (
            maghrib < isha
        ), f"Maghrib {result['maghrib']} must be before Isha {result['isha']}"

    def test_different_methods_give_different_results(self):
        result_makkah = self.calc_makkah.calculate_times(self.test_date)
        result_isna = PrayerTimeCalculator(
            latitude=21.3891, longitude=39.8579, timezone=3, method="isna"
        ).calculate_times(self.test_date)
        assert result_makkah["fajr"] != result_isna["fajr"]

    def test_calculate_times_different_dates(self):
        date1 = datetime(2024, 6, 21)
        date2 = datetime(2024, 12, 21)
        r1 = self.calc_makkah.calculate_times(date1)
        r2 = self.calc_makkah.calculate_times(date2)
        assert r1["maghrib"] != r2["maghrib"], "Sunset should differ between solstices"

    def test_northern_hemisphere_calculator(self):
        calc = PrayerTimeCalculator(
            latitude=51.5074, longitude=-0.1278, timezone=0, method="isna"
        )
        result = calc.calculate_times(self.test_date)
        assert isinstance(result, dict)
        assert "fajr" in result

    def test_southern_hemisphere_calculator(self):
        calc = PrayerTimeCalculator(
            latitude=-33.8688, longitude=151.2093, timezone=11, method="karachi"
        )
        result = calc.calculate_times(self.test_date)
        assert isinstance(result, dict)
        assert "fajr" in result

    def test_get_method_name_returns_string(self):
        name = self.calc_makkah.get_method_name()
        assert isinstance(name, str)
        assert len(name) > 0


class TestCityCoordinates:

    def test_get_city_coords_makkah(self):
        coords = CityCoordinates.get_city_coords("مكة المكرمة")
        assert coords is not None
        assert "lat" in coords
        assert "lng" in coords
        assert "country" in coords

    def test_get_city_coords_lat_lng_valid_range(self):
        coords = CityCoordinates.get_city_coords("مكة المكرمة")
        assert -90 <= coords["lat"] <= 90, "Latitude out of range"
        assert -180 <= coords["lng"] <= 180, "Longitude out of range"

    def test_get_city_coords_nonexistent_returns_none(self):
        result = CityCoordinates.get_city_coords("مدينة_غير_موجودة_xyz_123")
        assert result is None

    def test_get_all_cities_returns_dict(self):
        cities = CityCoordinates.get_all_cities()
        assert isinstance(cities, dict)
        assert len(cities) > 0

    def test_get_all_cities_minimum_count(self):
        cities = CityCoordinates.get_all_cities()
        assert len(cities) >= 10, f"Expected at least 10 cities, got {len(cities)}"

    def test_search_cities_arabic(self):
        results = CityCoordinates.search_cities("مكة")
        assert isinstance(results, list)
        assert len(results) > 0

    def test_search_cities_empty_query(self):
        results = CityCoordinates.search_cities("")
        assert isinstance(results, list)

    def test_search_cities_no_match(self):
        results = CityCoordinates.search_cities("زzzzznonexistent999")
        assert isinstance(results, list)

    def test_all_cities_have_valid_coords(self):
        cities = CityCoordinates.get_all_cities()
        for city_name, coords in cities.items():
            assert "lat" in coords, f"Missing lat for {city_name}"
            assert "lng" in coords, f"Missing lng for {city_name}"
            assert -90 <= coords["lat"] <= 90, f"Invalid lat for {city_name}"
            assert -180 <= coords["lng"] <= 180, f"Invalid lng for {city_name}"
