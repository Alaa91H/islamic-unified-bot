import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock


@pytest.fixture(autouse=True)
def _event_loop():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    loop.close()


class TestAzanKeyboards:
    def test_city_selection_keyboard_returns_markup(self):
        from bot.handlers.azan import city_selection_keyboard
        from pyrogram.types import InlineKeyboardMarkup

        markup = city_selection_keyboard()
        assert isinstance(markup, InlineKeyboardMarkup)
        assert len(markup.inline_keyboard) > 0
        assert "🔙" in markup.inline_keyboard[-1][0].text

    def test_method_selection_keyboard_returns_markup(self):
        from bot.handlers.azan import method_selection_keyboard
        from pyrogram.types import InlineKeyboardMarkup

        markup = method_selection_keyboard("مكة المكرمة")
        assert isinstance(markup, InlineKeyboardMarkup)
        assert len(markup.inline_keyboard) > 0
        assert "كراتشي" in markup.inline_keyboard[0][0].text

    def test_settings_keyboard_returns_markup(self):
        from bot.handlers.azan import settings_keyboard
        from pyrogram.types import InlineKeyboardMarkup

        markup = settings_keyboard()
        assert isinstance(markup, InlineKeyboardMarkup)
        texts = [b.text for row in markup.inline_keyboard for b in row]
        assert any("تنبيهات" in t for t in texts)
        assert any("مدينة" in t for t in texts)


class TestAzanHandlersRegistration:
    def _make_mock_app(self):
        app = MagicMock()
        app.on_message = MagicMock(return_value=lambda fn: fn)
        app.on_callback_query = MagicMock(return_value=lambda fn: fn)
        return app

    def _make_deps(self):
        deps = MagicMock()
        deps.user_repo = AsyncMock()
        deps.user_repo.get = AsyncMock(return_value=None)
        deps.user_repo.upsert = AsyncMock()
        deps.user_repo.update_partial = AsyncMock()
        deps.group_repo = AsyncMock()
        deps.sent_repo = AsyncMock()
        deps.notifier = AsyncMock()
        deps.scheduler = MagicMock()
        return deps

    @pytest.mark.asyncio
    async def test_register_registers_handlers(self):
        from bot.handlers.azan import register

        app = self._make_mock_app()
        deps = self._make_deps()
        register(app, deps)

        msg_count = app.on_message.call_count
        cb_count = app.on_callback_query.call_count
        assert msg_count >= 5, f"Expected >=5 on_message handlers, got {msg_count}"
        assert cb_count >= 3, f"Expected >=3 callback handlers, got {cb_count}"

    @pytest.mark.asyncio
    async def test_deps_user_repo_used_when_user_has_settings(self):
        from bot.handlers.azan import register

        app = self._make_mock_app()
        deps = self._make_deps()
        deps.user_repo.get = AsyncMock(return_value=MagicMock(
            city="مكة المكرمة", method="isna", asr_method="standard",
            notifications_on=True, prelude_on=True, prelude_minutes=10,
        ))
        register(app, deps)

    @pytest.mark.asyncio
    async def test_deps_user_repo_returns_none_when_no_settings(self):
        from bot.handlers.azan import register

        app = self._make_mock_app()
        deps = self._make_deps()
        deps.user_repo.get = AsyncMock(return_value=None)
        register(app, deps)

    @pytest.mark.asyncio
    async def test_register_does_not_raise(self):
        from bot.handlers.azan import register

        app = self._make_mock_app()
        deps = self._make_deps()
        register(app, deps)
