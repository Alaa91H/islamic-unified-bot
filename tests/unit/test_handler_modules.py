import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


# Pyrogram needs an event loop at import time on some platforms
@pytest.fixture(scope="session", autouse=True)
def _pyrogram_event_loop():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    yield
    loop.close()


class TestMainMenuFunctions:
    def test_home_keyboard_returns_markup(self):
        from bot.handlers.main_menu import home_keyboard
        from pyrogram.types import InlineKeyboardMarkup

        markup = home_keyboard()
        assert isinstance(markup, InlineKeyboardMarkup)
        assert len(markup.inline_keyboard) > 0

    def test_home_keyboard_has_expected_buttons(self):
        from bot.handlers.main_menu import home_keyboard

        markup = home_keyboard()
        texts = [b.text for row in markup.inline_keyboard for b in row]
        assert any("الأذكار" in t for t in texts)
        assert any("القرآن" in t for t in texts)
        assert any("الأذان" in t for t in texts)
        assert any("حول البوت" in t for t in texts)

    def test_home_keyboard_callback_data(self):
        from bot.handlers.main_menu import home_keyboard

        markup = home_keyboard()
        callbacks = [b.callback_data for row in markup.inline_keyboard for b in row]
        assert "main_adhkar_menu" in callbacks
        assert "quran_menu" in callbacks
        assert "azan_home" in callbacks
        assert "about" in callbacks

    def test_welcome_text_defined(self):
        from bot.handlers.main_menu import WELCOME_TEXT

        assert isinstance(WELCOME_TEXT, str) and len(WELCOME_TEXT) > 0
        assert "البوت الإسلامي الموحد" in WELCOME_TEXT

    def test_help_text_defined(self):
        from bot.handlers.main_menu import PRIVATE_HELP

        assert isinstance(PRIVATE_HELP, str) and len(PRIVATE_HELP) > 0
        assert "/quran" in PRIVATE_HELP

    def test_about_text_defined(self):
        from bot.handlers.main_menu import ABOUT_TEXT

        assert isinstance(ABOUT_TEXT, str) and len(ABOUT_TEXT) > 0
        assert "البوت الإسلامي الموحد" in ABOUT_TEXT


class TestAdhkarFunctions:
    def test_categories_keyboard_returns_markup(self):
        from bot.handlers.adhkar import categories_keyboard
        from pyrogram.types import InlineKeyboardMarkup
        from bot.data.adhkar import ADHKAR_CATEGORIES

        markup = categories_keyboard()
        assert isinstance(markup, InlineKeyboardMarkup)
        assert len(markup.inline_keyboard) == len(ADHKAR_CATEGORIES) + 1

    def test_categories_keyboard_has_back_button(self):
        from bot.handlers.adhkar import categories_keyboard

        markup = categories_keyboard()
        assert "🔙" in markup.inline_keyboard[-1][0].text

    def test_items_keyboard_valid_category(self):
        from bot.handlers.adhkar import items_keyboard
        from pyrogram.types import InlineKeyboardMarkup
        from bot.data.adhkar import ADHKAR

        for cat in ADHKAR:
            markup = items_keyboard(cat)
            assert isinstance(markup, InlineKeyboardMarkup)
            assert len(markup.inline_keyboard) >= len(ADHKAR[cat])

    def test_items_keyboard_invalid_category(self):
        from bot.handlers.adhkar import items_keyboard

        assert items_keyboard("nonexistent") is None

    def test_item_text_valid_index(self):
        from bot.handlers.adhkar import item_text
        from pyrogram.types import InlineKeyboardMarkup

        result = item_text("morning", 0)
        assert result is not None
        text, kb = result
        assert isinstance(text, str) and len(text) > 0
        assert isinstance(kb, InlineKeyboardMarkup)
        assert "✨" in text or "🕌" in text

    def test_item_text_invalid_category(self):
        from bot.handlers.adhkar import item_text

        assert item_text("nonexistent", 0) is None

    def test_item_text_invalid_index(self):
        from bot.handlers.adhkar import item_text

        assert item_text("morning", 999) is None

    def test_item_text_evening(self):
        from bot.handlers.adhkar import item_text
        from pyrogram.types import InlineKeyboardMarkup

        result = item_text("evening", 0)
        assert result is not None
        text, kb = result
        assert isinstance(text, str)
        assert isinstance(kb, InlineKeyboardMarkup)

    def test_items_keyboard_has_back_button(self):
        from bot.handlers.adhkar import items_keyboard

        markup = items_keyboard("morning")
        assert any("🔙" in b.text for row in markup.inline_keyboard for b in row)


class TestQuranFunctions:
    def test_surahs_keyboard_page_0(self):
        from bot.handlers.quran import surahs_keyboard
        from pyrogram.types import InlineKeyboardMarkup

        markup = surahs_keyboard(0)
        assert isinstance(markup, InlineKeyboardMarkup)
        assert len(markup.inline_keyboard) > 0

    def test_surahs_keyboard_first_page_has_next(self):
        from bot.handlers.quran import surahs_keyboard

        markup = surahs_keyboard(0)
        texts = [b.text for row in markup.inline_keyboard for b in row]
        assert any("التالي" in t for t in texts)

    def test_surahs_keyboard_last_page_has_prev(self):
        from bot.handlers.quran import surahs_keyboard

        markup = surahs_keyboard(5)
        texts = [b.text for row in markup.inline_keyboard for b in row]
        assert any("السابق" in t for t in texts)

    def test_surahs_keyboard_middle_page_has_both(self):
        from bot.handlers.quran import surahs_keyboard

        markup = surahs_keyboard(2)
        texts = [b.text for row in markup.inline_keyboard for b in row]
        assert any("السابق" in t for t in texts)
        assert any("التالي" in t for t in texts)

    def test_reciters_keyboard_returns_markup(self):
        from bot.handlers.quran import reciters_keyboard
        from pyrogram.types import InlineKeyboardMarkup
        from bot.data.sources import QURANIC_RECITERS

        markup = reciters_keyboard()
        assert isinstance(markup, InlineKeyboardMarkup)
        assert len(markup.inline_keyboard) == len(QURANIC_RECITERS) + 1

    def test_reciters_keyboard_has_back_button(self):
        from bot.handlers.quran import reciters_keyboard

        markup = reciters_keyboard()
        assert "🔙" in markup.inline_keyboard[-1][0].text


