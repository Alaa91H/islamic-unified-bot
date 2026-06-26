import asyncio
import contextlib
import logging
import random
from datetime import datetime, timezone

from bot.data.adhkar import ADHKAR

logger = logging.getLogger(__name__)

_CATEGORY_KEYS = list(ADHKAR.keys())

_MORNING_CATEGORIES = ["morning"]
_EVENING_CATEGORIES = ["evening"]
_FRIDAY_CATEGORIES = ["morning", "supplication", "protection", "gratitude"]


def _now_hhmm() -> str:
    return datetime.now(timezone.utc).strftime("%H:%M")


def _today_str() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _is_friday() -> bool:
    return datetime.now(timezone.utc).weekday() == 4


def _pick_random_item(categories: list[str]):
    category = random.choice(categories)
    items = ADHKAR.get(category, [])
    if not items:
        return None, None
    item = random.choice(items)
    return category, item


def _format_adhkar(item: dict) -> str:
    title = item.get("title", "ذكر")
    text = item.get("text", "")
    benefit = item.get("benefit", "")
    return f"**{title}**\n\n{text}\n\n💎 {benefit}"


class AdhkarScheduler:
    def __init__(self, adhkar_repo, app, tick_seconds: int = 30):
        self._repo = adhkar_repo
        self._app = app
        self.TICK_SECONDS = tick_seconds
        self._task: asyncio.Task | None = None
        self._running = False

    async def start(self) -> None:
        if self._task is not None:
            return
        self._running = True
        self._task = asyncio.create_task(self._loop())
        logger.info("✅ بدأت حلقة الأذكار (كل %sث)", self.TICK_SECONDS)

    async def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task
            self._task = None
        logger.info("🛑 توقفت حلقة الأذكار")

    async def _loop(self) -> None:
        while self._running:
            try:
                await self.tick()
            except Exception:
                logger.exception("⚠️ خطأ في دورة الأذكار (ستستأنف)")
            await asyncio.sleep(self.TICK_SECONDS)

    async def tick(self) -> None:
        now_hhmm = _now_hhmm()
        today = _today_str()
        for s in await self._repo.list_all():
            if not (
                s.interval_enabled
                or s.morning_enabled
                or s.evening_enabled
                or s.friday_enabled
            ):
                continue
            try:
                await self._check_group(s, now_hhmm, today)
            except Exception:
                logger.exception("⚠️ خطأ في أذكار المجموعة %s", s.chat_id)

    async def _check_group(self, s, now_hhmm: str, today: str) -> None:
        chat_id = s.chat_id

        # الأذكار الدورية
        if s.interval_enabled and s.last_sent_at:
            try:
                last = datetime.strptime(s.last_sent_at, "%Y-%m-%d %H:%M")
                elapsed = (datetime.now(timezone.utc) - last).total_seconds() / 60
            except (ValueError, TypeError):
                elapsed = s.interval_minutes + 1
            if elapsed >= s.interval_minutes:
                await self._send_adhkar(chat_id, _CATEGORY_KEYS)
                await self._repo.update_partial(
                    chat_id,
                    last_sent_at=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M"),
                )
                return

        # أول تفعيل للدوري — نرسل فوراً (إذا ما أُرسل شيء قبل)
        if s.interval_enabled and not s.last_sent_at:
            await self._send_adhkar(chat_id, _CATEGORY_KEYS)
            await self._repo.update_partial(
                chat_id,
                last_sent_at=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M"),
            )
            return

        # أذكار الصباح
        if s.morning_enabled and now_hhmm == s.morning_time:
            sent_key = f"adhkar_morning_{today}"
            if not await self._already_sent_today(chat_id, sent_key):
                await self._send_adhkar(
                    chat_id, _MORNING_CATEGORIES, "🌅 **أذكار الصباح**"
                )
                await self._mark_sent(chat_id, sent_key)

        # أذكار المساء
        if s.evening_enabled and now_hhmm == s.evening_time:
            sent_key = f"adhkar_evening_{today}"
            if not await self._already_sent_today(chat_id, sent_key):
                await self._send_adhkar(
                    chat_id, _EVENING_CATEGORIES, "🌙 **أذكار المساء**"
                )
                await self._mark_sent(chat_id, sent_key)

        # أذكار الجمعة
        if s.friday_enabled and _is_friday() and now_hhmm == s.friday_time:
            sent_key = f"adhkar_friday_{today}"
            if not await self._already_sent_today(chat_id, sent_key):
                await self._send_adhkar(
                    chat_id, _FRIDAY_CATEGORIES, "📿 **أذكار يوم الجمعة**"
                )
                await self._mark_sent(chat_id, sent_key)

    async def _send_adhkar(
        self, chat_id: int, categories: list[str], header: str = None
    ) -> None:
        category, item = _pick_random_item(categories)
        if not item:
            return
        text = _format_adhkar(item)
        if header:
            text = f"{header}\n\n{text}"
        try:
            await self._app.send_message(chat_id, text)
            logger.info("📿 أُرسل ذكر إلى %s", chat_id)
        except Exception as e:
            logger.error("❌ فشل إرسال ذكر إلى %s: %s", chat_id, e)

    async def _already_sent_today(self, chat_id: int, key: str) -> bool:
        row = await self._repo._db.fetchone(
            "SELECT 1 FROM adhkar_sent WHERE chat_id=? AND sent_key=?",
            (chat_id, key),
        )
        return row is not None

    async def _mark_sent(self, chat_id: int, key: str) -> None:
        await self._repo._db.execute(
            "INSERT OR IGNORE INTO adhkar_sent (chat_id, sent_key) VALUES (?,?)",
            (chat_id, key),
        )
