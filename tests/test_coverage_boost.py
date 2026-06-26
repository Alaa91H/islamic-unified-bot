"""
اختبارات إضافية لرفع تغطية الكود
Tests to boost coverage for the new bot structure
"""

import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ============================================================
# Tests for bot.config
# ============================================================


class TestSettings:
    def test_from_env_returns_all_values(self, monkeypatch):
        monkeypatch.setenv("BOT_TOKEN", "test_token")
        monkeypatch.setenv("API_ID", "12345")
        monkeypatch.setenv("API_HASH", "test_hash")
        monkeypatch.setenv("OWNER_ID", "99999")
        from bot.config import Settings

        settings = Settings.from_env()
        assert settings.bot_token == "test_token"
        assert settings.api_id == 12345
        assert settings.api_hash == "test_hash"
        assert settings.owner_id == 99999

    def test_defaults_applied(self, monkeypatch):
        monkeypatch.setenv("BOT_TOKEN", "t:token")
        monkeypatch.setenv("API_ID", "1")
        monkeypatch.setenv("API_HASH", "h")
        monkeypatch.setenv("OWNER_ID", "1")
        monkeypatch.delenv("MUSIC_DIR", raising=False)
        monkeypatch.delenv("QURAN_STREAM_URL", raising=False)
        monkeypatch.delenv("MAX_RECONNECT_ATTEMPTS", raising=False)
        from bot.config import Settings

        settings = Settings.from_env()
        assert settings.music_dir == "./music"
        assert "server8.mp3quran.net" in settings.quran_stream_url
        assert settings.max_reconnect_attempts == 10

    def test_settings_is_frozen(self, monkeypatch):
        monkeypatch.setenv("BOT_TOKEN", "t:token")
        monkeypatch.setenv("API_ID", "1")
        monkeypatch.setenv("API_HASH", "h")
        monkeypatch.setenv("OWNER_ID", "1")
        from bot.config import Settings

        settings = Settings.from_env()
        with pytest.raises(Exception):
            settings.bot_token = "new"


class TestSettingsValidation:
    def test_placeholder_token_raises(self, monkeypatch):
        monkeypatch.setenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
        monkeypatch.setenv("API_ID", "1")
        monkeypatch.setenv("API_HASH", "h")
        monkeypatch.setenv("OWNER_ID", "1")
        from bot.config import Settings

        with pytest.raises(ValueError):
            Settings.from_env()

    def test_empty_required_raises(self, monkeypatch):
        monkeypatch.setenv("BOT_TOKEN", "")
        monkeypatch.setenv("API_ID", "1")
        monkeypatch.setenv("API_HASH", "h")
        monkeypatch.setenv("OWNER_ID", "1")
        from bot.config import Settings

        with pytest.raises(ValueError):
            Settings.from_env()

    def test_non_numeric_api_id_raises(self, monkeypatch):
        monkeypatch.setenv("BOT_TOKEN", "t:token")
        monkeypatch.setenv("API_ID", "abc")
        monkeypatch.setenv("API_HASH", "h")
        monkeypatch.setenv("OWNER_ID", "1")
        from bot.config import Settings

        with pytest.raises(ValueError):
            Settings.from_env()


# ============================================================
# Tests for surahs & adhkar data
# ============================================================


class TestIslamicData:
    def test_surahs_dict_has_keys_1_to_114(self):
        from bot.data.surahs import SURAHS

        assert all(k in SURAHS for k in range(1, 115))

    def test_adhkar_categories_match(self):
        from bot.data.adhkar import ADHKAR, ADHKAR_CATEGORIES

        for key in ADHKAR_CATEGORIES:
            assert key in ADHKAR

    def test_each_adhkar_item_structure(self):
        from bot.data.adhkar import ADHKAR

        for cat, items in ADHKAR.items():
            for item in items:
                assert "title" in item
                assert "text" in item
                assert "benefit" in item

    def test_categories_values_are_strings(self):
        from bot.data.adhkar import ADHKAR_CATEGORIES

        for k, v in ADHKAR_CATEGORIES.items():
            assert isinstance(v, str) and len(v) > 0


