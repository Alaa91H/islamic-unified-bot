from datetime import date

from bot.islamic_calendar import HIJRI_EPOCH, to_hijri


def test_to_hijri_returns_first_day_at_supported_epoch():
    assert to_hijri(HIJRI_EPOCH) == (1, 0, 1)


def test_to_hijri_rejects_dates_before_supported_epoch():
    assert to_hijri(date(622, 7, 15)) is None
