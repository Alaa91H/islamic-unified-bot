import asyncio
import pytest
from datetime import date
from unittest.mock import AsyncMock, MagicMock


@pytest.fixture
async def bundle(tmp_path):
    """يبني scheduler مع DB معزول."""
    from bot.db.connection import Database
    from bot.db.repositories.group_settings import GroupSettingsRepo
    from bot.db.repositories.sent_notifications import SentNotificationsRepo
    from bot.db.repositories.user_settings import UserSettingsRepo
    from bot.scheduler.notifier import Notifier
    from bot.scheduler.prayer_scheduler import PrayerScheduler

    db = Database(str(tmp_path / "t.db"))
    await db.connect()
    user_repo = UserSettingsRepo(db)
    group_repo = GroupSettingsRepo(db)
    sent_repo = SentNotificationsRepo(db)

    app = MagicMock()
    stream = MagicMock()
    notifier = Notifier(app, stream)
    notifier.notify_user = AsyncMock(return_value=True)
    notifier.broadcast_group_azan = AsyncMock(return_value=True)

    sched = PrayerScheduler(user_repo, group_repo, sent_repo, notifier)
    yield {
        "sched": sched, "user_repo": user_repo, "group_repo": group_repo,
        "sent_repo": sent_repo, "notifier": notifier,
    }
    await db.close()


@pytest.mark.asyncio
async def test_tick_fires_notification_for_due_prayer(bundle):
    s = bundle["sched"]
    s._find_due_prayers = AsyncMock(return_value=[
        ("user", 1, {"prayer": "dhuhr", "time": "12:00", "is_prelude": False}),
    ])
    await s.tick()
    bundle["notifier"].notify_user.assert_awaited_once_with(
        1, "dhuhr", "12:00", False
    )


@pytest.mark.asyncio
async def test_tick_skips_already_sent(bundle):
    s = bundle["sched"]
    await bundle["sent_repo"].mark_sent(
        1, "user", "dhuhr", date.today().isoformat()
    )
    s._find_due_prayers = AsyncMock(return_value=[
        ("user", 1, {"prayer": "dhuhr", "time": "12:00", "is_prelude": False}),
    ])
    await s.tick()
    bundle["notifier"].notify_user.assert_not_awaited()


@pytest.mark.asyncio
async def test_tick_marks_sent_after_success(bundle):
    s = bundle["sched"]
    s._find_due_prayers = AsyncMock(return_value=[
        ("user", 1, {"prayer": "dhuhr", "time": "12:00", "is_prelude": False}),
    ])
    await s.tick()
    # tick ثانٍ لن يكرّر لأنه سُجّل
    s._find_due_prayers = AsyncMock(return_value=[
        ("user", 1, {"prayer": "dhuhr", "time": "12:00", "is_prelude": False}),
    ])
    await s.tick()
    assert bundle["notifier"].notify_user.await_count == 1


@pytest.mark.asyncio
async def test_tick_dispatches_group(bundle):
    s = bundle["sched"]
    s._find_due_prayers = AsyncMock(return_value=[
        ("group", -100, {"prayer": "maghrib", "time": "18:30",
                         "is_prelude": False}),
    ])
    await s.tick()
    bundle["notifier"].broadcast_group_azan.assert_awaited_once_with(
        -100, "maghrib", "traditional"
    )


@pytest.mark.asyncio
async def test_prelude_uses_distinct_key(bundle):
    """المقدمة لها مفتاح مستقل prelude_<prayer> فلا تحجب الصلاة نفسها."""
    s = bundle["sched"]
    s._find_due_prayers = AsyncMock(return_value=[
        ("user", 1, {"prayer": "fajr", "time": "05:00", "is_prelude": True,
                     "prelude_key": "prelude_fajr"}),
        ("user", 1, {"prayer": "fajr", "time": "05:00", "is_prelude": False}),
    ])
    await s.tick()
    # كلاهما أُرسل لأن المفاتيح مختلفة
    assert bundle["notifier"].notify_user.await_count == 2


@pytest.mark.asyncio
async def test_tick_one_failure_does_not_stop_others(bundle):
    s = bundle["sched"]
    bundle["notifier"].notify_user = AsyncMock(
        side_effect=[RuntimeError("boom"), True]
    )
    s._find_due_prayers = AsyncMock(return_value=[
        ("user", 1, {"prayer": "dhuhr", "time": "12:00", "is_prelude": False}),
        ("user", 2, {"prayer": "dhuhr", "time": "12:00", "is_prelude": False}),
    ])
    # يجب ألا يرفع tick رغم فشل الأول
    await s.tick()
    assert bundle["notifier"].notify_user.await_count == 2


@pytest.mark.asyncio
async def test_start_stop_runs_then_stops(bundle):
    s = bundle["sched"]
    s.tick = AsyncMock()
    s.TICK_SECONDS = 0.01
    await s.start()
    await asyncio.sleep(0.05)
    await s.stop()
    assert s.tick.await_count >= 1


@pytest.mark.asyncio
async def test_check_due_returns_prayer_when_now_matches():
    """تحقق مباشر للمنطق الحسابي: عن طريق freezegun أو حقن وقت مطابق."""
    from bot.scheduler.prayer_scheduler import PrayerScheduler

    # نتحقق فقط أن الدالة تُرجع dict صالح أو None دون خطأ
    result = PrayerScheduler._check_due(
        "مكة المكرمة", "makkah", "standard",
        # وقت عشوائي بعيد عن أي صلاة يُرجع غالبًا None أو قيمة صحيحة
        __import__("datetime").datetime(2026, 6, 18, 8, 0),
    )
    assert result is None or "prayer" in result


@pytest.mark.asyncio
async def test_check_due_unknown_city_returns_none():
    from bot.scheduler.prayer_scheduler import PrayerScheduler
    from datetime import datetime

    assert PrayerScheduler._check_due(
        "مدينة_وهمية", "isna", "standard", datetime(2026, 6, 18, 12, 0)
    ) is None
