from types import SimpleNamespace

import pytest

from bot.aiogram_runtime import build_aiogram_app, create_main_menu_router


def test_aiogram_router_registers_the_pilot_main_menu_handlers():
    router = create_main_menu_router()

    assert router.name == "main-menu-pilot"
    assert len(router.message.handlers) == 2
    assert len(router.callback_query.handlers) == 2


def test_build_aiogram_app_includes_the_pilot_router():
    bot, dispatcher = build_aiogram_app(SimpleNamespace(bot_token="123:TEST"))

    assert dispatcher.sub_routers[0].name == "main-menu-pilot"
    assert bot.token == "123:TEST"


def test_settings_rejects_aiogram_runtime_with_voice_streaming(monkeypatch):
    from bot.config import Settings

    monkeypatch.setenv("BOT_TOKEN", "123:ABC")
    monkeypatch.setenv("API_ID", "123456")
    monkeypatch.setenv("API_HASH", "abcdef")
    monkeypatch.setenv("OWNER_ID", "1")
    monkeypatch.setenv("TELEGRAM_RUNTIME", "aiogram")
    monkeypatch.setenv("STREAM_ENABLED", "true")

    with pytest.raises(ValueError, match="STREAM_ENABLED"):
        Settings.from_env()
