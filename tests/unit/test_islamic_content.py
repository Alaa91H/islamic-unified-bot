from datetime import date

import pytest

from bot.islamic_content import daily_selection, ramadan_status


def test_ramadan_status_handles_current_ramadan_and_future_year_rollover():
    assert ramadan_status((5, 9, 1447)) == "✅ **اليوم 5 من رمضان 1447 هـ** 🌙\n"
    assert ramadan_status((3, 8, 1447)) == "📅 رمضان 1447 هـ بعد ~30 يوم\n"
    assert ramadan_status((3, 10, 1447)) == "📅 رمضان 1448 هـ بعد ~330 يوم\n"
    assert ramadan_status(None) == ""


def test_daily_selection_is_deterministic_and_uses_local_sources():
    surahs = {1: "الفاتحة", 2: "البقرة", 3: "آل عمران"}
    duas = {
        "دعاء أ": {"dua": "أ", "source": "مصدر أ"},
        "دعاء ب": {"dua": "ب", "source": "مصدر ب"},
    }

    first = daily_selection(date(2026, 8, 22), surahs, duas)
    second = daily_selection(date(2026, 8, 22), surahs, duas)

    assert first == second
    assert 1 <= first.surah_number <= 114
    assert first.surah_name == surahs.get(first.surah_number, "")
    assert first.dua_name in duas
    assert first.dua == duas[first.dua_name]


@pytest.mark.parametrize("surahs, duas", [({}, {"دعاء": {}}), ({1: "الفاتحة"}, {})])
def test_daily_selection_rejects_empty_local_sources(surahs, duas):
    with pytest.raises(ValueError, match="must not be empty"):
        daily_selection(date(2026, 8, 22), surahs, duas)
