"""اختبارات NullStreamManager — مدير البث الفارغ (no-op)."""

import pytest
from unittest.mock import MagicMock, patch


@pytest.mark.asyncio
async def test_start_logs_message():
    from bot.streaming.null_stream_manager import NullStreamManager

    mgr = NullStreamManager()
    await mgr.start()


@pytest.mark.asyncio
async def test_stop_all_does_nothing():
    from bot.streaming.null_stream_manager import NullStreamManager

    mgr = NullStreamManager()
    await mgr.stop_all()


@pytest.mark.asyncio
async def test_play_returns_false():
    from bot.streaming.null_stream_manager import NullStreamManager

    mgr = NullStreamManager()
    result = await mgr.play(-100, "http://example.com/audio.mp3", "Test Stream")
    assert result is False


@pytest.mark.asyncio
async def test_stop_returns_false():
    from bot.streaming.null_stream_manager import NullStreamManager

    mgr = NullStreamManager()
    result = await mgr.stop(-100)
    assert result is False


def test_active_streams_returns_empty():
    from bot.streaming.null_stream_manager import NullStreamManager

    mgr = NullStreamManager()
    streams = mgr.active_streams()
    assert streams == {}


def test_get_local_files_returns_files(tmp_path):
    from bot.streaming.null_stream_manager import NullStreamManager

    music_dir = tmp_path / "music"
    music_dir.mkdir()
    (music_dir / "test1.mp3").write_text("data1")
    (music_dir / "test2.mp3").write_text("data2")
    (music_dir / "not_audio.txt").write_text("text")

    mgr = NullStreamManager()
    files = mgr.get_local_files(str(music_dir))
    assert len(files) == 2
    names = [f["name"] for f in files.values()]
    assert "test1.mp3" in names
    assert "test2.mp3" in names
    assert "not_audio.txt" not in names


def test_get_local_files_empty_dir(tmp_path):
    from bot.streaming.null_stream_manager import NullStreamManager

    empty_dir = tmp_path / "empty"
    empty_dir.mkdir()

    mgr = NullStreamManager()
    files = mgr.get_local_files(str(empty_dir))
    assert files == {}


def test_get_local_files_non_existent_dir():
    from bot.streaming.null_stream_manager import NullStreamManager

    mgr = NullStreamManager()
    files = mgr.get_local_files("/nonexistent/path/xyz123")
    assert files == {}


def test_get_local_files_default_path(tmp_path):
    from bot.streaming.null_stream_manager import NullStreamManager

    mgr = NullStreamManager()
    files = mgr.get_local_files()
    assert files == {}
