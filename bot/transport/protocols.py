"""العقود الدنيا التي تحتاجها خدمات المجال من Telegram."""

from __future__ import annotations

from typing import Protocol


class MessageTransport(Protocol):
    """إرسال نص إلى محادثة دون ربط الخدمة بإطار Telegram محدد."""

    async def send_text(self, chat_id: int, text: str) -> None: ...
