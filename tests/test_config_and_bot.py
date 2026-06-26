import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


class TestConfigValidation:

    def test_missing_bot_token_raises(self, monkeypatch):
        monkeypatch.setenv("BOT_TOKEN", "")
        monkeypatch.setenv("API_ID", "12345")
        monkeypatch.setenv("API_HASH", "abc123")
        monkeypatch.setenv("OWNER_ID", "111")
        from bot.config import Settings

        with pytest.raises(ValueError):
            Settings.from_env()

    def test_missing_api_id_raises(self, monkeypatch):
        monkeypatch.setenv("BOT_TOKEN", "valid:token")
        monkeypatch.setenv("API_ID", "")
        monkeypatch.setenv("API_HASH", "abc123")
        monkeypatch.setenv("OWNER_ID", "111")
        from bot.config import Settings

        with pytest.raises(ValueError):
            Settings.from_env()

    def test_missing_owner_id_raises(self, monkeypatch):
        monkeypatch.setenv("BOT_TOKEN", "valid:token")
        monkeypatch.setenv("API_ID", "12345")
        monkeypatch.setenv("API_HASH", "abc123")
        monkeypatch.setenv("OWNER_ID", "")
        from bot.config import Settings

        with pytest.raises(ValueError):
            Settings.from_env()

    def test_from_env_returns_settings_with_required_fields(self, monkeypatch):
        monkeypatch.setenv("BOT_TOKEN", "test:token")
        monkeypatch.setenv("API_ID", "99999")
        monkeypatch.setenv("API_HASH", "hashvalue")
        monkeypatch.setenv("OWNER_ID", "111111")
        from bot.config import Settings

        settings = Settings.from_env()
        assert settings.bot_token == "test:token"
        assert settings.api_id == 99999
        assert settings.api_hash == "hashvalue"
        assert settings.owner_id == 111111

    def test_is_owner_true_for_owner(self, monkeypatch):
        monkeypatch.setenv("BOT_TOKEN", "test:token")
        monkeypatch.setenv("API_ID", "123")
        monkeypatch.setenv("API_HASH", "hash")
        monkeypatch.setenv("OWNER_ID", "42")
        from bot.config import Settings

        settings = Settings.from_env()
        assert settings.is_owner(42) is True
        assert settings.is_owner(99) is False


class TestNullStreamManager:

    def setup_method(self):
        from bot.streaming.null_stream_manager import NullStreamManager

        self.tmp = tempfile.mkdtemp()
        self.manager = NullStreamManager(app=MagicMock())

    def test_get_local_files_empty_dir(self):
        files = self.manager.get_local_files(self.tmp)
        assert isinstance(files, dict)
        assert len(files) == 0

    def test_get_local_files_with_mp3(self):
        mp3_path = os.path.join(self.tmp, "test_audio.mp3")
        Path(mp3_path).write_bytes(b"ID3" + b"\x00" * 100)
        files = self.manager.get_local_files(self.tmp)
        assert len(files) == 1
        assert files[1]["name"] == "test_audio.mp3"

    def test_get_local_files_ignores_non_audio(self):
        Path(os.path.join(self.tmp, "document.txt")).write_text("text")
        Path(os.path.join(self.tmp, "image.png")).write_bytes(b"\x89PNG")
        files = self.manager.get_local_files(self.tmp)
        assert len(files) == 0

    def test_get_local_files_invalid_dir(self):
        files = self.manager.get_local_files("/nonexistent/path/xyz")
        assert isinstance(files, dict)

    def test_active_streams_initially_empty(self):
        streams = self.manager.active_streams()
        assert isinstance(streams, dict)
        assert len(streams) == 0

    @pytest.mark.asyncio
    async def test_stop_returns_false(self):
        result = await self.manager.stop(99999)
        assert result is False


class TestIslamicDataClass:

    def setup_method(self):
        from bot.data.surahs import SURAHS
        from bot.data.adhkar import ADHKAR, ADHKAR_CATEGORIES

        self.SURAHS = SURAHS
        self.ADHKAR = ADHKAR
        self.CATEGORIES = ADHKAR_CATEGORIES

    def test_categories_not_empty(self):
        assert len(self.CATEGORIES) > 0

    def test_all_categories_have_adhkar(self):
        for key in self.CATEGORIES:
            adhkar = self.ADHKAR.get(key, [])
            assert len(adhkar) > 0, f"Category '{key}' has no adhkar"

    def test_adhkar_keys_match_categories(self):
        cats = set(self.CATEGORIES.keys())
        adh = set(self.ADHKAR.keys())
        missing = cats - adh
        assert not missing, f"Categories missing adhkar: {missing}"

    def test_surahs_count(self):
        assert len(self.SURAHS) == 114

    def test_surahs_keys_1_to_114(self):
        keys = set(self.SURAHS.keys())
        expected = set(range(1, 115))
        assert (
            keys == expected
        ), f"Unexpected surah keys: {keys.symmetric_difference(expected)}"

    def test_surah_names_non_empty_strings(self):
        for num, name in self.SURAHS.items():
            assert isinstance(name, str), f"Surah {num} name is not string"
            assert len(name.strip()) > 0, f"Surah {num} name is empty"

    def test_adhkar_items_have_required_fields(self):
        for category, items in self.ADHKAR.items():
            for i, item in enumerate(items):
                assert "title" in item, f"Missing title in {category}[{i}]"
                assert "text" in item, f"Missing text in {category}[{i}]"
                assert "benefit" in item, f"Missing benefit in {category}[{i}]"