class TestMainMenuRegistration:
    @pytest.mark.asyncio
    async def test_register_registers_handlers(self):
        from bot.handlers.main_menu import register

        app = MagicMock()
        app.on_message = MagicMock(return_value=lambda fn: fn)
        app.on_callback_query = MagicMock(return_value=lambda fn: fn)

        register(app, MagicMock())
        assert app.on_message.call_count >= 2
        assert app.on_callback_query.call_count >= 1

    @pytest.mark.asyncio
    async def test_start_handler_replies(self):
        from bot.handlers.main_menu import register, WELCOME_TEXT, home_keyboard
        from pyrogram.types import InlineKeyboardMarkup

        app = MagicMock()
        captured = {}

        def capture_on_message(filter_):
            def decorator(func):
                captured[func.__name__] = func
                return func
            return decorator

        app.on_message = capture_on_message
        app.on_callback_query = MagicMock(return_value=lambda fn: fn)

        register(app, MagicMock())

        if "start_cmd" in captured:
            client = MagicMock()
            message = MagicMock()
            message.reply_text = AsyncMock()
            message.from_user = MagicMock()
            message.from_user.id = 12345

            message.chat.type = "private"
            await captured["start_cmd"](client, message)
            message.reply_text.assert_called_once()
            args, kwargs = message.reply_text.call_args
            assert WELCOME_TEXT in args[0]
            assert isinstance(kwargs.get("reply_markup"), InlineKeyboardMarkup)

    @pytest.mark.asyncio
    async def test_help_handler_replies(self):
        from bot.handlers.main_menu import register, PRIVATE_HELP

        app = MagicMock()
        captured = {}

        def capture_on_message(filter_):
            def decorator(func):
                captured[func.__name__] = func
                return func
            return decorator

        app.on_message = capture_on_message
        app.on_callback_query = MagicMock(return_value=lambda fn: fn)

        register(app, MagicMock())

        if "help_cmd" in captured:
            client = MagicMock()
            message = MagicMock()
            message.reply_text = AsyncMock()
            message.from_user = MagicMock()
            message.chat = MagicMock()
            message.chat.type = "private"

            await captured["help_cmd"](client, message)
            message.reply_text.assert_called_once_with(PRIVATE_HELP)

    @pytest.mark.asyncio
    async def test_home_handler_about_callback(self):
        from bot.handlers.main_menu import register, ABOUT_TEXT, home_keyboard

        app = MagicMock()
        captured = {}

        app.on_message = MagicMock(return_value=lambda fn: fn)

        def capture_on_callback(filter_):
            def decorator(func):
                captured[func.__name__] = func
                return func
            return decorator

        app.on_callback_query = capture_on_callback

        register(app, MagicMock())

        if "home_handler" in captured:
            client = MagicMock()
            cq = MagicMock()
            cq.data = "about"
            cq.message.edit_text = AsyncMock()
            cq.answer = AsyncMock()

            await captured["home_handler"](client, cq)
            cq.message.edit_text.assert_called_once()
            args, kwargs = cq.message.edit_text.call_args
            assert ABOUT_TEXT in args[0]
            cq.answer.assert_called_once()

    @pytest.mark.asyncio
    async def test_home_handler_back_to_start_callback(self):
        from bot.handlers.main_menu import register

        app = MagicMock()
        captured = {}

        app.on_message = MagicMock(return_value=lambda fn: fn)

        def capture_on_callback(filter_):
            def decorator(func):
                captured[func.__name__] = func
                return func
            return decorator

        app.on_callback_query = capture_on_callback

        register(app, MagicMock())

        if "home_handler" in captured:
            client = MagicMock()
            cq = MagicMock()
            cq.data = "back_to_start"
            cq.message.edit_text = AsyncMock()
            cq.answer = AsyncMock()

            await captured["home_handler"](client, cq)
            cq.message.edit_text.assert_called_once()
            args, kwargs = cq.message.edit_text.call_args
            assert "القائمة الرئيسية" in args[0]
            cq.answer.assert_called_once()


