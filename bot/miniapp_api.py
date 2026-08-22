"""واجهة HTTP اختيارية وآمنة لبيانات Telegram Mini App الحية."""

from __future__ import annotations

import logging
from urllib.parse import urlparse

import aiosqlite
from fastapi import FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from starlette.middleware.trustedhost import TrustedHostMiddleware

from bot.db.repositories.user_settings import UserSettings
from bot.miniapp_auth import (
    InitDataValidationError,
    TelegramWebAppIdentity,
    validate_init_data,
)
from bot.observability import log_event
from bot.prayer.calculator import CityCoordinates, PrayerTimeCalculator
from bot.time_utils import city_local_time, utc_now

logger = logging.getLogger(__name__)


class PreferencesInput(BaseModel):
    city: str = Field(min_length=1, max_length=120)
    language: str = Field(pattern="^(ar|en)$")
    notifications_on: bool


class PreferencesResponse(BaseModel):
    configured: bool
    city: str | None = None
    language: str | None = None
    notifications_on: bool | None = None


class SaveResponse(BaseModel):
    saved: bool


class CityResponse(BaseModel):
    name: str
    country: str
    method: str
    method_name: str


class CitiesResponse(BaseModel):
    query: str
    cities: list[CityResponse]


class ProfileResponse(BaseModel):
    username: str | None


class TodayCityResponse(CityResponse):
    asr_method: str
    timezone: str


class TodayPreferencesResponse(BaseModel):
    language: str
    notifications_on: bool


class PrayerResponse(BaseModel):
    key: str
    name: str
    time: str


class NextPrayerResponse(PrayerResponse):
    minutes_until: int
    is_tomorrow: bool


class TodayResponse(BaseModel):
    configured: bool
    profile: ProfileResponse
    local_now: str
    city: TodayCityResponse
    preferences: TodayPreferencesResponse
    prayers: list[PrayerResponse]
    next_prayer: NextPrayerResponse


_MINIAPP_PRAYERS = ("fajr", "sunrise", "dhuhr", "asr", "maghrib", "isha")
_MINIAPP_PRAYER_LABELS = {
    "fajr": "الفجر",
    "sunrise": "الشروق",
    "dhuhr": "الظهر",
    "asr": "العصر",
    "maghrib": "المغرب",
    "isha": "العشاء",
}


def _minutes_from_hhmm(value: str) -> int:
    hour, minute = map(int, value.split(":"))
    return hour * 60 + minute


def _city_response(city_name: str) -> CityResponse:
    coordinates = CityCoordinates.get_city_coords(city_name)
    if coordinates is None:
        raise ValueError(f"مدينة غير مدعومة: {city_name}")
    method = CityCoordinates.get_recommended_method(city_name)
    method_config = PrayerTimeCalculator.CALCULATION_METHODS.get(
        method, PrayerTimeCalculator.CALCULATION_METHODS["mwl"]
    )
    return CityResponse(
        name=city_name,
        country=coordinates.get("country", ""),
        method=method,
        method_name=str(method_config["name"]),
    )


def _today_payload(
    settings, identity: TelegramWebAppIdentity, user: UserSettings | None
) -> TodayResponse:
    city = user.city if user else settings.default_city
    coordinates = CityCoordinates.get_city_coords(city)
    if coordinates is None:
        logger.error("مدينة Mini App غير مدعومة: %s", city)
        raise HTTPException(status_code=500, detail="Prayer data is unavailable")

    method = (
        user.method
        if user
        else coordinates.get("method", settings.default_calculation_method)
    )
    asr_method = user.asr_method if user else settings.default_asr_method
    local_now = city_local_time(utc_now(), city, coordinates)
    calculator = PrayerTimeCalculator(
        latitude=coordinates["lat"],
        longitude=coordinates["lng"],
        timezone=coordinates["tz"],
        method=method,
        asr_method=asr_method,
        dst=coordinates.get("dst", False),
        city_name=city,
    )
    times = calculator.calculate_times(local_now)
    now_minutes = local_now.hour * 60 + local_now.minute
    next_key = "fajr"
    next_minutes = _minutes_from_hhmm(times[next_key]) + 24 * 60
    tomorrow = True
    for prayer in ("fajr", "dhuhr", "asr", "maghrib", "isha"):
        prayer_minutes = _minutes_from_hhmm(times[prayer])
        if prayer_minutes > now_minutes:
            next_key = prayer
            next_minutes = prayer_minutes
            tomorrow = False
            break

    return TodayResponse(
        configured=user is not None,
        profile=ProfileResponse(username=identity.username),
        local_now=local_now.isoformat(),
        city=TodayCityResponse(
            name=city,
            country=coordinates.get("country", ""),
            method=method,
            method_name=calculator.get_method_name(),
            asr_method=asr_method,
            timezone=str(local_now.tzinfo),
        ),
        preferences=TodayPreferencesResponse(
            language=user.language if user else "ar",
            notifications_on=user.notifications_on if user else True,
        ),
        prayers=[
            PrayerResponse(
                key=prayer, name=_MINIAPP_PRAYER_LABELS[prayer], time=times[prayer]
            )
            for prayer in _MINIAPP_PRAYERS
        ],
        next_prayer=NextPrayerResponse(
            key=next_key,
            name=_MINIAPP_PRAYER_LABELS[next_key],
            time=times[next_key],
            minutes_until=next_minutes - now_minutes,
            is_tomorrow=tomorrow,
        ),
    )


