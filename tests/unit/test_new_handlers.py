import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.fixture(scope="session", autouse=True)
def _pyrogram_event_loop():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    yield
    loop.close()


def _make_admin_deps():
    """Creates deps with admin-only support: get_chat_member returns admin."""
    deps = MagicMock()
    deps.settings = MagicMock()
    deps.settings.is_owner = MagicMock(return_value=True)
    deps.settings.quran_stream_url = "https://example.com/"
    deps.settings.music_dir = "/tmp/music"
    deps.stream_manager = AsyncMock()
    deps.stream_manager.play = AsyncMock(return_value=True)
    deps.stream_manager.stop = AsyncMock(return_value=True)
    deps.adhkar_repo = AsyncMock()
    deps.adhkar_repo.get = AsyncMock(return_value=None)
    deps.adhkar_repo.upsert = AsyncMock()
    return deps


def _make_admin_client():
    """Creates client mock where get_chat_member returns admin."""
    client = MagicMock()
    member = MagicMock()
    member.status = "administrator"
    client.get_chat_member = AsyncMock(return_value=member)
    return client


def _capture_handlers(app, module, deps):
    """Registers module handlers and captures them."""
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

    module.register(app, deps)
    return captured


# ============================================================
# module-level functions
# ============================================================

class TestGroupQuranModuleFunctions:
    def test_get_surah_name_known(self):
        from bot.handlers.group_quran import _get_surah_name

        assert _get_surah_name(1) == "الفاتحة"
        assert _get_surah_name(36) == "يس"
        assert _get_surah_name(114) == "الناس"

    def test_get_surah_name_unknown(self):
        from bot.handlers.group_quran import _get_surah_name

        assert _get_surah_name(999) == ""

    def test_messages_dict_has_required_keys(self):
        from bot.handlers.group_quran import MESSAGES

        for key in ("not_group", "no_number", "invalid", "playing", "failed", "stopped", "not_streaming"):
            assert key in MESSAGES


class TestGroupAdhkarModuleFunctions:
    def test_parse_bool_true_values(self):
        from bot.handlers.group_adhkar import _parse_bool

        assert _parse_bool("1") is True
        assert _parse_bool("true") is True
        assert _parse_bool("نعم") is True
        assert _parse_bool("تشغيل") is True

    def test_parse_bool_false_values(self):
        from bot.handlers.group_adhkar import _parse_bool

        assert _parse_bool("0") is False
        assert _parse_bool("false") is False
        assert _parse_bool("لا") is False
        assert _parse_bool("تعطيل") is False

    def test_parse_bool_case_insensitive(self):
        from bot.handlers.group_adhkar import _parse_bool

        assert _parse_bool("True") is True
        assert _parse_bool("FALSE") is False

    def test_parse_bool_unknown_returns_none(self):
        from bot.handlers.group_adhkar import _parse_bool

        assert _parse_bool("maybe") is None


class TestQuranTextModuleFunctions:
    def test_get_juz_first_juz(self):
        from bot.handlers.quran_text import _get_juz

        assert _get_juz(1) == "1"

    def test_get_juz_last_juz(self):
        from bot.handlers.quran_text import _get_juz

        assert _get_juz(114) == "30"

    def test_get_juz_middle(self):
        from bot.handlers.quran_text import _get_juz

        assert _get_juz(18) == "15-21"


# ============================================================
# Owner handler tests (HAS_STREAMING=False path)
# ============================================================

