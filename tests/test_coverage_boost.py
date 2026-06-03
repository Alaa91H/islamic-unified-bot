"""
اختبارات إضافية لرفع تغطية الكود
Tests to boost coverage for main.py, azan_commands.py, and advanced_adhkar_library.py
"""

import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ============================================================
# Tests for main.py
# ============================================================


class TestGetConfig:
    def test_get_config_returns_all_keys(self, monkeypatch):
        monkeypatch.setenv("BOT_TOKEN", "test_token")
        monkeypatch.setenv("API_ID", "12345")
        monkeypatch.setenv("API_HASH", "test_hash")
        monkeypatch.setenv("OWNER_ID", "99999")
        import main

        cfg = main.get_config()
        assert "BOT_TOKEN" in cfg
        assert "API_ID" in cfg
        assert "API_HASH" in cfg
        assert "OWNER_ID" in cfg
        assert "MUSIC_DIR" in cfg
        assert "QURAN_STREAM_URL" in cfg
        assert "MAX_RECONNECT_ATTEMPTS" in cfg
        assert "INITIAL_RECONNECT_DELAY" in cfg

    def test_get_config_defaults(self, monkeypatch):
        monkeypatch.delenv("API_ID", raising=False)
        monkeypatch.delenv("MAX_RECONNECT_ATTEMPTS", raising=False)
        monkeypatch.delenv("INITIAL_RECONNECT_DELAY", raising=False)
        import main

        cfg = main.get_config()
        assert cfg["API_ID"] == 0
        assert cfg["MAX_RECONNECT_ATTEMPTS"] == 10
        assert cfg["INITIAL_RECONNECT_DELAY"] == 5

    def test_get_config_music_dir_default(self, monkeypatch):
        monkeypatch.delenv("MUSIC_DIR", raising=False)
        import main

        cfg = main.get_config()
        assert "MUSIC_DIR" in cfg
        assert isinstance(cfg["MUSIC_DIR"], str)

    def test_get_config_quran_url_default(self, monkeypatch):
        monkeypatch.delenv("QURAN_STREAM_URL", raising=False)
        import main

        cfg = main.get_config()
        assert "QURAN_STREAM_URL" in cfg
        assert cfg["QURAN_STREAM_URL"].startswith("https://")


class TestIslamicDataClass:
    def test_surahs_dict_has_keys_1_to_114(self):
        import main

        surahs = main.IslamicData.SURAHS
        assert all(k in surahs for k in range(1, 115))

    def test_adhkar_categories_match(self):
        import main

        for key in main.IslamicData.CATEGORIES:
            assert key in main.IslamicData.ADHKAR

    def test_each_adhkar_item_structure(self):
        import main

        for cat, items in main.IslamicData.ADHKAR.items():
            for item in items:
                assert "title" in item
                assert "text" in item
                assert "benefit" in item

    def test_categories_values_are_strings(self):
        import main

        for k, v in main.IslamicData.CATEGORIES.items():
            assert isinstance(v, str) and len(v) > 0


class TestMainKeyboard:
    def test_main_keyboard_returns_markup(self):
        import main

        kb = main.main_keyboard()
        assert kb is not None

    def test_main_keyboard_has_rows(self):
        from pyrogram.types import InlineKeyboardMarkup

        import main

        kb = main.main_keyboard()
        assert isinstance(kb, InlineKeyboardMarkup)
        assert len(kb.inline_keyboard) > 0


