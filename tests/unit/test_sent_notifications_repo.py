from datetime import date

import pytest


@pytest.fixture
async def repo(tmp_path):
    from bot.db.connection import Database
    from bot.db.repositories.sent_notifications import SentNotificationsRepo

    db = Database(str(tmp_path / "t.db"))
    await db.connect()
    yield SentNotificationsRepo(db)
    await db.close()


@pytest.mark.asyncio
async def test_mark_sent_returns_true_first_time_false_second(repo):
    today = date.today().isoformat()
    assert await repo.mark_sent(1, "user", "fajr", today) is True
    assert await repo.mark_sent(1, "user", "fajr", today) is False


@pytest.mark.asyncio
async def test_already_sent_true_after_marking(repo):
    today = date.today().isoformat()
    assert await repo.already_sent(1, "user", "fajr", today) is False
    await repo.mark_sent(1, "user", "fajr", today)
    assert await repo.already_sent(1, "user", "fajr", today) is True


@pytest.mark.asyncio
async def test_prelude_key_distinct_from_prayer(repo):
    today = date.today().isoformat()
    await repo.mark_sent(1, "user", "prelude_fajr", today)
    # صلاة الفجر نفسها لا تُعتبر مُرسلة
    assert await repo.already_sent(1, "user", "fajr", today) is False


@pytest.mark.asyncio
async def test_different_dates_are_independent(repo):
    await repo.mark_sent(1, "user", "fajr", "2026-06-18")
    # يوم مختلف = لم تُرسل
    assert await repo.already_sent(1, "user", "fajr", "2026-06-19") is False


@pytest.mark.asyncio
async def test_user_and_group_targets_independent(repo):
    today = date.today().isoformat()
    await repo.mark_sent(1, "user", "fajr", today)
    # نفس الرقم لكن كمجموعة = هدف مختلف
    assert await repo.already_sent(1, "group", "fajr", today) is False
    assert await repo.mark_sent(1, "group", "fajr", today) is True


@pytest.mark.asyncio
async def test_concurrent_mark_sent_is_safe(repo):
    """إدراجان متزامنان لنفس المفتاح: أحدهما ينجح والآخر يُرجع False."""
    import asyncio

    today = date.today().isoformat()
    results = await asyncio.gather(
        repo.mark_sent(7, "user", "dhuhr", today),
        repo.mark_sent(7, "user", "dhuhr", today),
    )
    assert results.count(True) == 1
    assert results.count(False) == 1


@pytest.mark.asyncio
async def test_failed_delivery_waits_for_scheduled_retry(repo):
    key = (9, "user", "isha", "2026-08-22")
    assert await repo.claim_delivery(*key) is True
    await repo.fail_delivery(*key, RuntimeError("temporary gateway error"))

    assert await repo.claim_delivery(*key) is False


@pytest.mark.asyncio
async def test_permanent_failure_is_not_reclaimed(repo):
    key = (10, "user", "maghrib", "2026-08-22")
    assert await repo.claim_delivery(*key) is True
    await repo.fail_delivery(*key, RuntimeError("chat blocked bot"), retryable=False)

    assert await repo.claim_delivery(*key) is False


@pytest.mark.asyncio
async def test_delivery_metrics_report_all_states(repo):
    await repo.mark_sent(20, "user", "fajr", "2026-08-22")
    assert await repo.claim_delivery(21, "user", "dhuhr", "2026-08-22") is True
    assert await repo.claim_delivery(22, "user", "asr", "2026-08-22") is True
    await repo.fail_delivery(22, "user", "asr", "2026-08-22", RuntimeError("error"))

    assert await repo.delivery_metrics() == {"processing": 1, "sent": 1, "failed": 1}