class TestAdhkarRegistration:
    @pytest.mark.asyncio
    async def test_register_registers_handlers(self):
        from bot.handlers.adhkar import register

        app = MagicMock()
        app.on_message = MagicMock(return_value=lambda fn: fn)
        app.on_callback_query = MagicMock(return_value=lambda fn: fn)

        register(app, MagicMock())
        assert app.on_message.call_count >= 1
        assert app.on_callback_query.call_count >= 3

    @pytest.mark.asyncio
    async def test_adhkar_cmd_replies(self):
        from bot.handlers.adhkar import register

        app = MagicMock()
        captured = {}

        def capture_on_message(filter_):
            def decorator(func):
                captured[func.__name__] = func
                return func
            return decorator

        app.on_message = capture_on_message
        app.on_callback_query = MagicMock(return_value=lambda fn: fn)

        register(app, MagicMock())

        if "adhkar_cmd" in captured:
            client = MagicMock()
            message = MagicMock()
            message.reply_text = AsyncMock()
            message.from_user = MagicMock()

            await captured["adhkar_cmd"](client, message)
            message.reply_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_menu_handler(self):
        from bot.handlers.adhkar import register, categories_keyboard

        app = MagicMock()
        captured = {}

        app.on_message = MagicMock(return_value=lambda fn: fn)

        def capture_on_callback(filter_):
            def decorator(func):
                captured[func.__name__] = func
                return func
            return decorator

        app.on_callback_query = capture_on_callback

        register(app, MagicMock())

        if "menu_handler" in captured:
            client = MagicMock()
            cq = MagicMock()
            cq.data = "main_adhkar_menu"
            cq.message.edit_text = AsyncMock()
            cq.answer = AsyncMock()

            await captured["menu_handler"](client, cq)
            cq.message.edit_text.assert_called_once()
            assert "اختر فئة الأذكار" in cq.message.edit_text.call_args[0][0]
            cq.answer.assert_called_once()

    @pytest.mark.asyncio
    async def test_category_handler_valid(self):
        from bot.handlers.adhkar import register

        app = MagicMock()
        captured = {}

        app.on_message = MagicMock(return_value=lambda fn: fn)

        def capture_on_callback(filter_):
            def decorator(func):
                captured[func.__name__] = func
                return func
            return decorator

        app.on_callback_query = capture_on_callback

        register(app, MagicMock())

        if "category_handler" in captured:
            client = MagicMock()
            cq = MagicMock()
            cq.data = "category_morning"
            cq.message.edit_text = AsyncMock()
            cq.answer = AsyncMock()

            await captured["category_handler"](client, cq)
            cq.message.edit_text.assert_called_once()
            cq.answer.assert_called_once()

    @pytest.mark.asyncio
    async def test_category_handler_invalid(self):
        from bot.handlers.adhkar import register

        app = MagicMock()
        captured = {}

        app.on_message = MagicMock(return_value=lambda fn: fn)

        def capture_on_callback(filter_):
            def decorator(func):
                captured[func.__name__] = func
                return func
            return decorator

        app.on_callback_query = capture_on_callback

        register(app, MagicMock())

        if "category_handler" in captured:
            client = MagicMock()
            cq = MagicMock()
            cq.data = "category_nonexistent"
            cq.answer = AsyncMock()

            await captured["category_handler"](client, cq)
            cq.answer.assert_called_once_with("❌ فئة غير معروفة", show_alert=True)

    @pytest.mark.asyncio
    async def test_item_handler_valid(self):
        from bot.handlers.adhkar import register

        app = MagicMock()
        captured = {}

        app.on_message = MagicMock(return_value=lambda fn: fn)

        def capture_on_callback(filter_):
            def decorator(func):
                captured[func.__name__] = func
                return func
            return decorator

        app.on_callback_query = capture_on_callback

        register(app, MagicMock())

        if "item_handler" in captured:
            client = MagicMock()
            cq = MagicMock()
            cq.data = "adhkar_morning_0"
            cq.message.edit_text = AsyncMock()
            cq.answer = AsyncMock()

            await captured["item_handler"](client, cq)
            cq.message.edit_text.assert_called_once()
            cq.answer.assert_called_once()

    @pytest.mark.asyncio
    async def test_item_handler_invalid(self):
        from bot.handlers.adhkar import register

        app = MagicMock()
        captured = {}

        app.on_message = MagicMock(return_value=lambda fn: fn)

        def capture_on_callback(filter_):
            def decorator(func):
                captured[func.__name__] = func
                return func
            return decorator

        app.on_callback_query = capture_on_callback

        register(app, MagicMock())

        if "item_handler" in captured:
            client = MagicMock()
            cq = MagicMock()
            cq.data = "adhkar_nonexistent_0"
            cq.answer = AsyncMock()

            await captured["item_handler"](client, cq)
            cq.answer.assert_called_once_with("❌ ذكر غير موجود", show_alert=True)