class TestStreamManagerMethods:
    def setup_method(self):
        import main

        with patch("main.PyTgCalls"):
            with patch("main.CONFIG", {"MUSIC_DIR": tempfile.mkdtemp()}):
                self.manager = main.StreamManager.__new__(main.StreamManager)
                self.manager.pytgcalls = MagicMock()
                self.manager.streams = {}
                self.manager._music_dir = tempfile.mkdtemp()

    def test_get_active_streams_is_dict(self):
        assert isinstance(self.manager.get_active_streams(), dict)

    def test_get_active_streams_initially_empty(self):
        assert len(self.manager.get_active_streams()) == 0

    def test_get_local_files_invalid_path(self):
        result = self.manager.get_local_files("/nonexistent/path/xyz123")
        assert isinstance(result, dict)
        assert len(result) == 0

    def test_get_local_files_with_audio_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create fake audio files
            for name in ["track1.mp3", "track2.wav", "notes.txt"]:
                Path(tmpdir, name).write_text("fake content")
            result = self.manager.get_local_files(tmpdir)
            assert isinstance(result, dict)
            # Only audio files should be included
            assert all(
                v["name"].endswith((".mp3", ".wav", ".flac", ".m4a", ".ogg"))
                for v in result.values()
            )

    @pytest.mark.asyncio
    async def test_stop_stream_success(self):
        self.manager.pytgcalls.leave_call = AsyncMock()
        self.manager.streams[100] = {"url": "test", "title": "test"}
        result = await self.manager.stop_stream(100)
        assert result is True
        assert 100 not in self.manager.streams

    @pytest.mark.asyncio
    async def test_stop_stream_failure(self):
        self.manager.pytgcalls.leave_call = AsyncMock(
            side_effect=Exception("call error")
        )
        result = await self.manager.stop_stream(999)
        assert result is False

    @pytest.mark.asyncio
    async def test_stop_manager_success(self):
        self.manager.pytgcalls.stop = AsyncMock()
        await self.manager.stop()
        self.manager.pytgcalls.stop.assert_called_once()

    @pytest.mark.asyncio
    async def test_stop_manager_failure(self):
        self.manager.pytgcalls.stop = AsyncMock(side_effect=Exception("stop error"))
        # Should not raise
        await self.manager.stop()


class TestSetupLogging:
    def test_setup_logging_runs_without_error(self):
        import main

        # Should not raise
        main.setup_logging()


