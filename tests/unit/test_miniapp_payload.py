import json

import pytest

from bot.handlers.miniapp import validate_miniapp_payload
from bot.i18n.messages import message_for


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


def test_message_for_uses_selected_language_and_safe_fallback():
    assert message_for("en", "miniapp_saved").startswith("Your Mihrab")
    assert message_for("unknown", "miniapp_saved").startswith("تم حفظ")


@pytest.mark.parametrize(
    "payload",
    [
        {"source": "other", "city": "الرياض", "language": "ar", "notifications": True},
        {
            "source": "miniapp",
            "city": "unknown",
            "language": "ar",
            "notifications": True,
        },
        {
            "source": "miniapp",
            "city": "الرياض",
            "language": "fr",
            "notifications": True,
        },
        {
            "source": "miniapp",
            "city": "الرياض",
            "language": "ar",
            "notifications": "yes",
        },
    ],
)
def test_validate_miniapp_payload_rejects_invalid_data(payload):
    with pytest.raises(ValueError):
        validate_miniapp_payload(json.dumps(payload))
