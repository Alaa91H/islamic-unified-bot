import json

import pytest

from bot.handlers.miniapp import validate_miniapp_payload


def test_validate_miniapp_payload_returns_only_allowed_preferences():
    payload = json.dumps(
        {
            "source": "miniapp",
            "city": "الرياض",
            "language": "ar",
            "notifications": True,
            "unexpected": "discarded",
        }
    )

    assert validate_miniapp_payload(payload) == {
        "city": "الرياض",
        "language": "ar",
        "notifications_on": True,
    }


@pytest.mark.parametrize(
    "payload",
    [
        {"source": "other", "city": "الرياض", "language": "ar", "notifications": True},
        {"source": "miniapp", "city": "unknown", "language": "ar", "notifications": True},
        {"source": "miniapp", "city": "الرياض", "language": "fr", "notifications": True},
        {"source": "miniapp", "city": "الرياض", "language": "ar", "notifications": "yes"},
    ],
)
def test_validate_miniapp_payload_rejects_invalid_data(payload):
    with pytest.raises(ValueError):
        validate_miniapp_payload(json.dumps(payload))