# ============================================================
# Tests for main menu keyboard
# ============================================================


class TestMainKeyboard:
    @pytest.mark.asyncio
    async def test_home_keyboard_returns_markup(self):
        # Avoid pyrogram import outside event loop
        import asyncio
        try:
            asyncio.get_event_loop()
        except RuntimeError:
            asyncio.set_event_loop(asyncio.new_event_loop())
        from bot.handlers.main_menu import home_keyboard

        kb = home_keyboard()
        assert kb is not None

    @pytest.mark.asyncio
    async def test_home_keyboard_has_rows(self):
        import asyncio
        try:
            asyncio.get_event_loop()
        except RuntimeError:
            asyncio.set_event_loop(asyncio.new_event_loop())
        from pyrogram.types import InlineKeyboardMarkup
        from bot.handlers.main_menu import home_keyboard

        kb = home_keyboard()
        assert isinstance(kb, InlineKeyboardMarkup)
        assert len(kb.inline_keyboard) > 0


# ============================================================
# Tests for NullStreamManager
# ============================================================


class TestNullStreamManager:
    def setup_method(self):
        from bot.streaming.null_stream_manager import NullStreamManager

        self.manager = NullStreamManager(app=MagicMock())

    def test_active_streams_is_dict(self):
        assert isinstance(self.manager.active_streams(), dict)

    def test_active_streams_initially_empty(self):
        assert len(self.manager.active_streams()) == 0

    def test_get_local_files_invalid_path(self):
        result = self.manager.get_local_files("/nonexistent/path/xyz123")
        assert isinstance(result, dict)
        assert len(result) == 0

    def test_get_local_files_with_audio_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            for name in ["track1.mp3", "track2.wav", "notes.txt"]:
                Path(tmpdir, name).write_text("fake content")
            result = self.manager.get_local_files(tmpdir)
            assert isinstance(result, dict)
            assert all(
                v["name"].endswith((".mp3", ".wav", ".flac", ".m4a", ".ogg"))
                for v in result.values()
            )

    @pytest.mark.asyncio
    async def test_stop_returns_false(self):
        result = await self.manager.stop(100)
        assert result is False

    @pytest.mark.asyncio
    async def test_play_returns_false(self):
        result = await self.manager.play(123, "http://example.com/audio.mp3")
        assert result is False


# ============================================================
# Tests for logging setup
# ============================================================


class TestSetupLogging:
    def test_setup_logging_runs_without_error(self):
        from bot.logging_setup import setup_logging

        setup_logging()


# ============================================================
# Tests for azan_commands.py (legacy module)
# ============================================================


class TestAzanCommandsModule:
    def test_module_imports_cleanly(self):
        import azan_commands

        assert hasattr(azan_commands, "register_azan_commands")

    def test_register_azan_commands_is_coroutine(self):
        import inspect
        import azan_commands

        assert inspect.iscoroutinefunction(azan_commands.register_azan_commands)

    @pytest.mark.asyncio
    async def test_register_azan_commands_registers_handlers(self):
        import azan_commands

        mock_app = MagicMock()
        mock_app.on_message = MagicMock(return_value=lambda f: f)
        mock_app.on_callback_query = MagicMock(return_value=lambda f: f)

        await azan_commands.register_azan_commands(mock_app)
        assert mock_app.on_message.called or mock_app.on_callback_query.called


# ============================================================
# Tests for advanced_adhkar_library.py
# ============================================================


class TestAdvancedAdhkarLibraryExtra:
    def test_advanced_adhkar_import(self):
        from advanced_adhkar_library import ADVANCED_ADHKAR

        assert isinstance(ADVANCED_ADHKAR, dict)

    def test_main_block_runs(self):
        import io
        import runpy
        from contextlib import redirect_stdout

        f = io.StringIO()
        with redirect_stdout(f):
            runpy.run_path(
                os.path.join(
                    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                    "advanced_adhkar_library.py",
                ),
                run_name="__main__",
            )
        output = f.getvalue()
        assert "مكتبة" in output or "Advanced" in output
