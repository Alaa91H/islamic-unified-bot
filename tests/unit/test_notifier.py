import pytest
from unittest.mock import AsyncMock, MagicMock


@pytest.fixture
def notifier_bundle():
    from bot.scheduler.notifier import Notifier

    app = MagicMock()
    app.send_message = AsyncMock()
    stream = MagicMock()
    stream.play = AsyncMock(return_value=True)
    n = Notifier(app, stream)
    return n, app, stream


@pytest.mark.asyncio
async def test_notify_user_sends_message(notifier_bundle):
    n, app, _ = notifier_bundle
    ok = await n.notify_user(123, "fajr", "05:12")
    assert ok is True
    app.send_message.assert_awaited_once()
    args = app.send_message.call_args
    assert args.args[0] == 123
    msg = args.args[1]
    assert "الفجر" in msg and "05:12" in msg


@pytest.mark.asyncio
async def test_notify_user_prelude_text_differs(notifier_bundle):
    n, app, _ = notifier_bundle
    await n.notify_user(7, "dhuhr", "12:00", is_prelude=True)
    msg = app.send_message.call_args.args[1]
    assert "سيبدأ أذان" in msg


@pytest.mark.asyncio
async def test_notify_user_failure_returns_false(notifier_bundle):
    n, app, _ = notifier_bundle
    app.send_message = AsyncMock(side_effect=RuntimeError("blocked"))
    ok = await n.notify_user(1, "fajr", "05:00")
    assert ok is False


@pytest.mark.asyncio
async def test_broadcast_group_azan_streams(notifier_bundle):
    n, _, stream = notifier_bundle
    ok = await n.broadcast_group_azan(-100, "fajr", "traditional")
    assert ok is True
    stream.play.assert_awaited_once()
    args = stream.play.call_args
    assert args.args[0] == -100
    assert "fajr" in args.args[1] or "001" in args.args[1]


@pytest.mark.asyncio
async def test_broadcast_unknown_source_sends_text_only(notifier_bundle):
    n, app, stream = notifier_bundle
    ok = await n.broadcast_group_azan(-100, "fajr", "nonexistent_source")
    # لا رابط أذان → نص فقط، لكن يُرجع True
    assert ok is True
    stream.play.assert_not_awaited()
    app.send_message.assert_awaited_once()


@pytest.mark.asyncio
async def test_broadcast_stream_failure_returns_false(notifier_bundle):
    n, _, stream = notifier_bundle
    stream.play = AsyncMock(return_value=False)
    ok = await n.broadcast_group_azan(-100, "fajr", "traditional")
    assert ok is False
