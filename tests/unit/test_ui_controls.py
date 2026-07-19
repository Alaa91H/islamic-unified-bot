from unittest.mock import AsyncMock, MagicMock

import pytest


def test_bottom_controls_row_keeps_controls_compact():
    from bot.handlers.ui import UI_CLOSE, bottom_controls_row

    row = bottom_controls_row("section:back")
    callbacks = [button.callback_data for button in row]

    assert callbacks == ["section:back", "back_to_start", UI_CLOSE]


def test_markup_with_bottom_controls_appends_one_row():
    from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

    from bot.handlers.ui import markup_with_bottom_controls

    markup = markup_with_bottom_controls(
        [[InlineKeyboardButton("A", callback_data="a")]],
        back_callback="back",
        home_callback=None,
    )

    assert isinstance(markup, InlineKeyboardMarkup)
    assert len(markup.inline_keyboard) == 2
    assert [button.callback_data for button in markup.inline_keyboard[-1]] == [
        "back",
        "ui:close",
    ]


@pytest.mark.asyncio
async def test_common_ui_close_deletes_message():
    from bot.handlers.main_menu import register

    app = MagicMock()
    captured = {}

    def capture_on_message(filter_):
        return lambda fn: fn

    def capture_on_callback(filter_):
        def decorator(func):
            captured[func.__name__] = func
            return func

        return decorator

    app.on_message = capture_on_message
    app.on_callback_query = capture_on_callback

    register(app, MagicMock())

    cq = MagicMock()
    cq.data = "ui:close"
    cq.message.delete = AsyncMock()
    cq.answer = AsyncMock()

    await captured["common_ui_handler"](MagicMock(), cq)

    cq.message.delete.assert_awaited_once()
    cq.answer.assert_awaited_once()
