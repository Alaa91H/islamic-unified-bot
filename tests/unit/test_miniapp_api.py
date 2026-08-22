import hashlib
import hmac
import json
import time
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from urllib.parse import urlencode

import aiosqlite
import pytest
from fastapi.testclient import TestClient

from bot.db.repositories.user_settings import UserSettings
from bot.miniapp_api import create_miniapp_api
from bot.miniapp_auth import InitDataValidationError, validate_init_data


def signed_init_data(token: str, **extra) -> str:
    values = {
        "auth_date": str(int(time.time())),
        "query_id": "test-query",
        "user": json.dumps({"id": 12345, "username": "tester"}, separators=(",", ":")),
        **extra,
    }
    check = "\n".join(f"{key}={value}" for key, value in sorted(values.items()))
    secret = hmac.new(b"WebAppData", token.encode(), hashlib.sha256).digest()
    values["hash"] = hmac.new(secret, check.encode(), hashlib.sha256).hexdigest()
    return urlencode(values)


def test_validate_init_data_accepts_valid_telegram_signature():
    identity = validate_init_data(signed_init_data("test-token"), "test-token")
    assert identity.user_id == 12345
    assert identity.username == "tester"


def test_validate_init_data_rejects_tampering_and_expiry():
    with pytest.raises(InitDataValidationError):
        validate_init_data(
            signed_init_data("test-token", query_id="tampered"), "other-token"
        )
    expired = signed_init_data("test-token", auth_date="1")
    with pytest.raises(InitDataValidationError):
        validate_init_data(expired, "test-token", now=10_000)


def test_preferences_api_requires_init_data_and_saves_verified_user():
    repo = SimpleNamespace(get=AsyncMock(return_value=None), upsert=AsyncMock())
    db = SimpleNamespace(fetchone=AsyncMock(return_value=(1,)))
    sent_repo = SimpleNamespace(
        delivery_metrics=AsyncMock(
            return_value={"processing": 1, "sent": 2, "failed": 0}
        )
    )
    settings = SimpleNamespace(
        bot_token="test-token",
        miniapp_init_data_max_age=3600,
        miniapp_allowed_origin="",
        default_calculation_method="mwl",
        default_asr_method="standard",
        default_timezone=3,
    )
    app = create_miniapp_api(
        settings, SimpleNamespace(user_repo=repo, db=db, sent_repo=sent_repo)
    )
    client = TestClient(app)

    readiness = client.get("/readyz")
    assert readiness.status_code == 200
    assert readiness.json() == {
        "status": "ready",
        "delivery": {"processing": 1, "sent": 2, "failed": 0},
    }
    assert client.get("/api/miniapp/preferences").status_code == 401
    response = client.put(
        "/api/miniapp/preferences",
        headers={"X-Telegram-Init-Data": signed_init_data("test-token")},
        json={"city": "الرياض", "language": "ar", "notifications_on": True},
    )

    assert response.status_code == 200
    assert response.json() == {"saved": True}
    assert repo.upsert.await_args.args[0].user_id == 12345


def test_preferences_api_applies_cors_security_headers_and_no_store():
    repo = SimpleNamespace(get=AsyncMock(return_value=None), upsert=AsyncMock())
    db = SimpleNamespace(fetchone=AsyncMock(return_value=(1,)))
    sent_repo = SimpleNamespace(delivery_metrics=AsyncMock(return_value={}))
    settings = SimpleNamespace(
        bot_token="test-token",
        miniapp_init_data_max_age=3600,
        miniapp_allowed_origin="https://miniapp.example.com",
        default_calculation_method="mwl",
        default_asr_method="standard",
        default_timezone=3,
    )
    client = TestClient(
        create_miniapp_api(
            settings, SimpleNamespace(user_repo=repo, db=db, sent_repo=sent_repo)
        )
    )

    response = client.options(
        "/api/miniapp/preferences",
        headers={
            "Origin": "https://miniapp.example.com",
            "Access-Control-Request-Method": "PUT",
        },
    )

    assert response.status_code == 200
    assert (
        response.headers["access-control-allow-origin"] == "https://miniapp.example.com"
    )
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["cache-control"] == "no-store"


def test_readyz_hides_operational_database_errors():
    repo = SimpleNamespace(get=AsyncMock(return_value=None), upsert=AsyncMock())
    db = SimpleNamespace(fetchone=AsyncMock(side_effect=aiosqlite.OperationalError()))
    sent_repo = SimpleNamespace(delivery_metrics=AsyncMock(return_value={}))
    settings = SimpleNamespace(
        bot_token="test-token",
        miniapp_init_data_max_age=3600,
        miniapp_allowed_origin="",
        default_calculation_method="mwl",
        default_asr_method="standard",
        default_timezone=3,
    )
    client = TestClient(
        create_miniapp_api(
            settings, SimpleNamespace(user_repo=repo, db=db, sent_repo=sent_repo)
        )
    )

    response = client.get("/readyz")

    assert response.status_code == 503
    assert response.json() == {"detail": "Service unavailable"}


