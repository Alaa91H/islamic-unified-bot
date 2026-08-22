from datetime import UTC, datetime

import pytest


@pytest.mark.unit
def test_city_local_time_uses_iana_daylight_saving_for_london():
    from bot.time_utils import city_local_time

    local_time = city_local_time(
        datetime(2026, 7, 1, 12, 0, tzinfo=UTC), "London", {"tz": 0, "dst": False}
    )

    assert local_time.tzinfo is not None
    assert local_time.hour == 13
    assert local_time.utcoffset().total_seconds() == 3600


@pytest.mark.unit
def test_city_local_time_uses_expected_makkah_zone():
    from bot.time_utils import city_local_time

    local_time = city_local_time(
        datetime(2026, 1, 1, 12, 0, tzinfo=UTC), "مكة المكرمة", {"tz": 3}
    )

    assert local_time.hour == 15
    assert local_time.utcoffset().total_seconds() == 3 * 3600


@pytest.mark.asyncio
@pytest.mark.unit
async def test_delivery_claim_is_atomic_and_retriable(tmp_path):
    from bot.db.connection import Database
    from bot.db.repositories.sent_notifications import SentNotificationsRepo

    db = Database(str(tmp_path / "delivery.db"))
    await db.connect()
    repo = SentNotificationsRepo(db)

    assert await repo.claim_delivery(7, "user", "fajr", "2026-07-01") is True
    assert await repo.claim_delivery(7, "user", "fajr", "2026-07-01") is False

    await repo.fail_delivery(
        7, "user", "fajr", "2026-07-01", RuntimeError("gateway unavailable")
    )
    assert await repo.claim_delivery(7, "user", "fajr", "2026-07-01") is False
    await db.execute(
        """UPDATE sent_notifications
           SET next_retry_at=datetime('now', '-1 second')
           WHERE target_id=? AND target_type=? AND prayer=? AND prayer_date=?""",
        (7, "user", "fajr", "2026-07-01"),
    )
    assert await repo.claim_delivery(7, "user", "fajr", "2026-07-01") is True

    await repo.complete_delivery(7, "user", "fajr", "2026-07-01")
    assert await repo.already_sent(7, "user", "fajr", "2026-07-01") is True
    assert await repo.claim_delivery(7, "user", "fajr", "2026-07-01") is False

    await db.close()
