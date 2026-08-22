"""عقود ومحولات طبقة نقل Telegram القابلة للاستبدال."""

from bot.transport.protocols import MessageTransport
from bot.transport.pyrogram import PyrogramMessageTransport

__all__ = ["MessageTransport", "PyrogramMessageTransport"]
