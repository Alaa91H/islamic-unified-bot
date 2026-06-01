import pytest
import os
import tempfile
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from pathlib import Path


class TestConfigValidation:

    def test_missing_bot_token_exits(self, monkeypatch):
        monkeypatch.setenv("BOT_TOKEN", "")
        monkeypatch.setenv("API_ID", "12345")
        monkeypatch.setenv("API_HASH", "abc123")
        monkeypatch.setenv("OWNER_ID", "111")
        import importlib, sys
        if "main" in sys.modules:
            del sys.modules["main"]
        with pytest.raises(SystemExit):
            import main
            main.validate_config()

    def test_missing_api_id_exits(self, monkeypatch):
        monkeypatch.setenv("BOT_TOKEN", "valid:token")
        monkeypatch.setenv("API_ID", "0")
        monkeypatch.setenv("API_HASH", "")
        monkeypatch.setenv("OWNER_ID", "111")
        import sys
        if "main" in sys.modules:
            del sys.modules["main"]
        with pytest.raises(SystemExit):
            import main
            main.validate_config()

    def test_missing_owner_id_exits(self, monkeypatch):
        monkeypatch.setenv("BOT_TOKEN", "valid:token")
        monkeypatch.setenv("API_ID", "12345")
        monkeypatch.setenv("API_HASH", "abc123")
        monkeypatch.setenv("OWNER_ID", "0")
        import sys
        if "main" in sys.modules:
            del sys.modules["main"]
        with pytest.raises(SystemExit):
            import main
            main.validate_config()

    def test_get_config_returns_dict(self, monkeypatch):
        monkeypatch.setenv("BOT_TOKEN", "test:token")
        monkeypatch.setenv("API_ID", "99999")
        monkeypatch.setenv("API_HASH", "hashvalue")
        monkeypatch.setenv("OWNER_ID", "111111")
        import sys
        if "main" in sys.modules:
            del sys.modules["main"]
        import main
        cfg = main.get_config()
        assert isinstance(cfg, dict)
        assert "BOT_TOKEN" in cfg
        assert "API_ID" in cfg
        assert "OWNER_ID" in cfg


class TestStreamManager:

    def setup_method(self):
        self.tmp = tempfile.mkdtemp()

    def _make_manager(self):
        mock_client = MagicMock()
        with patch("main.PyTgCalls"), patch.dict(os.environ, {
            "BOT_TOKEN": "test:token",
            "API_ID": "123",
            "API_HASH": "hash",
            "OWNER_ID": "1",
            "MUSIC_DIR": self.tmp,
        }):
            import sys
            if "main" in sys.modules:
                del sys.modules["main"]
            import main
            manager = main.StreamManager(mock_client)
            return manager

    def test_get_local_files_empty_dir(self):
        manager = self._make_manager()
        files = manager.get_local_files(self.tmp)
        assert isinstance(files, dict)
        assert len(files) == 0

    def test_get_local_files_with_mp3(self):
        mp3_path = os.path.join(self.tmp, "test_audio.mp3")
        Path(mp3_path).write_bytes(b"ID3" + b"\x00" * 100)
        manager = self._make_manager()
        files = manager.get_local_files(self.tmp)
        assert len(files) == 1
        assert files[1]["name"] == "test_audio.mp3"

    def test_get_local_files_ignores_non_audio(self):
        Path(os.path.join(self.tmp, "document.txt")).write_text("text")
        Path(os.path.join(self.tmp, "image.png")).write_bytes(b"\x89PNG")
        manager = self._make_manager()
        files = manager.get_local_files(self.tmp)
        assert len(files) == 0

    def test_get_local_files_invalid_dir(self):
        manager = self._make_manager()
        files = manager.get_local_files("/nonexistent/path/xyz")
        assert isinstance(files, dict)

    def test_get_active_streams_initially_empty(self):
        manager = self._make_manager()
        streams = manager.get_active_streams()
        assert isinstance(streams, dict)
        assert len(streams) == 0

    @pytest.mark.asyncio
    async def test_stop_stream_not_active(self):
        manager = self._make_manager()
        result = await manager.stop_stream(99999)
        assert isinstance(result, bool)


class TestIslamicDataClass:

    def setup_method(self):
        import sys
        if "main" in sys.modules:
            del sys.modules["main"]
        with patch("main.PyTgCalls"), patch.dict(os.environ, {
            "BOT_TOKEN": "test:token", "API_ID": "123",
            "API_HASH": "hash", "OWNER_ID": "1",
        }):
            import main
            self.IslamicData = main.IslamicData

    def test_categories_not_empty(self):
        assert len(self.IslamicData.CATEGORIES) > 0

    def test_all_categories_have_adhkar(self):
        for key in self.IslamicData.CATEGORIES:
            adhkar = self.IslamicData.ADHKAR.get(key, [])
            assert len(adhkar) > 0, f"Category '{key}' has no adhkar"

    def test_adhkar_keys_match_categories(self):
        cats = set(self.IslamicData.CATEGORIES.keys())
        adh = set(self.IslamicData.ADHKAR.keys())
        missing = cats - adh
        assert not missing, f"Categories missing adhkar: {missing}"

    def test_surahs_count(self):
        assert len(self.IslamicData.SURAHS) == 114

    def test_surahs_keys_1_to_114(self):
        keys = set(self.IslamicData.SURAHS.keys())
        expected = set(range(1, 115))
        assert keys == expected, f"Unexpected surah keys: {keys.symmetric_difference(expected)}"

    def test_surah_names_non_empty_strings(self):
        for num, name in self.IslamicData.SURAHS.items():
            assert isinstance(name, str), f"Surah {num} name is not string"
            assert len(name.strip()) > 0, f"Surah {num} name is empty"

    def test_adhkar_items_have_required_fields(self):
        for category, items in self.IslamicData.ADHKAR.items():
            for i, item in enumerate(items):
                assert "title" in item, f"Missing title in {category}[{i}]"
                assert "text" in item, f"Missing text in {category}[{i}]"
                assert "benefit" in item, f"Missing benefit in {category}[{i}]"
