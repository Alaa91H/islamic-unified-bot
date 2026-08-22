"""محول Pyrogram لعقد النقل النصي."""

from __future__ import annotations


class PyrogramMessageTransport:
    def __init__(self, client):
        self._client = client

    async def send_text(self, chat_id: int, text: str) -> None:
        await self._client.send_message(chat_id, text)
