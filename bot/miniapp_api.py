"""واجهة HTTP اختيارية وآمنة لبيانات Telegram Mini App الحية."""

from __future__ import annotations

import logging

from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from bot.db.repositories.user_settings import UserSettings
from bot.miniapp_auth import (
    InitDataValidationError,
    TelegramWebAppIdentity,
    validate_init_data,
)
from bot.observability import log_event
from bot.prayer.calculator import CityCoordinates

logger = logging.getLogger(__name__)


class PreferencesInput(BaseModel):
    city: str = Field(min_length=1, max_length=120)
    language: str = Field(pattern="^(ar|en)$")
    notifications_on: bool


def create_miniapp_api(settings, deps) -> FastAPI:
    """إنشاء API لا يقبل أي طلب قبل التحقق من Telegram initData."""
    app = FastAPI(
        title="Islamic Unified Bot Mini App API", docs_url=None, redoc_url=None
    )
    if settings.miniapp_allowed_origin:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=[settings.miniapp_allowed_origin],
            allow_credentials=False,
            allow_methods=["GET", "PUT"],
            allow_headers=["X-Telegram-Init-Data", "Content-Type"],
        )

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
        except Exception:
            log_event(logger, "miniapp_readiness_failed", level=logging.ERROR)
            raise HTTPException(status_code=503, detail="Service unavailable") from None
        return {"status": "ready", "delivery": delivery}

    @app.get("/api/miniapp/preferences")
    async def get_preferences(
        x_telegram_init_data: str | None = Header(default=None),
    ):
        identity = await identity_from_header(x_telegram_init_data)
        user = await deps.user_repo.get(identity.user_id)
        if user is None:
            log_event(logger, "miniapp_preferences_read", configured=False)
            return {"configured": False}
        log_event(logger, "miniapp_preferences_read", configured=True)
        return {
            "configured": True,
            "city": user.city,
            "language": user.language,
            "notifications_on": user.notifications_on,
        }

    @app.put("/api/miniapp/preferences")
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
        return {"saved": True}

    return app
