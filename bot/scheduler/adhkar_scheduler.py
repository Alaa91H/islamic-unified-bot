import asyncio
import contextlib
import logging
import random
from datetime import UTC, datetime, timedelta

logger = logging.getLogger(__name__)

MAX_CONSECUTIVE_FAILURES = 3
BASE_BACKOFF_SECONDS = 10
MAX_BACKOFF_SECONDS = 300


def _now_hhmm() -> str:
    return datetime.now(UTC).strftime("%H:%M")


def _today_str() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%d")


def _is_friday() -> bool:
    return datetime.now(UTC).weekday() == 4


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _city_local_now(now_utc: datetime, coords: dict) -> datetime:
    tz_hours = float(coords.get("tz") or 0)
    if coords.get("dst", False):
        tz_hours += 1
    return now_utc + timedelta(hours=tz_hours)


def _get_adhkar():
    from bot.data.adhkar import ADHKAR

    return ADHKAR


def _get_category_keys():
    adhkar = _get_adhkar()
    return list(adhkar.keys())


_MORNING_CATEGORIES = ["morning"]
_EVENING_CATEGORIES = ["evening"]
_FRIDAY_CATEGORIES = ["morning", "supplication", "protection", "gratitude"]


def _pick_random_item(categories: list):
    adhkar = _get_adhkar()
    category = random.choice(categories)
    items = adhkar.get(category, [])
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
    def __init__(self, adhkar_repo, app, tick_seconds: int = 60, group_repo=None):
        self._repo = adhkar_repo
        self._app = app
        self._group_repo = group_repo
        self.TICK_SECONDS = tick_seconds
        self._task = None
        self._running = False
        self._consecutive_failures = 0

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
                self._consecutive_failures = 0
            except Exception:
                self._consecutive_failures += 1
                logger.exception(
                    "⚠️ خطأ في دورة الأذكار (%d/%d)",
                    self._consecutive_failures,
                    MAX_CONSECUTIVE_FAILURES,
                )
            jitter = random.uniform(-0.25, 0.25) * self.TICK_SECONDS
            sleep_time = self.TICK_SECONDS + jitter
            if self._consecutive_failures >= MAX_CONSECUTIVE_FAILURES:
                backoff = min(
                    BASE_BACKOFF_SECONDS
                    * (2 ** (self._consecutive_failures - MAX_CONSECUTIVE_FAILURES)),
                    MAX_BACKOFF_SECONDS,
                )
                sleep_time += backoff
                logger.warning(
                    "🔁 adhkar circuit breaker: زيادة النوم %dث", int(sleep_time)
                )
            try:
                await asyncio.sleep(sleep_time)
            except asyncio.CancelledError:
                break

    async def tick(self) -> None:
        now_utc = _utc_now()
        all_settings = await self._repo.list_all()
        for s in all_settings:
            if not (
                s.interval_enabled
                or s.morning_enabled
                or s.evening_enabled
                or s.friday_enabled
            ):
                continue
            try:
                local_now = await self._local_now_for_group(s.chat_id, now_utc)
                await self._check_group(
                    s,
                    local_now.strftime("%H:%M"),
                    local_now.strftime("%Y-%m-%d"),
                    now_utc,
                    local_now,
                )
            except Exception:
                logger.exception("⚠️ خطأ في أذكار المجموعة %s", s.chat_id)

    async def _local_now_for_group(self, chat_id: int, now_utc: datetime) -> datetime:
        if self._group_repo is None:
            return now_utc
        try:
            group_settings = await self._group_repo.get(chat_id)
        except Exception:
            logger.warning("⚠️ تعذّر جلب توقيت مجموعة الأذكار %s", chat_id)
            return now_utc
        if not group_settings:
            return now_utc
        from bot.prayer.calculator import CityCoordinates

        coords = CityCoordinates.get_city_coords(group_settings.city)
        if not coords:
            return now_utc
        return _city_local_now(now_utc, coords)

    async def _check_group(
        self,
        s,
        now_hhmm: str,
        today: str,
        now_utc: datetime | None = None,
        local_now: datetime | None = None,
    ) -> None:
        chat_id = s.chat_id
        now_utc = now_utc or _utc_now()
        local_now = local_now or now_utc

        if s.interval_enabled and s.last_sent_at:
            try:
                last = datetime.strptime(s.last_sent_at, "%Y-%m-%d %H:%M").replace(
                    tzinfo=UTC
                )
                elapsed = (now_utc - last).total_seconds() / 60
            except (ValueError, TypeError):
                elapsed = s.interval_minutes + 1
            if elapsed >= s.interval_minutes:
                await self._send_adhkar(chat_id, _get_category_keys())
                await self._repo.update_partial(
                    chat_id,
                    last_sent_at=now_utc.strftime("%Y-%m-%d %H:%M"),
                )
                return

        if s.interval_enabled and not s.last_sent_at:
            await self._send_adhkar(chat_id, _get_category_keys())
            await self._repo.update_partial(
                chat_id,
                last_sent_at=now_utc.strftime("%Y-%m-%d %H:%M"),
            )
            return

        if s.morning_enabled and now_hhmm == s.morning_time:
            sent_key = f"adhkar_morning_{today}"
            if not await self._already_sent_today(chat_id, sent_key):
                await self._send_adhkar(
                    chat_id, _MORNING_CATEGORIES, "🌅 **أذكار الصباح**"
                )
                await self._mark_sent(chat_id, sent_key)

        if s.evening_enabled and now_hhmm == s.evening_time:
            sent_key = f"adhkar_evening_{today}"
            if not await self._already_sent_today(chat_id, sent_key):
                await self._send_adhkar(
                    chat_id, _EVENING_CATEGORIES, "🌙 **أذكار المساء**"
                )
                await self._mark_sent(chat_id, sent_key)

        if s.friday_enabled and local_now.weekday() == 4 and now_hhmm == s.friday_time:
            sent_key = f"adhkar_friday_{today}"
            if not await self._already_sent_today(chat_id, sent_key):
                await self._send_adhkar(
                    chat_id, _FRIDAY_CATEGORIES, "📿 **أذكار يوم الجمعة**"
                )
                await self._mark_sent(chat_id, sent_key)

    async def _send_adhkar(
        self, chat_id: int, categories: list, header: str | None = None
    ):
        _category, item = _pick_random_item(categories)
        if not item:
            return
        text = _format_adhkar(item)
        if header:
            text = f"{header}\n\n{text}"
        try:
            await self._app.send_message(chat_id, text)
            logger.info("📿 أُرسل ذكر إلى %s", chat_id)
        except Exception as e:
            logger.exception("❌ فشل إرسال ذكر إلى %s: %s", chat_id, e)

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