class TestQuranRegistration:
    @pytest.mark.asyncio
    async def test_register_registers_handlers(self):
        from bot.handlers.quran import register

        app = MagicMock()
        app.on_message = MagicMock(return_value=lambda fn: fn)
        app.on_callback_query = MagicMock(return_value=lambda fn: fn)

        register(app, MagicMock())
        assert app.on_message.call_count >= 1
        assert app.on_callback_query.call_count >= 5

    @pytest.mark.asyncio
    async def test_quran_cmd_replies(self):
        from bot.handlers.quran import register

        app = MagicMock()
        captured = {}

        def capture_on_message(filter_):
            def decorator(func):
                captured[func.__name__] = func
                return func
            return decorator

        app.on_message = capture_on_message
        app.on_callback_query = MagicMock(return_value=lambda fn: fn)

        register(app, MagicMock())

        if "quran_cmd" in captured:
            client = MagicMock()
            message = MagicMock()
            message.reply_text = AsyncMock()
            message.from_user = MagicMock()

            await captured["quran_cmd"](client, message)
            message.reply_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_quran_menu_handler(self):
        from bot.handlers.quran import register

        app = MagicMock()
        captured = {}

        app.on_message = MagicMock(return_value=lambda fn: fn)

        def capture_on_callback(filter_):
            def decorator(func):
                captured[func.__name__] = func
                return func
            return decorator

        app.on_callback_query = capture_on_callback

        register(app, MagicMock())

        if "quran_menu_handler" in captured:
            client = MagicMock()
            cq = MagicMock()
            cq.data = "quran_menu"
            cq.message.edit_text = AsyncMock()

            await captured["quran_menu_handler"](client, cq)
            cq.message.edit_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_quran_list_handler(self):
        from bot.handlers.quran import register

        app = MagicMock()
        captured = {}

        app.on_message = MagicMock(return_value=lambda fn: fn)

        def capture_on_callback(filter_):
            def decorator(func):
                captured[func.__name__] = func
                return func
            return decorator

        app.on_callback_query = capture_on_callback

        register(app, MagicMock())

        if "quran_list_handler" in captured:
            client = MagicMock()
            cq = MagicMock()
            cq.data = "quran_list"
            cq.message.edit_text = AsyncMock()

            await captured["quran_list_handler"](client, cq)
            cq.message.edit_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_quran_page_handler(self):
        from bot.handlers.quran import register

        app = MagicMock()
        captured = {}

        app.on_message = MagicMock(return_value=lambda fn: fn)

        def capture_on_callback(filter_):
            def decorator(func):
                captured[func.__name__] = func
                return func
            return decorator

        app.on_callback_query = capture_on_callback

        register(app, MagicMock())

        if "quran_page_handler" in captured:
            client = MagicMock()
            cq = MagicMock()
            cq.data = "quran_page:2"
            cq.message.edit_text = AsyncMock()

            await captured["quran_page_handler"](client, cq)
            cq.message.edit_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_quran_surah_handler(self):
        from bot.handlers.quran import register

        app = MagicMock()
        captured = {}

        app.on_message = MagicMock(return_value=lambda fn: fn)

        def capture_on_callback(filter_):
            def decorator(func):
                captured[func.__name__] = func
                return func
            return decorator

        app.on_callback_query = capture_on_callback

        register(app, MagicMock())

        if "quran_surah_handler" in captured:
            client = MagicMock()
            cq = MagicMock()
            cq.data = "quran_surah:1"
            cq.message.edit_text = AsyncMock()

            await captured["quran_surah_handler"](client, cq)
            cq.message.edit_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_quran_reciters_handler(self):
        from bot.handlers.quran import register

        app = MagicMock()
        captured = {}

        app.on_message = MagicMock(return_value=lambda fn: fn)

        def capture_on_callback(filter_):
            def decorator(func):
                captured[func.__name__] = func
                return func
            return decorator

        app.on_callback_query = capture_on_callback

        register(app, MagicMock())

        if "quran_reciters_handler" in captured:
            client = MagicMock()
            cq = MagicMock()
            cq.data = "quran_reciters"
            cq.message.edit_text = AsyncMock()

            await captured["quran_reciters_handler"](client, cq)
            cq.message.edit_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_quran_reciter_handler_valid(self):
        from bot.handlers.quran import register
        from bot.data.sources import QURANIC_RECITERS

        app = MagicMock()
        captured = {}

        app.on_message = MagicMock(return_value=lambda fn: fn)

        def capture_on_callback(filter_):
            def decorator(func):
                captured[func.__name__] = func
                return func
            return decorator

        app.on_callback_query = capture_on_callback

        register(app, MagicMock())

        if "quran_reciter_handler" in captured:
            client = MagicMock()
            cq = MagicMock()
            first_key = next(iter(QURANIC_RECITERS))
            cq.data = f"quran_reciter:{first_key}"
            cq.message.edit_text = AsyncMock()

            await captured["quran_reciter_handler"](client, cq)
            cq.message.edit_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_quran_reciter_handler_invalid(self):
        from bot.handlers.quran import register

        app = MagicMock()
        captured = {}

        app.on_message = MagicMock(return_value=lambda fn: fn)

        def capture_on_callback(filter_):
            def decorator(func):
                captured[func.__name__] = func
                return func
            return decorator

        app.on_callback_query = capture_on_callback

        register(app, MagicMock())

        if "quran_reciter_handler" in captured:
            client = MagicMock()
            cq = MagicMock()
            cq.data = "quran_reciter:nonexistent"
            cq.answer = AsyncMock()

            await captured["quran_reciter_handler"](client, cq)
            cq.answer.assert_called_once_with("❌ غير معروف", show_alert=True)


