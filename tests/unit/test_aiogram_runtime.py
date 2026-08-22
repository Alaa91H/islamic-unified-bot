from types import SimpleNamespace

import pytest

from bot.aiogram_runtime import (
    _adhkar_categories_keyboard,
    _adhkar_item_detail,
    _adhkar_items_keyboard,
    _home_keyboard,
    _name_detail,
    _names_keyboard,
    _parse_adhkar_callback,
    _parse_qts_callback,
    _quran_info_keyboard,
    _quran_page_keyboard,
    _quran_text_keyboard,
    build_aiogram_app,
    create_main_menu_router,
)


def test_aiogram_router_registers_the_pilot_main_menu_handlers():
    router = create_main_menu_router()

    assert router.name == "main-menu-pilot"
    assert len(router.message.handlers) == 5
    assert len(router.callback_query.handlers) == 6


def test_build_aiogram_app_includes_the_pilot_router():
    bot, dispatcher = build_aiogram_app(SimpleNamespace(bot_token="123:TEST"))

    assert dispatcher.sub_routers[0].name == "main-menu-pilot"
    assert bot.token == "123:TEST"


def test_aiogram_names_keyboard_and_detail_use_only_valid_name_indices():
    keyboard = _names_keyboard(0)
    detail = _name_detail(1)

    assert keyboard.inline_keyboard[0][0].callback_data == "names:show:1"
    assert keyboard.inline_keyboard[-1][0].callback_data == "back_to_start"
    assert detail is not None
    assert "الاسم 1" in detail[0]
    assert _name_detail(0) is None
    assert _name_detail(100) is None


def test_aiogram_home_keyboard_exposes_only_callbacks_implemented_by_pilot():
    callbacks = {
        button.callback_data
        for row in _home_keyboard().inline_keyboard
        for button in row
    }

    assert callbacks == {"quran_text:home", "adhkar:home", "names:page:0", "about"}


def test_aiogram_quran_text_keyboard_and_callbacks_are_bounded_to_text_reading():
    keyboard = _quran_text_keyboard()

    assert keyboard.inline_keyboard[0][0].callback_data == "qts:1:0"
    assert keyboard.inline_keyboard[-1][0].callback_data == "back_to_start"
    assert _parse_qts_callback("qts:114:1:tafsir") == (114, 1, True)
    assert _parse_qts_callback("qts:0:1") is None
    assert _parse_qts_callback("qts:1:-1") is None
    assert _parse_qts_callback("qts:1:one") is None
    assert _parse_qts_callback("qts:1:1:listen") is None


def test_aiogram_quran_detail_and_navigation_emit_only_supported_callbacks():
    keyboards = [
        _quran_info_keyboard(2),
        _quran_page_keyboard(2, 1, 29, False),
        _quran_page_keyboard(2, 29, 29, True),
    ]
    callbacks = {
        button.callback_data
        for keyboard in keyboards
        for row in keyboard.inline_keyboard
        for button in row
    }

    assert "quran_text:home" in callbacks
    assert "back_to_start" in {
        button.callback_data
        for row in _quran_info_keyboard(2).inline_keyboard
        for button in row
    }
    assert all(
        callback in {"quran_text:home", "back_to_start"}
        or _parse_qts_callback(callback) is not None
        for callback in callbacks
    )
    assert not any(
        "listen" in callback or "search" in callback for callback in callbacks
    )


def test_aiogram_adhkar_callbacks_are_bounded_to_local_data():
    categories = _adhkar_categories_keyboard()
    category_callback = categories.inline_keyboard[0][0].callback_data
    parsed_category = _parse_adhkar_callback(category_callback)

    assert parsed_category is not None
    _, category, _ = parsed_category
    items = _adhkar_items_keyboard(category)
    assert items is not None
    item_callback = items.inline_keyboard[0][0].callback_data
    assert _parse_adhkar_callback(item_callback) is not None
    assert _parse_adhkar_callback("adhkar:item:unknown:0") is None
    assert _parse_adhkar_callback(f"adhkar:item:{category}:999") is None
    assert _parse_adhkar_callback(f"adhkar:item:{category}:text") is None

    detail = _adhkar_item_detail(category, 0)
    assert detail is not None
    assert "**النص:**" in detail[0]


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
