import pytest


def test_from_env_reads_required_vars(monkeypatch):
    from bot.config import Settings

    monkeypatch.setenv("BOT_TOKEN", "123:ABC")
    monkeypatch.setenv("API_ID", "123456")
    monkeypatch.setenv("API_HASH", "abcdef1234567890")
    monkeypatch.setenv("OWNER_ID", "987654321")

    s = Settings.from_env()

    assert s.bot_token == "123:ABC"
    assert s.api_id == 123456
    assert s.api_hash == "abcdef1234567890"
    assert s.owner_id == 987654321


def test_from_env_rejects_placeholder_token(monkeypatch):
    from bot.config import Settings

    monkeypatch.setenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
    monkeypatch.setenv("API_ID", "123456")
    monkeypatch.setenv("API_HASH", "abcdef")
    monkeypatch.setenv("OWNER_ID", "1")
    with pytest.raises(ValueError, match="BOT_TOKEN"):
        Settings.from_env()


def test_from_env_rejects_empty_required(monkeypatch):
    from bot.config import Settings

    monkeypatch.delenv("BOT_TOKEN", raising=False)
    monkeypatch.setenv("API_ID", "123456")
    monkeypatch.setenv("API_HASH", "abcdef")
    monkeypatch.setenv("OWNER_ID", "1")
    with pytest.raises(ValueError, match="BOT_TOKEN"):
        Settings.from_env()


def test_from_env_rejects_non_numeric_api_id(monkeypatch):
    from bot.config import Settings

    monkeypatch.setenv("BOT_TOKEN", "123:ABC")
    monkeypatch.setenv("API_ID", "not-a-number")
    monkeypatch.setenv("API_HASH", "abcdef")
    monkeypatch.setenv("OWNER_ID", "1")
    with pytest.raises(ValueError, match="API_ID"):
        Settings.from_env()


def test_from_env_applies_defaults(monkeypatch):
    from bot.config import Settings

    monkeypatch.setenv("BOT_TOKEN", "123:ABC")
    monkeypatch.setenv("API_ID", "123456")
    monkeypatch.setenv("API_HASH", "abcdef")
    monkeypatch.setenv("OWNER_ID", "1")
    for k in ("MUSIC_DIR", "AZAN_DATA_DIR", "DEFAULT_CITY", "DB_PATH"):
        monkeypatch.delenv(k, raising=False)

    s = Settings.from_env()

    assert s.music_dir == "./music"
    assert s.default_city == "مكة المكرمة"
    assert s.max_reconnect_attempts == 10
    assert s.scheduler_tick_seconds == 30
    assert s.db_path == "./data/bot.db"


def test_is_owner_true_only_for_owner():
    from bot.config import Settings

    s = Settings(bot_token="1:ABC", api_id=1, api_hash="h", owner_id=42)
    assert s.is_owner(42) is True
    assert s.is_owner(99) is False


def test_settings_is_frozen():
    from bot.config import Settings

    s = Settings(bot_token="1:ABC", api_id=1, api_hash="h", owner_id=1)
    with pytest.raises(Exception):
        s.bot_token = "mutated"  # type: ignore[misc]
