"""محول aiogram لعقد النقل النصي؛ لا يفرض اعتمادًا أثناء مرحلة التحضير."""

from __future__ import annotations


class AiogramMessageTransport:
    """يمرر العقد إلى كائن aiogram.Bot عند بدء الهجرة الفعلية."""

    def __init__(self, bot):
        self._bot = bot

    async def send_text(self, chat_id: int, text: str) -> None:
        await self._bot.send_message(chat_id=chat_id, text=text)