class TestOwnerStreamingUnavailable:
    def test_register_streaming_unavailable_registers_handlers(self):
        from bot.handlers.owner import _register_streaming_unavailable

        app = MagicMock()
        app.on_message = MagicMock(return_value=lambda fn: fn)

        settings = MagicMock()
        _register_streaming_unavailable(app, settings)
        assert app.on_message.call_count >= 2

    @pytest.mark.asyncio
    async def test_stream_unavailable_replies(self):
        from bot.handlers.owner import register as owner_register

        app = MagicMock()
        captured = {}
        app.on_message = MagicMock(return_value=lambda fn: fn)

        def capture_on_message(filter_):
            def decorator(func):
                captured[func.__name__] = func
                return func
            return decorator

        app.on_message = capture_on_message
        app.on_callback_query = MagicMock(return_value=lambda fn: fn)

        deps = _make_admin_deps()
        with patch("bot.handlers.owner.HAS_STREAMING", False):
            owner_register(app, deps)

        if "stream_unavailable" in captured:
            client = MagicMock()
            message = MagicMock()
            message.reply_text = AsyncMock()
            message.command = ["stream"]
            message.from_user = MagicMock()
            message.from_user.id = 1

            await captured["stream_unavailable"](client, message)
            message.reply_text.assert_called_once()
            assert "غير متاح" in message.reply_text.call_args[0][0]

    @pytest.mark.asyncio
    async def test_stop_unavailable_replies(self):
        from bot.handlers.owner import register as owner_register

        app = MagicMock()
        captured = {}

        def capture_on_message(filter_):
            def decorator(func):
                captured[func.__name__] = func
                return func
            return decorator

        app.on_message = capture_on_message
        app.on_callback_query = MagicMock(return_value=lambda fn: fn)

        deps = _make_admin_deps()
        with patch("bot.handlers.owner.HAS_STREAMING", False):
            owner_register(app, deps)

        if "stop_unavailable" in captured:
            client = MagicMock()
            message = MagicMock()
            message.reply_text = AsyncMock()
            message.command = ["stop"]
            message.from_user = MagicMock()
            message.from_user.id = 1

            await captured["stop_unavailable"](client, message)
            message.reply_text.assert_called_once()
            assert "غير متاح" in message.reply_text.call_args[0][0]


# ============================================================
# Group Quran handler execution tests
# ============================================================

class TestGroupQuranHandlerExecution:
    def _capture(self, app, deps):
        import bot.handlers.group_quran
        return _capture_handlers(app, bot.handlers.group_quran, deps)

    @pytest.mark.asyncio
    async def test_quran_play_no_number(self):
        app = MagicMock()
        captured = self._capture(app, _make_admin_deps())

        if "quran_play" in captured:
            client = _make_admin_client()
            message = MagicMock()
            message.chat.id = -100123
            message.command = ["quran"]
            message.reply_text = AsyncMock()

            await captured["quran_play"](client, message)
            message.reply_text.assert_called_once()
            assert "استخدم" in message.reply_text.call_args[0][0]

    @pytest.mark.asyncio
    async def test_quran_play_invalid_number(self):
        app = MagicMock()
        captured = self._capture(app, _make_admin_deps())

        if "quran_play" in captured:
            client = _make_admin_client()
            message = MagicMock()
            message.chat.id = -100123
            message.command = ["quran", "999"]
            message.reply_text = AsyncMock()

            await captured["quran_play"](client, message)
            message.reply_text.assert_called_once()
            assert "1-114" in message.reply_text.call_args[0][0]

    @pytest.mark.asyncio
    async def test_quran_play_valid(self):
        deps = _make_admin_deps()
        deps.stream_manager.play = AsyncMock(return_value=True)

        app = MagicMock()
        captured = self._capture(app, deps)

        if "quran_play" in captured:
            client = _make_admin_client()
            message = MagicMock()
            message.chat.id = -100123
            message.command = ["quran", "1"]
            message.reply_text = AsyncMock()

            await captured["quran_play"](client, message)
            message.reply_text.assert_called_once()
            assert "الفاتحة" in message.reply_text.call_args[0][0]

    @pytest.mark.asyncio
    async def test_quran_play_failed(self):
        deps = _make_admin_deps()
        deps.stream_manager.play = AsyncMock(return_value=False)

        app = MagicMock()
        captured = self._capture(app, deps)

        if "quran_play" in captured:
            client = _make_admin_client()
            message = MagicMock()
            message.chat.id = -100123
            message.command = ["quran", "1"]
            message.reply_text = AsyncMock()

            await captured["quran_play"](client, message)
            message.reply_text.assert_called_once()
            assert "فشل" in message.reply_text.call_args[0][0]

    @pytest.mark.asyncio
    async def test_quran_stop_success(self):
        deps = _make_admin_deps()
        deps.stream_manager.stop = AsyncMock(return_value=True)

        app = MagicMock()
        captured = self._capture(app, deps)

        if "quran_stop" in captured:
            client = _make_admin_client()
            message = MagicMock()
            message.chat.id = -100123
            message.command = ["stop"]
            message.reply_text = AsyncMock()

            await captured["quran_stop"](client, message)
            message.reply_text.assert_called_once()
            assert "إيقاف" in message.reply_text.call_args[0][0]

    @pytest.mark.asyncio
    async def test_quran_stop_not_streaming(self):
        deps = _make_admin_deps()
        deps.stream_manager.stop = AsyncMock(return_value=False)

        app = MagicMock()
        captured = self._capture(app, deps)

        if "quran_stop" in captured:
            client = _make_admin_client()
            message = MagicMock()
            message.chat.id = -100123
            message.command = ["stop"]
            message.reply_text = AsyncMock()

            await captured["quran_stop"](client, message)
            message.reply_text.assert_called_once()
            assert "لا يوجد بث" in message.reply_text.call_args[0][0]


