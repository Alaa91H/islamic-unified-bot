from unittest.mock import AsyncMock

import pytest
from aiogram import Bot, Dispatcher
from aiogram.methods import AnswerCallbackQuery, EditMessageText, SendMessage
from aiogram.types import Update

from bot.aiogram_runtime import create_main_menu_router


def _message_update(text: str, update_id: int = 1) -> dict:
    return {
        "update_id": update_id,
        "message": {
            "message_id": 1,
            "date": 1,
            "chat": {"id": 100, "type": "private"},
            "from": {"id": 200, "is_bot": False, "first_name": "Tester"},
            "text": text,
        },
    }


def _callback_update(data: str, update_id: int = 2) -> dict:
    return {
        "update_id": update_id,
        "callback_query": {
            "id": "callback-id",
            "from": {"id": 200, "is_bot": False, "first_name": "Tester"},
            "chat_instance": "chat-instance",
            "data": data,
            "message": {
                "message_id": 1,
                "date": 1,
                "chat": {"id": 100, "type": "private"},
                "from": {"id": 999, "is_bot": True, "first_name": "Bot"},
                "text": "اختبار",
            },
        },
    }


async def _dispatch(payload: dict) -> list[object]:
    """مرّر Update فعليًا إلى Router وسجّل طلبات Bot API من دون شبكة."""
    bot = Bot(token="123:TEST")
    dispatcher = Dispatcher()
    dispatcher.include_router(create_main_menu_router())
    requests: list[object] = []

    async def record_request(*args, **kwargs):
        requests.append(args[1])
        return True

    bot.session.make_request = AsyncMock(side_effect=record_request)
    try:
        update = Update.model_validate(payload, context={"bot": bot})
        await dispatcher.feed_update(bot, update)
    finally:
        await bot.session.close()
    return requests


async def test_qibla_command_dispatches_a_local_result_without_network():
    requests = await _dispatch(_message_update("/qibla الرياض"))

    assert len(requests) == 1
    assert isinstance(requests[0], SendMessage)
    assert "**المدينة:** الرياض" in requests[0].text
    assert "**المسافة:**" in requests[0].text


async def test_qibla_help_callback_edits_message_then_answers_callback():
    requests = await _dispatch(_callback_update("qibla:help"))

    assert isinstance(requests[0], EditMessageText)
    assert "`/qibla [اسم المدينة]`" in requests[0].text
    assert isinstance(requests[1], AnswerCallbackQuery)
    assert requests[1].show_alert is None


@pytest.mark.parametrize(
    ("callback_data", "expected_text"),
    [
        ("qts:1:0", "**سورة الفاتحة**"),
        ("adhkar:home", "**الأذكار الإسلامية الشاملة**"),
        ("dua:home", "**الأدعية الجامعة**"),
        ("ramadan:today", "🌙 **رمضان مبارك**"),
    ],
)
async def test_reading_callbacks_dispatch_edit_and_answer(callback_data, expected_text):
    requests = await _dispatch(_callback_update(callback_data))

    assert isinstance(requests[0], EditMessageText)
    assert expected_text in requests[0].text
    assert isinstance(requests[1], AnswerCallbackQuery)


async def test_invalid_quran_callback_answers_with_alert_without_editing_message():
    requests = await _dispatch(_callback_update("qts:0:1"))

    assert len(requests) == 1
    assert isinstance(requests[0], AnswerCallbackQuery)
    assert requests[0].show_alert is True
    assert requests[0].text == "طلب غير صالح"