def create_miniapp_api(settings, deps) -> FastAPI:
    """إنشاء API لا يقبل أي طلب قبل التحقق من Telegram initData."""
    app = FastAPI(
        title="Islamic Unified Bot Mini App API", docs_url=None, redoc_url=None
    )
    if settings.miniapp_allowed_origin:
        origin_host = urlparse(settings.miniapp_allowed_origin).netloc
        app.add_middleware(TrustedHostMiddleware, allowed_hosts=[origin_host])
        app.add_middleware(
            CORSMiddleware,
            allow_origins=[settings.miniapp_allowed_origin],
            allow_credentials=False,
            allow_methods=["GET", "PUT"],
            allow_headers=["X-Telegram-Init-Data", "Content-Type"],
            max_age=600,
        )

    @app.middleware("http")
    async def add_security_headers(request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Cache-Control"] = "no-store"
        return response

    async def identity_from_header(
        x_telegram_init_data: str | None = Header(default=None),
    ) -> TelegramWebAppIdentity:
        if not x_telegram_init_data:
            log_event(logger, "miniapp_auth_rejected", reason="missing_init_data")
            raise HTTPException(status_code=401, detail="Telegram initData is required")
        try:
            return validate_init_data(
                x_telegram_init_data,
                settings.bot_token,
                max_age_seconds=settings.miniapp_init_data_max_age,
            )
        except InitDataValidationError as exc:
            log_event(logger, "miniapp_auth_rejected", reason="invalid_init_data")
            raise HTTPException(
                status_code=401, detail="Invalid Telegram session"
            ) from exc

    @app.get("/healthz")
    async def healthz():
        return {"status": "ok"}

    @app.get("/readyz")
    async def readyz():
        """تحقق جاهزية داخلي بلا إفصاح عن تفاصيل البنية أو المستخدمين."""
        try:
            await deps.db.fetchone("SELECT 1")
            delivery = await deps.sent_repo.delivery_metrics()
        except (RuntimeError, aiosqlite.Error):
            log_event(logger, "miniapp_readiness_failed", level=logging.ERROR)
            raise HTTPException(status_code=503, detail="Service unavailable") from None
        return {"status": "ready", "delivery": delivery}

    @app.get("/api/miniapp/preferences", response_model=PreferencesResponse)
    async def get_preferences(
        x_telegram_init_data: str | None = Header(default=None),
    ):
        identity = await identity_from_header(x_telegram_init_data)
        user = await deps.user_repo.get(identity.user_id)
        if user is None:
            log_event(logger, "miniapp_preferences_read", configured=False)
            return PreferencesResponse(configured=False)
        log_event(logger, "miniapp_preferences_read", configured=True)
        return PreferencesResponse(
            configured=True,
            city=user.city,
            language=user.language,
            notifications_on=user.notifications_on,
        )

    @app.get("/api/miniapp/cities", response_model=CitiesResponse)
    async def get_cities(
        query: str = Query(default="", max_length=80),
        x_telegram_init_data: str | None = Header(default=None),
    ):
        """أعد المدن المحلية المدعومة فقط لاختيار Mini App."""
        await identity_from_header(x_telegram_init_data)
        city_names = (
            CityCoordinates.search_cities(query)
            if query.strip()
            else sorted(CityCoordinates.get_all_cities())
        )
        cities = [_city_response(city_name) for city_name in city_names[:100]]
        return CitiesResponse(query=query, cities=cities)

    @app.get("/api/miniapp/today", response_model=TodayResponse)
    async def get_today(x_telegram_init_data: str | None = Header(default=None)):
        """أعد بيانات اليوم المحسوبة خادميًا للمستخدم الموثق فقط."""
        identity = await identity_from_header(x_telegram_init_data)
        user = await deps.user_repo.get(identity.user_id)
        payload = _today_payload(settings, identity, user)
        log_event(
            logger,
            "miniapp_today_read",
            configured=user is not None,
            city=payload.city.name,
        )
        return payload

    @app.put("/api/miniapp/preferences", response_model=SaveResponse)
    async def save_preferences(
        body: PreferencesInput,
        x_telegram_init_data: str | None = Header(default=None),
    ):
        identity = await identity_from_header(x_telegram_init_data)
        if CityCoordinates.get_city_coords(body.city) is None:
            log_event(logger, "miniapp_preferences_rejected", reason="unsupported_city")
            raise HTTPException(status_code=422, detail="Unsupported city")
        existing = await deps.user_repo.get(identity.user_id)
        if existing is None:
            await deps.user_repo.upsert(
                UserSettings(
                    user_id=identity.user_id,
                    city=body.city,
                    method=settings.default_calculation_method,
                    asr_method=settings.default_asr_method,
                    timezone=settings.default_timezone,
                    language=body.language,
                    notifications_on=body.notifications_on,
                )
            )
        else:
            await deps.user_repo.update_partial(
                identity.user_id,
                city=body.city,
                language=body.language,
                notifications_on=body.notifications_on,
            )
        log_event(
            logger,
            "miniapp_preferences_saved",
            created=existing is None,
            language=body.language,
            notifications_enabled=body.notifications_on,
        )
        return SaveResponse(saved=True)

    return app