class TestOwnerRegistration:
    def _make_deps(self):
        deps = MagicMock()
        deps.settings = MagicMock()
        deps.settings.is_owner = MagicMock(return_value=True)
        deps.settings.quran_stream_url = "https://example.com/"
        deps.settings.music_dir = "/tmp/music"
        deps.stream_manager = MagicMock()
        deps.stream_manager.play = AsyncMock(return_value=True)
        deps.stream_manager.stop = AsyncMock(return_value=True)
        deps.stream_manager.active_streams = MagicMock(return_value={})
        deps.stream_manager.get_local_files = MagicMock(return_value={})
        return deps

    def _capture_handlers(self, app, deps):
        from bot.handlers.owner import register

        captured = {}

        def capture_on_message(filter_):
            def decorator(func):
                captured[func.__name__] = func
                return func
            return decorator

        app.on_message = capture_on_message
        app.on_callback_query = MagicMock(return_value=lambda fn: fn)

        register(app, deps)
        return captured

    @pytest.mark.asyncio
    async def test_register_registers_stream_handlers(self):
        from unittest.mock import patch

        app = MagicMock()
        app.on_message = MagicMock(return_value=lambda fn: fn)
        app.on_callback_query = MagicMock(return_value=lambda fn: fn)

        with patch("bot.handlers.owner.HAS_STREAMING", True):
            register_owner = __import__("bot.handlers.owner", fromlist=["register"]).register
            register_owner(app, self._make_deps())
        assert app.on_message.call_count >= 4

    @pytest.mark.asyncio
    async def test_stream_cmd_no_args(self):
        app = MagicMock()
        captured = self._capture_handlers(app, self._make_deps())

        if "stream_cmd" in captured:
            client = MagicMock()
            message = MagicMock()
            message.command = ["stream"]
            message.reply_text = AsyncMock()
            message.from_user = MagicMock()
            message.from_user.id = 1

            await captured["stream_cmd"](client, message)
            message.reply_text.assert_called_once()
            assert "استخدام" in message.reply_text.call_args[0][0]

    @pytest.mark.asyncio
    async def test_stream_cmd_quran(self):
        deps = self._make_deps()
        deps.stream_manager.play = AsyncMock(return_value=True)

        app = MagicMock()
        captured = self._capture_handlers(app, deps)

        if "stream_cmd" in captured:
            client = MagicMock()
            message = MagicMock()
            message.command = ["stream", "-100123", "quran", "1"]
            message.reply_text = AsyncMock()
            message.from_user = MagicMock()
            message.from_user.id = 1

            await captured["stream_cmd"](client, message)
            message.reply_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_stream_cmd_quran_missing_number(self):
        app = MagicMock()
        captured = self._capture_handlers(app, self._make_deps())

        if "stream_cmd" in captured:
            client = MagicMock()
            message = MagicMock()
            message.command = ["stream", "-100123", "quran"]
            message.reply_text = AsyncMock()
            message.from_user = MagicMock()
            message.from_user.id = 1

            await captured["stream_cmd"](client, message)
            message.reply_text.assert_called_once()
            assert "رقم السورة" in message.reply_text.call_args[0][0]

    @pytest.mark.asyncio
    async def test_stream_cmd_quran_invalid_surah(self):
        app = MagicMock()
        captured = self._capture_handlers(app, self._make_deps())

        if "stream_cmd" in captured:
            client = MagicMock()
            message = MagicMock()
            message.command = ["stream", "-100123", "quran", "999"]
            message.reply_text = AsyncMock()
            message.from_user = MagicMock()
            message.from_user.id = 1

            await captured["stream_cmd"](client, message)
            message.reply_text.assert_called_once()
            assert "1-114" in message.reply_text.call_args[0][0]

    @pytest.mark.asyncio
    async def test_stream_cmd_url(self):
        deps = self._make_deps()
        deps.stream_manager.play = AsyncMock(return_value=True)

        app = MagicMock()
        captured = self._capture_handlers(app, deps)

        if "stream_cmd" in captured:
            client = MagicMock()
            message = MagicMock()
            message.command = ["stream", "-100123", "url", "https://example.com/audio.mp3"]
            message.reply_text = AsyncMock()
            message.from_user = MagicMock()
            message.from_user.id = 1

            await captured["stream_cmd"](client, message)
            message.reply_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_stream_cmd_file_missing_number(self):
        app = MagicMock()
        captured = self._capture_handlers(app, self._make_deps())

        if "stream_cmd" in captured:
            client = MagicMock()
            message = MagicMock()
            message.command = ["stream", "-100123", "file"]
            message.reply_text = AsyncMock()
            message.from_user = MagicMock()
            message.from_user.id = 1

            await captured["stream_cmd"](client, message)
            message.reply_text.assert_called_once()
            assert "رقم الملف" in message.reply_text.call_args[0][0]

    @pytest.mark.asyncio
    async def test_stream_cmd_file_invalid_number(self):
        deps = self._make_deps()
        deps.stream_manager.get_local_files = MagicMock(return_value={})

        app = MagicMock()
        captured = self._capture_handlers(app, deps)

        if "stream_cmd" in captured:
            client = MagicMock()
            message = MagicMock()
            message.command = ["stream", "-100123", "file", "1"]
            message.reply_text = AsyncMock()
            message.from_user = MagicMock()
            message.from_user.id = 1

            await captured["stream_cmd"](client, message)
            message.reply_text.assert_called_once()
            assert "غير موجود" in message.reply_text.call_args[0][0]

    @pytest.mark.asyncio
    async def test_stop_cmd_no_args(self):
        app = MagicMock()
        captured = self._capture_handlers(app, self._make_deps())

        if "stop_cmd" in captured:
            client = MagicMock()
            message = MagicMock()
            message.command = ["stop"]
            message.reply_text = AsyncMock()
            message.from_user = MagicMock()
            message.from_user.id = 1

            await captured["stop_cmd"](client, message)
            message.reply_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_stop_cmd_success(self):
        deps = self._make_deps()
        deps.stream_manager.stop = AsyncMock(return_value=True)

        app = MagicMock()
        captured = self._capture_handlers(app, deps)

        if "stop_cmd" in captured:
            client = MagicMock()
            message = MagicMock()
            message.command = ["stop", "-100123"]
            message.reply_text = AsyncMock()
            message.from_user = MagicMock()
            message.from_user.id = 1

            await captured["stop_cmd"](client, message)
            message.reply_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_status_cmd_no_streams(self):
        deps = self._make_deps()
        deps.stream_manager.active_streams = MagicMock(return_value={})

        app = MagicMock()
        captured = self._capture_handlers(app, deps)

        if "status_cmd" in captured:
            client = MagicMock()
            message = MagicMock()
            message.command = ["status"]
            message.reply_text = AsyncMock()
            message.from_user = MagicMock()
            message.from_user.id = 1

            await captured["status_cmd"](client, message)
            message.reply_text.assert_called_once()
            assert "لا توجد بثات" in message.reply_text.call_args[0][0]

    @pytest.mark.asyncio
    async def test_status_cmd_with_streams(self):
        from datetime import datetime, timedelta

        deps = self._make_deps()
        deps.stream_manager.active_streams = MagicMock(return_value={
            -100123: {"url": "test", "title": "Test Stream", "started_at": datetime.now() - timedelta(minutes=30)},
        })

        app = MagicMock()
        captured = self._capture_handlers(app, deps)

        if "status_cmd" in captured:
            client = MagicMock()
            message = MagicMock()
            message.command = ["status"]
            message.reply_text = AsyncMock()
            message.from_user = MagicMock()
            message.from_user.id = 1

            await captured["status_cmd"](client, message)
            message.reply_text.assert_called_once()
            assert "البثات النشطة" in message.reply_text.call_args[0][0]

    @pytest.mark.asyncio
    async def test_files_cmd_empty(self):
        deps = self._make_deps()
        deps.settings.music_dir = "/tmp/music"
        deps.stream_manager.get_local_files = MagicMock(return_value={})

        app = MagicMock()
        captured = self._capture_handlers(app, deps)

        if "files_cmd" in captured:
            client = MagicMock()
            message = MagicMock()
            message.command = ["files"]
            message.reply_text = AsyncMock()
            message.from_user = MagicMock()
            message.from_user.id = 1

            await captured["files_cmd"](client, message)
            message.reply_text.assert_called_once()
            assert "لا توجد ملفات" in message.reply_text.call_args[0][0]

    @pytest.mark.asyncio
    async def test_files_cmd_with_files(self):
        deps = self._make_deps()
        deps.settings.music_dir = "/tmp/music"
        deps.stream_manager.get_local_files = MagicMock(return_value={
            1: {"name": "test.mp3", "path": "/tmp/music/test.mp3", "size": 5 * 1024 * 1024},
            2: {"name": "test2.mp3", "path": "/tmp/music/test2.mp3", "size": 10 * 1024 * 1024},
        })

        app = MagicMock()
        captured = self._capture_handlers(app, deps)

        if "files_cmd" in captured:
            client = MagicMock()
            message = MagicMock()
            message.command = ["files"]
            message.reply_text = AsyncMock()
            message.from_user = MagicMock()
            message.from_user.id = 1

            await captured["files_cmd"](client, message)
            message.reply_text.assert_called_once()
            assert "الملفات" in message.reply_text.call_args[0][0]


