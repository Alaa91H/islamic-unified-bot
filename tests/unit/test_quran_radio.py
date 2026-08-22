import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from bot.services.quran_radio import QuranRadio, estimate_duration


@pytest.fixture
def stream():
    return SimpleNamespace(
        play=AsyncMock(return_value=True), stop=AsyncMock(return_value=True)
    )


@pytest.fixture
def radio(stream):
    return QuranRadio(stream, SimpleNamespace(audio_quality="medium"))


async def _cancel_radio_task(radio: QuranRadio, chat_id: int) -> None:
    state = radio.get_state(chat_id)
    if state and state.task:
        state.task.cancel()
        await asyncio.gather(state.task, return_exceptions=True)


@pytest.mark.parametrize(
    ("surah_num", "expected"),
    [(1, 1), (2, 55), (10, 14), (20, 10), (35, 7), (55, 5), (75, 4), (95, 3), (114, 2)],
)
def test_estimate_duration_has_stable_tiers(surah_num, expected):
    assert estimate_duration(surah_num) == expected


async def test_start_plays_selected_surah_with_configured_quality(radio, stream):
    assert await radio.start(42, reciter_key="ahmed_al_ajmi", surah_start=18) is True

    state = radio.get_state(42)
    assert state is not None
    assert state.current_index == 17
    assert state.playing is True
    assert state.audio_quality == "medium"
    assert stream.play.await_args.kwargs == {
        "loop": False,
        "duration_min": 15,
        "audio_quality": "medium",
    }
    assert stream.play.await_args.args[0] == 42
    assert stream.play.await_args.args[1].endswith("018.mp3")
    await _cancel_radio_task(radio, 42)


async def test_next_prev_shuffle_and_stop_keep_radio_state_consistent(radio, stream):
    await radio.start(42, surah_start=2)
    assert await radio.next(42) is True
    assert radio.get_current_surah(radio.get_state(42)) == 3
    assert await radio.prev(42) is True
    assert radio.get_current_surah(radio.get_state(42)) == 2

    assert await radio.toggle_shuffle(42) is True
    shuffled = radio.get_state(42)
    assert shuffled.shuffle is True
    assert shuffled.queue[0] == 2
    assert sorted(shuffled.queue) == list(range(1, 115))

    assert await radio.toggle_shuffle(42) is True
    restored = radio.get_state(42)
    assert restored.shuffle is False
    assert radio.get_current_surah(restored) == 2
    assert await radio.stop(42) is True
    stream.stop.assert_awaited_once_with(42)


async def test_radio_rejects_unknown_state_and_invalid_reciter_or_quality(radio):
    assert await radio.next(999) is False
    assert await radio.prev(999) is False
    assert await radio.toggle_shuffle(999) is False
    assert await radio.set_reciter(999, "ahmed_al_ajmi") is False
    assert await radio.set_quality(999, "high") is False

    await radio.start(42)
    assert await radio.set_reciter(42, "unknown") is False
    assert await radio.set_quality(42, "ultra") is False
    await _cancel_radio_task(radio, 42)


async def test_quality_reciter_pause_and_resume_replay_current_surah(radio, stream):
    await radio.start(42)
    stream.play.reset_mock()

    assert await radio.set_quality(42, "studio") is True
    assert stream.play.await_args.kwargs["audio_quality"] == "studio"
    assert await radio.set_reciter(42, "ahmed_al_ajmi") is True
    assert "server12.mp3quran.net/ajm" in stream.play.await_args.args[1]

    assert await radio.pause(42) is True
    stream.stop.assert_awaited_once_with(42)
    assert await radio.resume(42) is True
    assert radio.get_state(42).paused is False
    await _cancel_radio_task(radio, 42)