@patch("bot.miniapp_api.utc_now", return_value=datetime(2026, 8, 22, 9, tzinfo=UTC))
def test_today_api_returns_city_local_prayers_and_verified_preferences(_utc_now):
    repo = SimpleNamespace(
        get=AsyncMock(
            return_value=UserSettings(
                user_id=12345,
                city="الرياض",
                method="makkah",
                asr_method="standard",
                timezone=3,
                language="en",
                notifications_on=False,
            )
        ),
        upsert=AsyncMock(),
    )
    settings = SimpleNamespace(
        bot_token="test-token",
        miniapp_init_data_max_age=3600,
        miniapp_allowed_origin="",
        default_city="مكة المكرمة",
        default_calculation_method="mwl",
        default_asr_method="standard",
        default_timezone=3,
    )
    client = TestClient(
        create_miniapp_api(
            settings,
            SimpleNamespace(
                user_repo=repo,
                db=SimpleNamespace(fetchone=AsyncMock(return_value=(1,))),
                sent_repo=SimpleNamespace(delivery_metrics=AsyncMock(return_value={})),
            ),
        )
    )

    assert client.get("/api/miniapp/today").status_code == 401
    response = client.get(
        "/api/miniapp/today",
        headers={"X-Telegram-Init-Data": signed_init_data("test-token")},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["configured"] is True
    assert body["city"]["name"] == "الرياض"
    assert body["preferences"] == {"language": "en", "notifications_on": False}
    assert [prayer["key"] for prayer in body["prayers"]] == [
        "fajr",
        "sunrise",
        "dhuhr",
        "asr",
        "maghrib",
        "isha",
    ]
    assert body["next_prayer"]["minutes_until"] > 0


@patch("bot.miniapp_api.utc_now", return_value=datetime(2026, 8, 22, 9, tzinfo=UTC))
def test_today_api_uses_configured_defaults_for_new_user(_utc_now):
    repo = SimpleNamespace(get=AsyncMock(return_value=None), upsert=AsyncMock())
    settings = SimpleNamespace(
        bot_token="test-token",
        miniapp_init_data_max_age=3600,
        miniapp_allowed_origin="",
        default_city="مكة المكرمة",
        default_calculation_method="mwl",
        default_asr_method="standard",
        default_timezone=3,
    )
    client = TestClient(
        create_miniapp_api(
            settings,
            SimpleNamespace(
                user_repo=repo,
                db=SimpleNamespace(fetchone=AsyncMock(return_value=(1,))),
                sent_repo=SimpleNamespace(delivery_metrics=AsyncMock(return_value={})),
            ),
        )
    )

    response = client.get(
        "/api/miniapp/today",
        headers={"X-Telegram-Init-Data": signed_init_data("test-token")},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["configured"] is False
    assert body["city"]["name"] == "مكة المكرمة"
    assert body["preferences"] == {"language": "ar", "notifications_on": True}


def test_cities_api_returns_supported_cities_only_to_verified_user():
    repo = SimpleNamespace(get=AsyncMock(return_value=None), upsert=AsyncMock())
    settings = SimpleNamespace(
        bot_token="test-token",
        miniapp_init_data_max_age=3600,
        miniapp_allowed_origin="",
        default_city="مكة المكرمة",
        default_calculation_method="mwl",
        default_asr_method="standard",
        default_timezone=3,
    )
    client = TestClient(
        create_miniapp_api(
            settings,
            SimpleNamespace(
                user_repo=repo,
                db=SimpleNamespace(fetchone=AsyncMock(return_value=(1,))),
                sent_repo=SimpleNamespace(delivery_metrics=AsyncMock(return_value={})),
            ),
        )
    )

    assert client.get("/api/miniapp/cities").status_code == 401
    response = client.get(
        "/api/miniapp/cities?query=الرياض",
        headers={"X-Telegram-Init-Data": signed_init_data("test-token")},
    )

    assert response.status_code == 200
    assert response.json() == {
        "query": "الرياض",
        "cities": [
            {
                "name": "الرياض",
                "country": "السعودية",
                "method": "makkah",
                "method_name": "أم القرى (Umm Al-Qura University)",
            }
        ],
    }