class TestHandlerRegistry:
    def test_registry_registers_all_handlers(self):
        from bot.handlers import HandlerRegistry

        app = MagicMock()
        app.on_message = MagicMock(return_value=lambda fn: fn)
        app.on_callback_query = MagicMock(return_value=lambda fn: fn)

        deps = MagicMock()
        deps.settings = MagicMock()
        deps.stream_manager = MagicMock()

        registry = HandlerRegistry()
        registry.register(app, deps)
        assert app.on_message.called
        assert app.on_callback_query.called

    def test_registry_imports_all_modules(self):
        from bot.handlers import HandlerRegistry

        import bot.handlers.adhkar
        import bot.handlers.azan
        import bot.handlers.main_menu
        import bot.handlers.owner
        import bot.handlers.quran
        import bot.handlers.hadith
        import bot.handlers.quran_text
        import bot.handlers.islamic_names
        import bot.handlers.group_adhkar
        import bot.handlers.group_quran
        import bot.handlers.islamic_tools
        import bot.handlers.quran_radio_handler

        assert True


class TestBuildApp:
    @patch("pyrogram.Client")
    def test_build_app_returns_client(self, mock_client_cls):
        from bot.app import build_app

        settings = MagicMock()
        settings.session_name = "test_session"
        settings.api_id = 12345
        settings.api_hash = "hash"
        settings.bot_token = "token"

        deps = MagicMock()
        result = build_app(settings, deps)
        assert result is not None
        mock_client_cls.assert_called_once()

    @patch("pyrogram.Client")
    def test_build_app_passes_session_name(self, mock_client_cls):
        from bot.app import build_app

        settings = MagicMock()
        settings.session_name = "test_session"
        settings.api_id = 12345
        settings.api_hash = "test_hash"
        settings.bot_token = "test_token"

        deps = MagicMock()
        build_app(settings, deps)
        mock_client_cls.assert_called_once_with(
            "test_session",
            api_id=12345,
            api_hash="test_hash",
            bot_token="test_token",
        )


