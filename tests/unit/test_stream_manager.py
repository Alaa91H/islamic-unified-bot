import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock


# ===== بدائل وهمية لرموز pytgcalls =====

class _NotInCallError(Exception):
    """بديل لpytgcalls.exceptions.NotInCallError."""


class _AudioQuality:
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    STUDIO = "studio"


class _MediaStream:
    def __init__(self, url, audio_parameters=None, ffmpeg_parameters=None):
        self.url = url
        self.audio_parameters = audio_parameters
        self.ffmpeg_parameters = ffmpeg_parameters


class _FakePyTgCalls:
    """بديل وهمي لـ PyTgCalls لاختبار StreamManager بدون native binding."""

    def __init__(self, app):
        self.app = app
        self.play = AsyncMock()
        self.leave_call = AsyncMock()
        self.stop = AsyncMock()
        self.start = AsyncMock()
        self._on_update = None

    def on_update(self):
        def deco(func):
            self._on_update = func
            return func
        return deco


def _fake_import():
    """دالة الاستيراد الوهمية — تُرجع رموز pytgcalls البديلة."""
    return _FakePyTgCalls, _NotInCallError, _AudioQuality, _MediaStream


@pytest.fixture
def manager():
    from bot.streaming.stream_manager import StreamManager

    fake = MagicMock()
    pytgcalls = _FakePyTgCalls(fake)
    sm = StreamManager(
        fake,
        max_reconnect=3,
        base_delay=1,
        default_duration_min=120,
        pytgcalls_factory=lambda app: pytgcalls,
        import_func=_fake_import,
    )
    return sm, pytgcalls


@pytest.mark.asyncio
async def test_play_stores_stream(manager):
    sm, _ = manager
    ok = await sm.play(-100, "http://x/a.mp3", "title", loop=False)
    assert ok is True
    streams = sm.active_streams()
    assert -100 in streams
    assert streams[-100]["loop"] is False


@pytest.mark.asyncio
async def test_stop_removes_stream(manager):
    sm, _ = manager
    await sm.play(-100, "http://x/a.mp3", "title")
    ok = await sm.stop(-100)
    assert ok is True
    assert -100 not in sm.active_streams()


@pytest.mark.asyncio
async def test_stop_returns_false_if_no_stream(manager):
    sm, _ = manager
    ok = await sm.stop(-999)
    assert ok is False


@pytest.mark.asyncio
async def test_play_retries_then_fails(manager):
    sm, ptc = manager
    ptc.play = AsyncMock(side_effect=RuntimeError("boom"))
    sm.base_delay = 0  # تسريع الاختبار
    ok = await sm.play(-100, "http://x/a.mp3", "t", loop=False)
    assert ok is False
    # المحاولة الأولى + max_reconnect إعادات = 1 + 3 = 4 محاولات
    assert ptc.play.await_count == sm.max_reconnect + 1


@pytest.mark.asyncio
async def test_play_not_in_call_treated_as_success(manager):
    sm, ptc = manager
    ptc.play = AsyncMock(side_effect=_NotInCallError())
    ok = await sm.play(-100, "http://x/a.mp3", "t")
    assert ok is True
    assert -100 in sm.active_streams()


@pytest.mark.asyncio
async def test_max_duration_schedules_stop(manager):
    sm, _ = manager
    await sm.play(-100, "http://x/a.mp3", "t", duration_min=0.0001)
    await asyncio.sleep(0.1)
    assert -100 not in sm.active_streams()


@pytest.mark.asyncio
async def test_start_registers_stream_end_handler(manager):
    sm, ptc = manager
    await sm.start()
    assert ptc._on_update is not None
    assert sm._started is True


@pytest.mark.asyncio
async def test_start_is_idempotent(manager):
    sm, _ = manager
    await sm.start()
    await sm.start()
    assert sm._started is True


@pytest.mark.asyncio
async def test_stop_all_clears_state(manager):
    sm, _ = manager
    await sm.play(-100, "http://x/a.mp3", "t", duration_min=999)
    await sm.stop_all()
    assert sm.active_streams() == {}
    assert sm._timers == {}


@pytest.mark.asyncio
async def test_stream_end_loop_replays(manager):
    """عند loop=True وانتهاء البث، يُعاد البث تلقائيًا."""
    sm, ptc = manager
    await sm.start()  # يسجّل معالج on_stream_end
    await sm.play(-100, "http://x/a.mp3", "t", loop=True, duration_min=999)
    ptc.play.reset_mock()
    fake_update = MagicMock()
    fake_update.chat_id = -100
    await ptc._on_update(None, fake_update)
    assert ptc.play.await_count == 1


@pytest.mark.asyncio
async def test_stream_end_no_loop_does_not_replay(manager):
    """عند loop=False، نهاية البث لا تُعيد التشغيل."""
    sm, ptc = manager
    await sm.start()  # يسجّل معالج on_stream_end
    await sm.play(-100, "http://x/a.mp3", "t", loop=False, duration_min=999)
    ptc.play.reset_mock()
    fake_update = MagicMock()
    fake_update.chat_id = -100
    await ptc._on_update(None, fake_update)
    assert ptc.play.await_count == 0
