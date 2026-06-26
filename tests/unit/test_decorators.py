import pytest
from unittest.mock import AsyncMock, MagicMock


@pytest.mark.asyncio
async def test_owner_only_blocks_non_owner():
    from bot.decorators import owner_only

    settings = MagicMock()
    settings.is_owner.return_value = False

    @owner_only(settings)
    async def handler(client, message):
        return "ran"

    msg = MagicMock()
    msg.from_user.id = 999
    msg.reply_text = AsyncMock()
    result = await handler(None, msg)
    assert result is None
    msg.reply_text.assert_awaited_once()


@pytest.mark.asyncio
async def test_owner_only_allows_owner():
    from bot.decorators import owner_only

    settings = MagicMock()
    settings.is_owner.return_value = True

    @owner_only(settings)
    async def handler(client, message):
        return "ran"

    msg = MagicMock()
    msg.from_user.id = 1
    assert await handler(None, msg) == "ran"


@pytest.mark.asyncio
async def test_safe_handler_swallows_exception():
    from bot.decorators import safe_handler

    @safe_handler()
    async def handler(client, message):
        raise ValueError("boom")

    msg = MagicMock()
    msg.reply_text = AsyncMock()
    await handler(None, msg)  # يجب ألا يرفع
    msg.reply_text.assert_awaited_once()


@pytest.mark.asyncio
async def test_safe_handler_passes_through_on_success():
    from bot.decorators import safe_handler

    @safe_handler()
    async def handler(client, message):
        return "ok"

    msg = MagicMock()
    assert await handler(None, msg) == "ok"
