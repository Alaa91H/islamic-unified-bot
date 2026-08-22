from unittest.mock import AsyncMock, MagicMock

import pytest


@pytest.fixture
def notifier_bundle():
    from bot.scheduler.notifier import Notifier

    messages = MagicMock()
    messages.send_text = AsyncMock()
    stream = MagicMock()
    stream.play = AsyncMock(return_value=True)
    return Notifier(messages, stream), messages, stream


@pytest.mark.asyncio
async def test_notify_user_sends_message(notifier_bundle):
    notifier, messages, _ = notifier_bundle
    assert await notifier.notify_user(123, "fajr", "05:12") is True
    messages.send_text.assert_awaited_once()
    args = messages.send_text.call_args
    assert args.args[0] == 123
    assert "الفجر" in args.args[1] and "05:12" in args.args[1]


@pytest.mark.asyncio
async def test_notify_user_prelude_text_differs(notifier_bundle):
    notifier, messages, _ = notifier_bundle
    await notifier.notify_user(7, "dhuhr", "12:00", is_prelude=True)
    assert "سيبدأ أذان" in messages.send_text.call_args.args[1]


@pytest.mark.asyncio
async def test_notify_user_failure_returns_false(notifier_bundle):
    notifier, messages, _ = notifier_bundle
    messages.send_text = AsyncMock(side_effect=RuntimeError("blocked"))
    assert await notifier.notify_user(1, "fajr", "05:00") is False


@pytest.mark.asyncio
async def test_broadcast_group_azan_streams(notifier_bundle):
    notifier, _, stream = notifier_bundle
    assert await notifier.broadcast_group_azan(-100, "fajr", "traditional") is True
    stream.play.assert_awaited_once()
    assert stream.play.call_args.args[0] == -100
    assert (
        "fajr" in stream.play.call_args.args[1]
        or "001" in stream.play.call_args.args[1]
    )


@pytest.mark.asyncio
async def test_broadcast_unknown_source_sends_text_only(notifier_bundle):
    notifier, messages, stream = notifier_bundle
    assert (
        await notifier.broadcast_group_azan(-100, "fajr", "nonexistent_source") is True
    )
    stream.play.assert_not_awaited()
    messages.send_text.assert_awaited_once()


@pytest.mark.asyncio
async def test_broadcast_stream_failure_returns_false(notifier_bundle):
    notifier, _, stream = notifier_bundle
    stream.play = AsyncMock(return_value=False)
    assert await notifier.broadcast_group_azan(-100, "fajr", "traditional") is False
