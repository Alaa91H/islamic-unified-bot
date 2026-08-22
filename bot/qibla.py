"""حسابات القبلة المحلية المشتركة بين واجهات Telegram."""

from dataclasses import dataclass
from math import atan2, cos, degrees, radians, sin, sqrt

KAABA_LATITUDE = 21.4225
KAABA_LONGITUDE = 39.8262
EARTH_RADIUS_KM = 6371.0


@dataclass(frozen=True)
class QiblaResult:
    """نتيجة حساب اتجاه ومسافة القبلة من إحداثيات معتمدة."""

    bearing_degrees: float
    compass: str
    distance_km: float


def compass_direction(bearing_degrees: float) -> str:
    """أعد الاتجاه البوصلي الأقرب لزاوية قبلة صحيحة."""

    directions = [
        (0, "N"),
        (22.5, "NNE"),
        (45, "NE"),
        (67.5, "ENE"),
        (90, "E"),
        (112.5, "ESE"),
        (135, "SE"),
        (157.5, "SSE"),
        (180, "S"),
        (202.5, "SSW"),
        (225, "SW"),
        (247.5, "WSW"),
        (270, "W"),
        (292.5, "WNW"),
        (315, "NW"),
        (337.5, "NNW"),
    ]
    normalized = bearing_degrees % 360
    for angle, label in directions:
        if normalized < angle + 11.25:
            return label
    return "N"


def calculate_qibla(latitude: float, longitude: float) -> QiblaResult:
    """احسب اتجاه ومسافة القبلة من إحداثيات WGS84 محلية."""

    if not -90 <= latitude <= 90 or not -180 <= longitude <= 180:
        raise ValueError("invalid coordinates")

    source_latitude = radians(latitude)
    source_longitude = radians(longitude)
    kaaba_latitude = radians(KAABA_LATITUDE)
    longitude_delta = radians(KAABA_LONGITUDE) - source_longitude
    x_axis = sin(longitude_delta) * cos(kaaba_latitude)
    y_axis = cos(source_latitude) * sin(kaaba_latitude) - sin(source_latitude) * cos(
        kaaba_latitude
    ) * cos(longitude_delta)
    bearing = (degrees(atan2(x_axis, y_axis)) + 360) % 360

    latitude_delta = radians(KAABA_LATITUDE - latitude)
    distance_longitude_delta = radians(KAABA_LONGITUDE - longitude)
    haversine = (
        sin(latitude_delta / 2) ** 2
        + cos(source_latitude)
        * cos(kaaba_latitude)
        * sin(distance_longitude_delta / 2) ** 2
    )
    arc = 2 * atan2(sqrt(haversine), sqrt(1 - haversine))
    return QiblaResult(
        bearing_degrees=bearing,
        compass=compass_direction(bearing),
        distance_km=EARTH_RADIUS_KM * arc,
    )