# ============================================================
# Group Adhkar handler execution tests
# ============================================================

class TestGroupAdhkarHandlerExecution:
    def _capture(self, app, deps):
        import bot.handlers.group_adhkar
        return _capture_handlers(app, bot.handlers.group_adhkar, deps)

    @pytest.mark.asyncio
    async def test_adhkar_cmd_replies(self):
        app = MagicMock()
        captured = self._capture(app, _make_admin_deps())

        if "adhkar_cmd" in captured:
            client = _make_admin_client()
            message = MagicMock()
            message.chat.id = -100123
            message.reply_text = AsyncMock()

            await captured["adhkar_cmd"](client, message)
            message.reply_text.assert_called_once()
            assert "إعدادات الأذكار" in message.reply_text.call_args[0][0]

    @pytest.mark.asyncio
    async def test_adhk_toggle_interval(self):
        deps = _make_admin_deps()
        adhk_settings = MagicMock()
        adhk_settings.interval_enabled = False
        adhk_settings.morning_enabled = False
        adhk_settings.evening_enabled = False
        adhk_settings.friday_enabled = False
        deps.adhkar_repo.get = AsyncMock(return_value=adhk_settings)

        app = MagicMock()
        captured = self._capture(app, deps)

        if "adhk_toggle" in captured:
            client = _make_admin_client()
            cq = MagicMock()
            cq.data = "adhk_toggle:interval:-100123"
            cq.message.edit_reply_markup = AsyncMock()
            cq.answer = AsyncMock()

            await captured["adhk_toggle"](client, cq)
            cq.answer.assert_called_once_with("✅ تم التحديث")

    @pytest.mark.asyncio
    async def test_adhk_toggle_morning(self):
        deps = _make_admin_deps()
        adhk_settings = MagicMock()
        adhk_settings.interval_enabled = False
        adhk_settings.morning_enabled = False
        adhk_settings.evening_enabled = False
        adhk_settings.friday_enabled = False
        deps.adhkar_repo.get = AsyncMock(return_value=adhk_settings)

        app = MagicMock()
        captured = self._capture(app, deps)

        if "adhk_toggle" in captured:
            client = _make_admin_client()
            cq = MagicMock()
            cq.data = "adhk_toggle:morning:-100123"
            cq.message.edit_reply_markup = AsyncMock()
            cq.answer = AsyncMock()

            await captured["adhk_toggle"](client, cq)
            cq.answer.assert_called_once()

    @pytest.mark.asyncio
    async def test_adhk_back(self):
        deps = _make_admin_deps()
        deps.adhkar_repo.get = AsyncMock(return_value=None)

        app = MagicMock()
        captured = self._capture(app, deps)

        if "adhk_back" in captured:
            client = _make_admin_client()
            cq = MagicMock()
            cq.data = "adhk_back:-100123"
            cq.message.edit_text = AsyncMock()

            await captured["adhk_back"](client, cq)
            cq.message.edit_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_adhk_close(self):
        app = MagicMock()
        captured = self._capture(app, _make_admin_deps())

        if "adhk_close" in captured:
            client = _make_admin_client()
            cq = MagicMock()
            cq.data = "adhk_close"
            cq.message.delete = AsyncMock()

            await captured["adhk_close"](client, cq)
            cq.message.delete.assert_called_once()


