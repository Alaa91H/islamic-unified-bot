from datetime import datetime

import pytest

from bot.prayer.calculator import (
    CityCoordinates,
    PrayerTimeCalculator,
    PrayerTimeVerifier,
)


def test_verifier_handles_empty_sources_without_unbound_local_error():
    result = PrayerTimeVerifier.verify({})

    assert result == {
        "times": {},
        "confidence": PrayerTimeVerifier.CONFIDENCE_LOW,
        "discrepancies": [],
        "sources_used": 0,
    }


def test_verifier_uses_two_source_consensus_and_preserves_local_extras():
    local = {"fajr": "04:00", "dhuhr": "12:00", "imsak": "03:50", "midnight": "00:00"}
    aladhan = {"fajr": "04:00", "dhuhr": "12:03"}
    muslimsalat = {"fajr": "04:00", "dhuhr": "12:00"}

    result = PrayerTimeVerifier.verify(local, aladhan, muslimsalat)

    assert result["times"] == {
        "fajr": "04:00",
        "dhuhr": "12:00",
        "imsak": "03:50",
        "midnight": "00:00",
    }
    assert result["confidence"] == PrayerTimeVerifier.CONFIDENCE_HIGH
    assert result["sources_used"] == 3
    assert result["discrepancies"] == ["dhuhr: local=720 vs aladhan=723"]


def test_verifier_ignores_invalid_times_and_keeps_low_confidence_for_one_source():
    result = PrayerTimeVerifier.verify({"fajr": "bad", "dhuhr": "12:20"})

    assert result["times"] == {"dhuhr": "12:20"}
    assert result["confidence"] == PrayerTimeVerifier.CONFIDENCE_LOW


@pytest.mark.asyncio
async def test_city_coordinates_async_returns_known_city_without_geocoding():
    city = await CityCoordinates.get_city_coords_async("مكة المكرمة")

    assert city is not None
    assert city["lat"] == pytest.approx(21.4225)
    assert city["lng"] == pytest.approx(39.8264)


def test_prayer_calculator_rounds_minutes_and_reuses_cached_day_result():
    assert PrayerTimeCalculator._decimal_to_time(23.999) == "00:00"
    calculator = PrayerTimeCalculator(21.4225, 39.8262, timezone=3, method="makkah")
    day = datetime(2026, 6, 18)

    first = calculator.calculate_times(day)
    second = calculator.calculate_times(day)

    assert first is second
