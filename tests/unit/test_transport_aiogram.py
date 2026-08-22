from unittest.mock import AsyncMock, MagicMock

import pytest

from bot.transport.aiogram import AiogramMessageTransport


@pytest.mark.asyncio
async def test_aiogram_message_transport_forwards_text_contract():
    bot = MagicMock()
    bot.send_message = AsyncMock()

    transport = AiogramMessageTransport(bot)
    await transport.send_text(42, "السلام عليكم")

    bot.send_message.assert_awaited_once_with(chat_id=42, text="السلام عليكم")