# ============================================================
# Quran Text handler execution tests
# ============================================================

class TestQuranTextHandlerExecution:
    def _capture(self, app, deps):
        import bot.handlers.quran_text
        return _capture_handlers(app, bot.handlers.quran_text, deps)

    @pytest.mark.asyncio
    async def test_quran_text_cmd_replies(self):
        app = MagicMock()
        captured = self._capture(app, MagicMock())

        if "quran_text_cmd" in captured:
            client = MagicMock()
            message = MagicMock()
            message.reply_text = AsyncMock()
            message.from_user = MagicMock()

            await captured["quran_text_cmd"](client, message)
            message.reply_text.assert_called_once()
            assert "النص والتفسير" in message.reply_text.call_args[0][0]

    @pytest.mark.asyncio
    async def test_quran_text_callback_info(self):
        app = MagicMock()
        captured = self._capture(app, MagicMock())

        if "quran_text_callback" in captured:
            client = MagicMock()
            cq = MagicMock()
            cq.data = "qts:1:0"
            cq.message.edit_text = AsyncMock()
            cq.answer = AsyncMock()

            await captured["quran_text_callback"](client, cq)
            cq.message.edit_text.assert_called_once()
            assert "الفاتحة" in cq.message.edit_text.call_args[0][0]
            cq.answer.assert_called_once()

    @pytest.mark.asyncio
    async def test_quran_text_callback_info_explicit(self):
        app = MagicMock()
        captured = self._capture(app, MagicMock())

        if "quran_text_callback" in captured:
            client = MagicMock()
            cq = MagicMock()
            cq.data = "qts:1:0:info"
            cq.message.edit_text = AsyncMock()
            cq.answer = AsyncMock()

            await captured["quran_text_callback"](client, cq)
            cq.message.edit_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_quran_search_cmd_no_keyword(self):
        app = MagicMock()
        captured = self._capture(app, MagicMock())

        if "quran_search_cmd" in captured:
            client = MagicMock()
            message = MagicMock()
            message.command = ["quran_search"]
            message.reply_text = AsyncMock()
            message.from_user = MagicMock()

            await captured["quran_search_cmd"](client, message)
            message.reply_text.assert_called_once()
            assert "استخدم" in message.reply_text.call_args[0][0]


# ============================================================
# Islamic Names handler execution tests
# ============================================================

class TestIslamicNamesHandlerExecution:
    def _capture(self, app, deps):
        import bot.handlers.islamic_names
        return _capture_handlers(app, bot.handlers.islamic_names, deps)

    @pytest.mark.asyncio
    async def test_names_cmd_replies(self):
        app = MagicMock()
        captured = self._capture(app, MagicMock())

        if "names_cmd" in captured:
            client = MagicMock()
            message = MagicMock()
            message.reply_text = AsyncMock()
            message.from_user = MagicMock()

            await captured["names_cmd"](client, message)
            message.reply_text.assert_called_once()
            assert "أسماء الله الحسنى" in message.reply_text.call_args[0][0]

    @pytest.mark.asyncio
    async def test_names_callback_page(self):
        app = MagicMock()
        captured = self._capture(app, MagicMock())

        if "names_callback" in captured:
            client = MagicMock()
            cq = MagicMock()
            cq.data = "names:page:1"
            cq.message.edit_text = AsyncMock()
            cq.answer = AsyncMock()

            await captured["names_callback"](client, cq)
            cq.message.edit_text.assert_called_once()
            cq.answer.assert_called_once()

    @pytest.mark.asyncio
    async def test_names_callback_show_first(self):
        app = MagicMock()
        captured = self._capture(app, MagicMock())

        if "names_callback" in captured:
            client = MagicMock()
            cq = MagicMock()
            cq.data = "names:show:1"
            cq.message.edit_text = AsyncMock()
            cq.answer = AsyncMock()

            await captured["names_callback"](client, cq)
            cq.message.edit_text.assert_called_once()
            assert "الرحمن" in cq.message.edit_text.call_args[0][0]
            cq.answer.assert_called_once()

    @pytest.mark.asyncio
    async def test_names_callback_show_last(self):
        app = MagicMock()
        captured = self._capture(app, MagicMock())

        if "names_callback" in captured:
            client = MagicMock()
            cq = MagicMock()
            cq.data = "names:show:99"
            cq.message.edit_text = AsyncMock()
            cq.answer = AsyncMock()

            await captured["names_callback"](client, cq)
            cq.message.edit_text.assert_called_once()
            assert "الصبور" in cq.message.edit_text.call_args[0][0]

    @pytest.mark.asyncio
    async def test_names_callback_close(self):
        app = MagicMock()
        captured = self._capture(app, MagicMock())

        if "names_callback" in captured:
            client = MagicMock()
            cq = MagicMock()
            cq.data = "names:close"
            cq.message.delete = AsyncMock()
            cq.answer = AsyncMock()

            await captured["names_callback"](client, cq)
            cq.message.delete.assert_called_once()
            cq.answer.assert_called_once()


