import hashlib
import hmac
import json
import time
from types import SimpleNamespace
from urllib.parse import urlencode
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

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
    settings = SimpleNamespace(
        bot_token="test-token",
        miniapp_init_data_max_age=3600,
        miniapp_allowed_origin="",
        default_calculation_method="mwl",
        default_asr_method="standard",
        default_timezone=3,
    )
    app = create_miniapp_api(settings, SimpleNamespace(user_repo=repo))
    client = TestClient(app)

    assert client.get("/api/miniapp/preferences").status_code == 401
    response = client.put(
        "/api/miniapp/preferences",
        headers={"X-Telegram-Init-Data": signed_init_data("test-token")},
        json={"city": "الرياض", "language": "ar", "notifications_on": True},
    )

    assert response.status_code == 200
    assert response.json() == {"saved": True}
    assert repo.upsert.await_args.args[0].user_id == 12345
