import pytest

from bot.qibla import (
    KAABA_LATITUDE,
    KAABA_LONGITUDE,
    calculate_qibla,
    compass_direction,
)


def test_calculate_qibla_returns_zero_distance_at_kaaba_coordinates():
    result = calculate_qibla(KAABA_LATITUDE, KAABA_LONGITUDE)

    assert result.distance_km == pytest.approx(0)
    assert 0 <= result.bearing_degrees < 360


def test_calculate_qibla_returns_valid_direction_and_distance_for_riyadh():
    result = calculate_qibla(24.7136, 46.6753)

    assert 0 <= result.bearing_degrees < 360
    assert result.distance_km > 0
    assert result.compass == compass_direction(result.bearing_degrees)


@pytest.mark.parametrize(
    "latitude, longitude", [(91, 0), (-91, 0), (0, 181), (0, -181)]
)
def test_calculate_qibla_rejects_invalid_coordinates(latitude, longitude):
    with pytest.raises(ValueError, match="invalid coordinates"):
        calculate_qibla(latitude, longitude)