class TestAzanHandlerExecution:
    def _make_deps(self):
        deps = MagicMock()
        deps.user_repo = AsyncMock()
        deps.user_repo.get = AsyncMock()
        deps.user_repo.upsert = AsyncMock()
        deps.user_repo.update_partial = AsyncMock()
        deps.group_repo = AsyncMock()
        deps.sent_repo = AsyncMock()
        deps.notifier = AsyncMock()
        deps.scheduler = MagicMock()
        return deps

    def _capture_azan(self, app, deps):
        from bot.handlers.azan import register

        captured = {}

        def capture_on_message(filter_):
            def decorator(func):
                captured[func.__name__] = func
                return func
            return decorator

        def capture_on_callback(filter_):
            def decorator(func):
                captured[func.__name__] = func
                return func
            return decorator

        app.on_message = capture_on_message
        app.on_callback_query = capture_on_callback
        register(app, deps)
        return captured

    @pytest.mark.asyncio
    async def test_azan_setup_cmd_sends_keyboard(self):
        app = MagicMock()
        captured = self._capture_azan(app, self._make_deps())

        if "azan_setup_cmd" in captured:
            client = MagicMock()
            message = MagicMock()
            message.reply_text = AsyncMock()
            message.from_user = MagicMock()

            await captured["azan_setup_cmd"](client, message)
            message.reply_text.assert_called_once()
            assert "اختر مدينتك" in message.reply_text.call_args[0][0]

    @pytest.mark.asyncio
    async def test_city_handler_valid(self):
        app = MagicMock()
        captured = self._capture_azan(app, self._make_deps())

        if "city_handler" in captured:
            client = MagicMock()
            cq = MagicMock()
            cq.data = "azan_city:مكة المكرمة"
            cq.message.edit_text = AsyncMock()

            await captured["city_handler"](client, cq)
            cq.message.edit_text.assert_called_once()
            assert "مكة المكرمة" in cq.message.edit_text.call_args[0][0]

    @pytest.mark.asyncio
    async def test_city_handler_invalid(self):
        app = MagicMock()
        captured = self._capture_azan(app, self._make_deps())

        if "city_handler" in captured:
            client = MagicMock()
            cq = MagicMock()
            cq.data = "azan_city:NONEXISTENT_CITY_XYZ"
            cq.answer = AsyncMock()

            await captured["city_handler"](client, cq)
            cq.answer.assert_called_once_with("❌ المدينة غير متاحة", show_alert=True)

    @pytest.mark.asyncio
    async def test_method_handler(self):
        app = MagicMock()
        captured = self._capture_azan(app, self._make_deps())

        if "method_handler" in captured:
            client = MagicMock()
            cq = MagicMock()
            cq.data = "azan_method:مكة المكرمة:makkah"
            cq.from_user.id = 12345
            cq.message.edit_text = AsyncMock()

            await captured["method_handler"](client, cq)
            cq.message.edit_text.assert_called_once()
            assert "تم الإعداد" in cq.message.edit_text.call_args[0][0]

    @pytest.mark.asyncio
    async def test_azan_times_cmd_no_settings(self):
        deps = self._make_deps()
        deps.user_repo.get = AsyncMock(return_value=None)

        app = MagicMock()
        captured = self._capture_azan(app, deps)

        if "azan_times_cmd" in captured:
            client = MagicMock()
            message = MagicMock()
            message.from_user.id = 12345
            message.reply_text = AsyncMock()

            await captured["azan_times_cmd"](client, message)
            message.reply_text.assert_called_once()
            assert "لم تقم بالإعداد" in message.reply_text.call_args[0][0]

    @pytest.mark.asyncio
    async def test_azan_times_cmd_with_settings(self):
        user_settings = MagicMock()
        user_settings.city = "مكة المكرمة"
        user_settings.method = "makkah"
        user_settings.asr_method = "standard"
        user_settings.notifications_on = True
        user_settings.prelude_on = True
        user_settings.prelude_minutes = 10

        deps = self._make_deps()
        deps.user_repo.get = AsyncMock(return_value=user_settings)

        app = MagicMock()
        captured = self._capture_azan(app, deps)

        if "azan_times_cmd" in captured:
            client = MagicMock()
            message = MagicMock()
            message.from_user.id = 12345
            message.reply_text = AsyncMock()

            await captured["azan_times_cmd"](client, message)
            message.reply_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_azan_next_cmd_no_settings(self):
        deps = self._make_deps()
        deps.user_repo.get = AsyncMock(return_value=None)

        app = MagicMock()
        captured = self._capture_azan(app, deps)

        if "azan_next_cmd" in captured:
            client = MagicMock()
            message = MagicMock()
            message.from_user.id = 12345
            message.reply_text = AsyncMock()

            await captured["azan_next_cmd"](client, message)
            message.reply_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_azan_next_cmd_no_remaining(self):
        user_settings = MagicMock()
        user_settings.city = "مكة المكرمة"
        user_settings.method = "makkah"
        user_settings.asr_method = "standard"

        deps = self._make_deps()
        deps.user_repo.get = AsyncMock(return_value=user_settings)

        app = MagicMock()
        captured = self._capture_azan(app, deps)

        if "azan_next_cmd" in captured:
            client = MagicMock()
            message = MagicMock()
            message.from_user.id = 12345
            message.reply_text = AsyncMock()

            await captured["azan_next_cmd"](client, message)
            message.reply_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_azan_search_cmd_no_args(self):
        app = MagicMock()
        captured = self._capture_azan(app, self._make_deps())

        if "azan_search_cmd" in captured:
            client = MagicMock()
            message = MagicMock()
            message.command = ["azan_search"]
            message.reply_text = AsyncMock()

            await captured["azan_search_cmd"](client, message)
            message.reply_text.assert_called_once()
            assert "الاستخدام" in message.reply_text.call_args[0][0]

    @pytest.mark.asyncio
    async def test_azan_search_cmd_with_query(self):
        app = MagicMock()
        captured = self._capture_azan(app, self._make_deps())

        if "azan_search_cmd" in captured:
            client = MagicMock()
            message = MagicMock()
            message.command = ["azan_search", "مكة"]
            message.reply_text = AsyncMock()

            await captured["azan_search_cmd"](client, message)
            message.reply_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_azan_settings_cmd_no_settings(self):
        deps = self._make_deps()
        deps.user_repo.get = AsyncMock(return_value=None)

        app = MagicMock()
        captured = self._capture_azan(app, deps)

        if "azan_settings_cmd" in captured:
            client = MagicMock()
            message = MagicMock()
            message.from_user.id = 12345
            message.reply_text = AsyncMock()

            await captured["azan_settings_cmd"](client, message)
            message.reply_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_azan_settings_cmd_with_settings(self):
        user_settings = MagicMock()
        user_settings.city = "مكة المكرمة"
        user_settings.method = "makkah"
        user_settings.asr_method = "standard"
        user_settings.notifications_on = True
        user_settings.prelude_on = True
        user_settings.prelude_minutes = 10

        deps = self._make_deps()
        deps.user_repo.get = AsyncMock(return_value=user_settings)

        app = MagicMock()
        captured = self._capture_azan(app, deps)

        if "azan_settings_cmd" in captured:
            client = MagicMock()
            message = MagicMock()
            message.from_user.id = 12345
            message.reply_text = AsyncMock()

            await captured["azan_settings_cmd"](client, message)
            message.reply_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_settings_menu_handler(self):
        app = MagicMock()
        captured = self._capture_azan(app, self._make_deps())

        if "settings_menu_handler" in captured:
            client = MagicMock()
            cq = MagicMock()
            cq.message.edit_text = AsyncMock()

            await captured["settings_menu_handler"](client, cq)
            cq.message.edit_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_azan_home_handler(self):
        app = MagicMock()
        captured = self._capture_azan(app, self._make_deps())

        if "azan_home_handler" in captured:
            client = MagicMock()
            cq = MagicMock()
            cq.message.edit_text = AsyncMock()

            await captured["azan_home_handler"](client, cq)
            cq.message.edit_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_notif_settings_handler(self):
        user_settings = MagicMock()
        user_settings.notifications_on = True
        user_settings.prelude_on = False
        user_settings.prelude_minutes = 10

        deps = self._make_deps()
        deps.user_repo.get = AsyncMock(return_value=user_settings)

        app = MagicMock()
        captured = self._capture_azan(app, deps)

        if "notif_settings_handler" in captured:
            client = MagicMock()
            cq = MagicMock()
            cq.from_user.id = 12345
            cq.message.edit_text = AsyncMock()

            await captured["notif_settings_handler"](client, cq)
            cq.message.edit_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_notif_settings_handler_no_settings(self):
        deps = self._make_deps()
        deps.user_repo.get = AsyncMock(return_value=None)

        app = MagicMock()
        captured = self._capture_azan(app, deps)

        if "notif_settings_handler" in captured:
            client = MagicMock()
            cq = MagicMock()
            cq.from_user.id = 12345

            await captured["notif_settings_handler"](client, cq)

    @pytest.mark.asyncio
    async def test_toggle_notif(self):
        user_settings = MagicMock()
        user_settings.notifications_on = True

        deps = self._make_deps()
        deps.user_repo.get = AsyncMock(return_value=user_settings)

        app = MagicMock()
        captured = self._capture_azan(app, deps)

        if "toggle_notif" in captured:
            client = MagicMock()
            cq = MagicMock()
            cq.from_user.id = 12345
            cq.message.edit_text = AsyncMock()
            cq.answer = AsyncMock()

            await captured["toggle_notif"](client, cq)

    @pytest.mark.asyncio
    async def test_toggle_prelude(self):
        user_settings = MagicMock()
        user_settings.prelude_on = True

        deps = self._make_deps()
        deps.user_repo.get = AsyncMock(return_value=user_settings)

        app = MagicMock()
        captured = self._capture_azan(app, deps)

        if "toggle_prelude" in captured:
            client = MagicMock()
            cq = MagicMock()
            cq.from_user.id = 12345
            cq.message.edit_text = AsyncMock()
            cq.answer = AsyncMock()

            await captured["toggle_prelude"](client, cq)


