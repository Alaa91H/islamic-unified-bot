"""تحقق خادمي من Telegram WebApp initData قبل استعمال هوية المستخدم."""

from __future__ import annotations

import hashlib
import hmac
import json
import time
from dataclasses import dataclass
from urllib.parse import parse_qsl


class InitDataValidationError(ValueError):
    """تشير إلى بيانات Mini App مفقودة أو مزورة أو منتهية."""


@dataclass(frozen=True)
class TelegramWebAppIdentity:
    user_id: int
    username: str | None
    auth_date: int


def validate_init_data(
    init_data: str,
    bot_token: str,
    *,
    max_age_seconds: int = 3600,
    now: int | None = None,
) -> TelegramWebAppIdentity:
    """تحقق من HMAC ومدة صلاحية ``initData`` حسب خوارزمية Telegram الرسمية."""
    values = dict(parse_qsl(init_data, keep_blank_values=True))
    received_hash = values.pop("hash", None)
    if not received_hash:
        raise InitDataValidationError("Telegram initData is missing hash")

    data_check_string = "\n".join(
        f"{key}={value}" for key, value in sorted(values.items())
    )
    secret_key = hmac.new(
        b"WebAppData", bot_token.encode("utf-8"), hashlib.sha256
    ).digest()
    expected_hash = hmac.new(
        secret_key, data_check_string.encode("utf-8"), hashlib.sha256
    ).hexdigest()
    if not hmac.compare_digest(expected_hash, received_hash):
        raise InitDataValidationError("Telegram initData signature is invalid")

    try:
        auth_date = int(values["auth_date"])
        user = json.loads(values["user"])
        user_id = int(user["id"])
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise InitDataValidationError("Telegram initData identity is invalid") from exc

    current_time = int(time.time()) if now is None else now
    if auth_date > current_time or current_time - auth_date > max_age_seconds:
        raise InitDataValidationError("Telegram initData has expired")
    return TelegramWebAppIdentity(
        user_id=user_id,
        username=user.get("username"),
        auth_date=auth_date,
    )
