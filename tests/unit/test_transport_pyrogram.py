from unittest.mock import AsyncMock, MagicMock

import pytest

from bot.transport.pyrogram import PyrogramMessageTransport


@pytest.mark.asyncio
async def test_pyrogram_message_transport_forwards_text_contract():
    client = MagicMock()
    client.send_message = AsyncMock()

    transport = PyrogramMessageTransport(client)
    await transport.send_text(42, "السلام عليكم")

    client.send_message.assert_awaited_once_with(42, "السلام عليكم")