# ============================================================
# Hadith handler execution tests
# ============================================================

class TestHadithHandlerExecution:
    def _capture(self, app, deps):
        import bot.handlers.hadith
        return _capture_handlers(app, bot.handlers.hadith, deps)

    @pytest.mark.asyncio
    async def test_hadith_cmd_replies(self):
        app = MagicMock()
        captured = self._capture(app, MagicMock())

        if "hadith_cmd" in captured:
            client = MagicMock()
            message = MagicMock()
            message.reply_text = AsyncMock()
            message.from_user = MagicMock()

            await captured["hadith_cmd"](client, message)
            message.reply_text.assert_called_once()
            assert "مكتبة الحديث" in message.reply_text.call_args[0][0]

    @pytest.mark.asyncio
    async def test_hadith_callback_book_first_page(self):
        app = MagicMock()
        captured = self._capture(app, MagicMock())

        if "hadith_callback" in captured:
            client = MagicMock()
            cq = MagicMock()
            cq.data = "hadith:book:bukhari:1"
            cq.message.edit_text = AsyncMock()
            cq.answer = AsyncMock()

            await captured["hadith_callback"](client, cq)
            cq.message.edit_text.assert_called_once()
            assert "صحيح البخاري" in cq.message.edit_text.call_args[0][0]
            cq.answer.assert_called_once()

    @pytest.mark.asyncio
    async def test_hadith_callback_book_invalid(self):
        app = MagicMock()
        captured = self._capture(app, MagicMock())

        if "hadith_callback" in captured:
            client = MagicMock()
            cq = MagicMock()
            cq.data = "hadith:book:nonexistent:1"
            cq.answer = AsyncMock()

            await captured["hadith_callback"](client, cq)
            cq.answer.assert_called_once_with("❌ كتاب غير معروف")

    @pytest.mark.asyncio
    async def test_hadith_callback_books_list(self):
        app = MagicMock()
        captured = self._capture(app, MagicMock())

        if "hadith_callback" in captured:
            client = MagicMock()
            cq = MagicMock()
            cq.data = "hadith:books"
            cq.message.edit_text = AsyncMock()
            cq.answer = AsyncMock()

            await captured["hadith_callback"](client, cq)
            cq.message.edit_text.assert_called_once()
            assert "مكتبة الحديث" in cq.message.edit_text.call_args[0][0]
            cq.answer.assert_called_once()

    @pytest.mark.asyncio
    async def test_hadith_callback_get_success(self):
        hadith_data = {
            "number": 1,
            "arab": "نص الحديث بالعربية",
            "id": "Terjemahan Indonesia",
        }

        app = MagicMock()
        with patch("bot.data.hadith_data.get_hadith", new=AsyncMock(return_value=hadith_data)):
            captured = self._capture(app, MagicMock())

        if "hadith_callback" in captured:
            client = MagicMock()
            cq = MagicMock()
            cq.data = "hadith:get:bukhari:1"
            cq.message.edit_text = AsyncMock()
            cq.answer = AsyncMock()

            with patch("bot.data.hadith_data.format_hadith", return_value="متن الحديث"):
                await captured["hadith_callback"](client, cq)
                cq.message.edit_text.assert_called_once()
                cq.answer.assert_called_once()

    @pytest.mark.asyncio
    async def test_hadith_callback_get_not_found(self):
        app = MagicMock()
        with patch("bot.data.hadith_data.get_hadith", new=AsyncMock(return_value=None)):
            captured = self._capture(app, MagicMock())

        if "hadith_callback" in captured:
            client = MagicMock()
            cq = MagicMock()
            cq.data = "hadith:get:bukhari:1"
            cq.answer = AsyncMock()

            await captured["hadith_callback"](client, cq)
            cq.answer.assert_called_once_with("❌ لم يتم العثور على الحديث")

    @pytest.mark.asyncio
    async def test_hadith_callback_noop(self):
        app = MagicMock()
        captured = self._capture(app, MagicMock())

        if "hadith_callback" in captured:
            client = MagicMock()
            cq = MagicMock()
            cq.data = "hadith:_"
            cq.answer = AsyncMock()

            await captured["hadith_callback"](client, cq)
            cq.answer.assert_called_once()

    @pytest.mark.asyncio
    async def test_hadith_inline_known_book(self):
        app = MagicMock()
        captured = self._capture(app, MagicMock())

        if "hadith_inline" in captured:
            client = MagicMock()
            message = MagicMock()
            message.text = "/hadith bukhari"
            message.command = ["hadith", "bukhari"]
            message.reply_text = AsyncMock()
            message.from_user = MagicMock()

            await captured["hadith_inline"](client, message)
            message.reply_text.assert_called_once()
            assert "صحيح البخاري" in message.reply_text.call_args[0][0]

    @pytest.mark.asyncio
    async def test_hadith_inline_unknown_book(self):
        app = MagicMock()
        captured = self._capture(app, MagicMock())

        if "hadith_inline" in captured:
            client = MagicMock()
            message = MagicMock()
            message.text = "/hadith nonexistent"
            message.command = ["hadith", "nonexistent"]
            message.reply_text = AsyncMock()
            message.from_user = MagicMock()

            await captured["hadith_inline"](client, message)
            message.reply_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_hadith_inline_book_and_number_success(self):
        hadith_data = {
            "number": 1,
            "arab": "نص الحديث بالعربية",
            "id": "Terjemahan Indonesia",
        }

        app = MagicMock()
        with patch("bot.data.hadith_data.get_hadith", new=AsyncMock(return_value=hadith_data)):
            captured = self._capture(app, MagicMock())

        if "hadith_inline" in captured:
            client = MagicMock()
            message = MagicMock()
            message.text = "/hadith bukhari 1"
            message.command = ["hadith", "bukhari", "1"]
            message.reply_text = AsyncMock()
            message.from_user = MagicMock()

            with patch("bot.data.hadith_data.format_hadith", return_value="متن الحديث"):
                await captured["hadith_inline"](client, message)
                message.reply_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_hadith_inline_book_and_number_not_found(self):
        app = MagicMock()
        with patch("bot.data.hadith_data.get_hadith", new=AsyncMock(return_value=None)):
            captured = self._capture(app, MagicMock())

        if "hadith_inline" in captured:
            client = MagicMock()
            message = MagicMock()
            message.text = "/hadith bukhari 1"
            message.command = ["hadith", "bukhari", "1"]
            message.reply_text = AsyncMock()
            message.from_user = MagicMock()

            await captured["hadith_inline"](client, message)
            message.reply_text.assert_called_once()
            assert "لم يتم العثور" in message.reply_text.call_args[0][0]

    @pytest.mark.asyncio
    async def test_hadith_inline_invalid_number(self):
        app = MagicMock()
        captured = self._capture(app, MagicMock())

        if "hadith_inline" in captured:
            client = MagicMock()
            message = MagicMock()
            message.text = "/hadith bukhari abc"
            message.command = ["hadith", "bukhari", "abc"]
            message.reply_text = AsyncMock()
            message.from_user = MagicMock()

            await captured["hadith_inline"](client, message)
            message.reply_text.assert_called_once()
            assert "استخدم" in message.reply_text.call_args[0][0]