class TestAdminOnlyDecorator:
    @pytest.mark.asyncio
    async def test_admin_only_allows_admin(self):
        from bot.decorators import admin_only

        mock_app = MagicMock()

        @admin_only(mock_app)
        async def handler(client, update):
            return "ok"

        client = MagicMock()
        member = MagicMock()
        member.status = "administrator"
        client.get_chat_member = AsyncMock(return_value=member)

        update = MagicMock()
        update.from_user.id = 123
        update.message.chat.id = -100123
        update.message.from_user.id = 123

        result = await handler(client, update)
        assert result == "ok"

    @pytest.mark.asyncio
    async def test_admin_only_blocks_non_admin(self):
        from bot.decorators import admin_only

        mock_app = MagicMock()

        @admin_only(mock_app)
        async def handler(client, update):
            return "ok"

        client = MagicMock()
        member = MagicMock()
        member.status = "member"
        client.get_chat_member = AsyncMock(return_value=member)

        update = MagicMock()
        update.from_user.id = 123
        update.message.chat.id = -100123
        update.message.from_user.id = 123
        update.reply_text = AsyncMock()

        result = await handler(client, update)
        assert result is None
        update.reply_text.assert_called_once_with("❌ هذا الأمر للمشرفين فقط")

    @pytest.mark.asyncio
    async def test_admin_only_exception_is_swallowed(self):
        from bot.decorators import admin_only

        mock_app = MagicMock()

        @admin_only(mock_app)
        async def handler(client, update):
            return "ok"

        client = MagicMock()
        client.get_chat_member = AsyncMock(side_effect=Exception("api error"))

        update = MagicMock()
        update.from_user.id = 123
        update.message.chat.id = -100123
        update.message.from_user.id = 123

        result = await handler(client, update)
        assert result == "ok"

    @pytest.mark.asyncio
    async def test_admin_only_no_user_still_passes(self):
        from bot.decorators import admin_only

        mock_app = MagicMock()

        @admin_only(mock_app)
        async def handler(client, update):
            return "ok"

        client = MagicMock()
        update = MagicMock()
        update.from_user = None
        update.message = None

        result = await handler(client, update)
        assert result == "ok"

    @pytest.mark.asyncio
    async def test_admin_only_update_is_message(self):
        from bot.decorators import admin_only

        mock_app = MagicMock()

        @admin_only(mock_app)
        async def handler(client, update):
            return "ok"

        client = MagicMock()
        member = MagicMock()
        member.status = "administrator"
        client.get_chat_member = AsyncMock(return_value=member)

        message = MagicMock()
        message.from_user.id = 123
        message.chat.id = -100123

        result = await handler(client, message)
        assert result == "ok"