# ============================================================
# Tests for azan_commands.py
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

        # Should run without errors and register handlers
        await azan_commands.register_azan_commands(mock_app)
        assert mock_app.on_message.called or mock_app.on_callback_query.called

    @pytest.mark.asyncio
    async def test_azan_setup_handler_no_user(self):
        """Test azan_setup sends city selection keyboard"""
        import azan_commands

        mock_app = MagicMock()
        captured_handlers = {}

        def capture_on_message(filter_):
            def decorator(func):
                captured_handlers[func.__name__] = func
                return func

            return decorator

        def capture_on_callback(filter_):
            def decorator(func):
                captured_handlers[func.__name__] = func
                return func

            return decorator

        mock_app.on_message = capture_on_message
        mock_app.on_callback_query = capture_on_callback

        await azan_commands.register_azan_commands(mock_app)

        if "azan_setup" in captured_handlers:
            mock_client = MagicMock()
            mock_message = MagicMock()
            mock_message.from_user.id = 12345
            mock_message.reply_text = AsyncMock()
            await captured_handlers["azan_setup"](mock_client, mock_message)
            mock_message.reply_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_azan_times_handler_no_settings(self):
        """Test azan_times when user has no settings"""
        import azan_commands

        mock_app = MagicMock()
        captured_handlers = {}

        def capture_on_message(filter_):
            def decorator(func):
                captured_handlers[func.__name__] = func
                return func

            return decorator

        def capture_on_callback(filter_):
            def decorator(func):
                captured_handlers[func.__name__] = func
                return func

            return decorator

        mock_app.on_message = capture_on_message
        mock_app.on_callback_query = capture_on_callback

        await azan_commands.register_azan_commands(mock_app)

        if "azan_times" in captured_handlers:
            mock_client = MagicMock()
            mock_message = MagicMock()
            mock_message.from_user.id = 99999
            mock_message.reply_text = AsyncMock()
            await captured_handlers["azan_times"](mock_client, mock_message)
            mock_message.reply_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_azan_next_handler_no_settings(self):
        """Test azan_next when user has no settings"""
        import azan_commands

        mock_app = MagicMock()
        captured_handlers = {}

        def capture_on_message(filter_):
            def decorator(func):
                captured_handlers[func.__name__] = func
                return func

            return decorator

        def capture_on_callback(filter_):
            def decorator(func):
                captured_handlers[func.__name__] = func
                return func

            return decorator

        mock_app.on_message = capture_on_message
        mock_app.on_callback_query = capture_on_callback

        await azan_commands.register_azan_commands(mock_app)

        if "azan_next" in captured_handlers:
            mock_client = MagicMock()
            mock_message = MagicMock()
            mock_message.from_user.id = 88888
            mock_message.reply_text = AsyncMock()
            await captured_handlers["azan_next"](mock_client, mock_message)
            mock_message.reply_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_azan_search_no_args(self):
        """Test azan_search with no query"""
        import azan_commands

        mock_app = MagicMock()
        captured_handlers = {}

        def capture_on_message(filter_):
            def decorator(func):
                captured_handlers[func.__name__] = func
                return func

            return decorator

        def capture_on_callback(filter_):
            def decorator(func):
                captured_handlers[func.__name__] = func
                return func

            return decorator

        mock_app.on_message = capture_on_message
        mock_app.on_callback_query = capture_on_callback

        await azan_commands.register_azan_commands(mock_app)

        if "azan_search" in captured_handlers:
            mock_client = MagicMock()
            mock_message = MagicMock()
            mock_message.from_user.id = 77777
            mock_message.command = ["azan_search"]  # no query arg
            mock_message.reply_text = AsyncMock()
            await captured_handlers["azan_search"](mock_client, mock_message)
            mock_message.reply_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_azan_search_with_query(self):
        """Test azan_search with a city query"""
        import azan_commands

        mock_app = MagicMock()
        captured_handlers = {}

        def capture_on_message(filter_):
            def decorator(func):
                captured_handlers[func.__name__] = func
                return func

            return decorator

        def capture_on_callback(filter_):
            def decorator(func):
                captured_handlers[func.__name__] = func
                return func

            return decorator

        mock_app.on_message = capture_on_message
        mock_app.on_callback_query = capture_on_callback

        await azan_commands.register_azan_commands(mock_app)

        if "azan_search" in captured_handlers:
            mock_client = MagicMock()
            mock_message = MagicMock()
            mock_message.from_user.id = 77777
            mock_message.command = ["azan_search", "مكة"]
            mock_message.reply_text = AsyncMock()
            await captured_handlers["azan_search"](mock_client, mock_message)
            mock_message.reply_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_azan_settings_handler_no_settings(self):
        """Test azan_settings when user has no settings"""
        import azan_commands

        mock_app = MagicMock()
        captured_handlers = {}

        def capture_on_message(filter_):
            def decorator(func):
                captured_handlers[func.__name__] = func
                return func

            return decorator

        def capture_on_callback(filter_):
            def decorator(func):
                captured_handlers[func.__name__] = func
                return func

            return decorator

        mock_app.on_message = capture_on_message
        mock_app.on_callback_query = capture_on_callback

        await azan_commands.register_azan_commands(mock_app)

        if "azan_settings" in captured_handlers:
            mock_client = MagicMock()
            mock_message = MagicMock()
            mock_message.from_user.id = 66666
            mock_message.reply_text = AsyncMock()
            await captured_handlers["azan_settings"](mock_client, mock_message)
            mock_message.reply_text.assert_called_once()


# ============================================================
# Tests for advanced_adhkar_library.py
# ============================================================


class TestAdvancedAdhkarLibraryExtra:
    def test_advanced_adhkar_import(self):
        from advanced_adhkar_library import ADVANCED_ADHKAR

        assert isinstance(ADVANCED_ADHKAR, dict)

    def test_main_block_runs(self):
        """Cover the __main__ block by running it via subprocess or exec"""
        # runpy.run_path will execute the __main__ block
        # We redirect stdout to avoid noise
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
