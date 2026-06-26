import pytest
from unittest.mock import AsyncMock, MagicMock, patch


def test_now_hhmm_returns_string():
    from bot.scheduler.adhkar_scheduler import _now_hhmm

    result = _now_hhmm()
    assert isinstance(result, str)
    assert len(result) == 5
    assert ":" in result


def test_today_str_returns_string():
    from bot.scheduler.adhkar_scheduler import _today_str

    result = _today_str()
    assert isinstance(result, str)
    assert len(result) == 10


@patch("bot.scheduler.adhkar_scheduler.datetime")
def test_is_friday_returns_true_on_friday(mock_dt):
    from bot.scheduler.adhkar_scheduler import _is_friday

    mock_dt.now.return_value.weekday.return_value = 4
    assert _is_friday() is True


@patch("bot.scheduler.adhkar_scheduler.datetime")
def test_is_friday_returns_false_other_days(mock_dt):
    from bot.scheduler.adhkar_scheduler import _is_friday

    mock_dt.now.return_value.weekday.return_value = 0
    assert _is_friday() is False


@patch("bot.scheduler.adhkar_scheduler.random.choice")
def test_pick_random_item_returns_item(mock_choice):
    from bot.scheduler.adhkar_scheduler import _pick_random_item
    from bot.data.adhkar import ADHKAR

    mock_choice.side_effect = lambda x: x[0] if isinstance(x, list) else x
    category, item = _pick_random_item(["morning"])
    assert category is not None
    assert item is not None


def test_pick_random_item_empty_category():
    from bot.scheduler.adhkar_scheduler import _pick_random_item

    with patch("bot.scheduler.adhkar_scheduler.ADHKAR", {"empty_cat": []}):
        category, item = _pick_random_item(["empty_cat"])
        assert category is None
        assert item is None


def test_format_adhkar_returns_correct_format():
    from bot.scheduler.adhkar_scheduler import _format_adhkar

    item = {"title": "Test Title", "text": "Test text content", "benefit": "Test benefit"}
    result = _format_adhkar(item)
    assert "Test Title" in result
    assert "Test text content" in result
    assert "Test benefit" in result


@pytest.mark.asyncio
async def test_scheduler_start_creates_task():
    from bot.scheduler.adhkar_scheduler import AdhkarScheduler

    repo = MagicMock()
    app = MagicMock()
    scheduler = AdhkarScheduler(repo, app, tick_seconds=9999)
    assert scheduler._task is None

    await scheduler.start()
    assert scheduler._task is not None
    assert scheduler._running is True

    await scheduler.stop()
    assert scheduler._running is False


@pytest.mark.asyncio
async def test_scheduler_start_is_idempotent():
    from bot.scheduler.adhkar_scheduler import AdhkarScheduler

    repo = MagicMock()
    app = MagicMock()
    scheduler = AdhkarScheduler(repo, app, tick_seconds=9999)

    await scheduler.start()
    task = scheduler._task
    await scheduler.start()
    assert scheduler._task is task

    await scheduler.stop()


@pytest.mark.asyncio
async def test_scheduler_stop_without_start():
    from bot.scheduler.adhkar_scheduler import AdhkarScheduler

    repo = MagicMock()
    app = MagicMock()
    scheduler = AdhkarScheduler(repo, app)
    await scheduler.stop()


@pytest.mark.asyncio
async def test_tick_processes_all_groups():
    from bot.scheduler.adhkar_scheduler import AdhkarScheduler

    settings = MagicMock()
    settings.chat_id = -100123
    settings.interval_enabled = True
    settings.morning_enabled = False
    settings.evening_enabled = False
    settings.friday_enabled = False
    settings.interval_minutes = 10
    settings.last_sent_at = None

    repo = AsyncMock()
    repo.list_all = AsyncMock(return_value=[settings])
    repo.update_partial = AsyncMock()

    app = MagicMock()
    scheduler = AdhkarScheduler(repo, app, tick_seconds=9999)
    scheduler._app.send_message = AsyncMock()

    with patch("bot.scheduler.adhkar_scheduler._pick_random_item") as mock_pick:
        mock_pick.return_value = ("morning", {"title": "Test", "text": "Test", "benefit": "Test"})
        await scheduler.tick()
        repo.update_partial.assert_called_once()


@pytest.mark.asyncio
async def test_tick_skips_disabled_group():
    from bot.scheduler.adhkar_scheduler import AdhkarScheduler

    settings = MagicMock()
    settings.chat_id = -100123
    settings.interval_enabled = False
    settings.morning_enabled = False
    settings.evening_enabled = False
    settings.friday_enabled = False

    repo = AsyncMock()
    repo.list_all = AsyncMock(return_value=[settings])

    app = MagicMock()
    scheduler = AdhkarScheduler(repo, app, tick_seconds=9999)

    await scheduler.tick()
    repo.update_partial.assert_not_called()


@pytest.mark.asyncio
async def test_send_adhkar_sends_message():
    from bot.scheduler.adhkar_scheduler import AdhkarScheduler

    repo = MagicMock()
    app = MagicMock()
    app.send_message = AsyncMock()

    scheduler = AdhkarScheduler(repo, app, tick_seconds=9999)
    await scheduler._send_adhkar(-100, ["morning"], "🌅 **Header**")

    app.send_message.assert_called_once()


@pytest.mark.asyncio
async def test_send_adhkar_without_header():
    from bot.scheduler.adhkar_scheduler import AdhkarScheduler

    repo = MagicMock()
    app = MagicMock()
    app.send_message = AsyncMock()

    scheduler = AdhkarScheduler(repo, app, tick_seconds=9999)
    with patch("bot.scheduler.adhkar_scheduler._pick_random_item") as mock_pick:
        mock_pick.return_value = ("morning", {"title": "Test", "text": "Body", "benefit": "B"})
        await scheduler._send_adhkar(-100, ["morning"])

    app.send_message.assert_called_once()


@pytest.mark.asyncio
async def test_already_sent_today():
    from bot.scheduler.adhkar_scheduler import AdhkarScheduler

    repo = MagicMock()
    repo._db = AsyncMock()
    repo._db.fetchone = AsyncMock(return_value=None)

    app = MagicMock()
    scheduler = AdhkarScheduler(repo, app, tick_seconds=9999)

    result = await scheduler._already_sent_today(-100, "test_key")
    assert result is False


@pytest.mark.asyncio
async def test_mark_sent():
    from bot.scheduler.adhkar_scheduler import AdhkarScheduler

    repo = MagicMock()
    repo._db = AsyncMock()
    repo._db.execute = AsyncMock()

    app = MagicMock()
    scheduler = AdhkarScheduler(repo, app, tick_seconds=9999)

    await scheduler._mark_sent(-100, "test_key")
    repo._db.execute.assert_called_once()
