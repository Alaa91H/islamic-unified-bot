"""مدير بث صوتي متسامح مع الأعطال فوق PyTgCalls.

يعزل هذا المكوّن الاعتماد الأصلي للبث، ويمنع تجاوز عدد البثات المسموح، ويستخدم
إعادة محاولة محصورة زمنيًا. لا ينشئ البوت المكالمة الصوتية؛ يجب أن تبدأها إدارة
المجموعة في Telegram قبل تشغيل الصوت.
"""

from __future__ import annotations

import asyncio
import logging
import random
from pathlib import Path
from typing import Any

from bot.time_utils import utc_now

logger = logging.getLogger(__name__)
MAX_RETRY_DELAY_SECONDS = 60.0


def _import_pytgcalls():
    """استيراد PyTgCalls وواجهاته كسليًا ليسهل الاستبدال في الاختبارات."""
    from pytgcalls import PyTgCalls
    from pytgcalls.exceptions import NotInCallError
    from pytgcalls.types import AudioQuality, MediaStream

    return PyTgCalls, NotInCallError, AudioQuality, MediaStream


class StreamManager:
    """مدير البث مع حد تزامن وإعادة محاولة وإيقاف منظّم."""

    def __init__(
        self,
        app: Any,
        max_reconnect: int = 10,
        base_delay: int = 5,
        default_duration_min: int = 120,
        audio_quality: str = "studio",
        max_concurrent_streams: int = 2,
        pytgcalls_factory=None,
        import_func=None,
    ) -> None:
        if max_concurrent_streams < 1:
            raise ValueError("max_concurrent_streams must be at least 1")

        self._app = app
        self.max_reconnect = max_reconnect
        self.base_delay = base_delay
        self.default_duration_min = default_duration_min
        self.max_concurrent_streams = max_concurrent_streams
        self._audio_quality_str = audio_quality
        self._streams: dict[int, dict[str, Any]] = {}
        self._timers: dict[int, asyncio.Task[None]] = {}
        self._pending_chats: set[int] = set()
        self._state_lock = asyncio.Lock()
        self._jitter = random.SystemRandom()
        self._started = False
        self._import_func = import_func or _import_pytgcalls
        if pytgcalls_factory is None:
            pytgcalls_factory, _, _, _ = self._import_func()
        self.pytgcalls = pytgcalls_factory(app)

    async def start(self) -> None:
        """بدء عميل المكالمات وتسجيل إعادة البث الاختيارية عند التحديث."""
        if self._started:
            return
        await self.pytgcalls.start()

        @self.pytgcalls.on_update()
        async def _on_update(_client, update) -> None:
            chat_id = getattr(update, "chat_id", None)
            if chat_id is None:
                return
            info = self._streams.get(chat_id)
            if info and info.get("loop") and info.get("status") == "active":
                logger.info("إعادة بث دوري في %s", chat_id)
                await self.play(
                    chat_id,
                    info["url"],
                    info["title"],
                    loop=True,
                    duration_min=info.get("duration_min"),
                    audio_quality=info.get("audio_quality"),
                )

        self._started = True
        logger.info("خدمة المكالمات جاهزة")

    async def stop_all(self) -> None:
        """إيقاف كل المكالمات والمؤقتات وإغلاق عميل البث إن كانت واجهته تدعمه."""
        active_chat_ids = list(self._streams)
        if active_chat_ids:
            await asyncio.gather(
                *(self.stop(chat_id) for chat_id in active_chat_ids),
                return_exceptions=True,
            )
        for timer in self._timers.values():
            timer.cancel()
        self._timers.clear()
        self._streams.clear()
        self._pending_chats.clear()

        stop_client = getattr(self.pytgcalls, "stop", None)
        if callable(stop_client) and self._started:
            try:
                await stop_client()
            except Exception:
                logger.exception("تعذر إيقاف عميل PyTgCalls")
        self._started = False

    async def _reserve_chat(self, chat_id: int) -> bool:
        """حجز سعة بث قبل تشغيل المكتبة الخارجية، مع السماح بتحديث البث القائم."""
        async with self._state_lock:
            if chat_id in self._streams or chat_id in self._pending_chats:
                self._pending_chats.add(chat_id)
                return True
            if (
                len(self._streams) + len(self._pending_chats)
                >= self.max_concurrent_streams
            ):
                logger.warning(
                    "رفض بث جديد في %s: حد البث المتزامن (%s) ممتلئ",
                    chat_id,
                    self.max_concurrent_streams,
                )
                return False
            self._pending_chats.add(chat_id)
            return True

    async def _release_reservation(self, chat_id: int) -> None:
        async with self._state_lock:
            self._pending_chats.discard(chat_id)

    def _retry_delay(self, attempt: int) -> float:
        exponential = self.base_delay * (2**attempt)
        return min(exponential, MAX_RETRY_DELAY_SECONDS) + self._jitter.uniform(0, 1)

    async def play(
        self,
        chat_id: int,
        url: str,
        title: str = "بث",
        loop: bool = False,
        duration_min: int | None = None,
        attempts: int = 0,
        audio_quality: str | None = None,
    ) -> bool:
        """بدء بث، مع إعادة المحاولة للأخطاء العابرة ضمن سقف زمني واضح."""
        if not await self._reserve_chat(chat_id):
            return False

        try:
            _, not_in_call_error, audio_quality_type, media_stream = self._import_func()
            quality_map = {
                "low": audio_quality_type.LOW,
                "medium": audio_quality_type.MEDIUM,
                "high": audio_quality_type.HIGH,
                "studio": audio_quality_type.STUDIO,
            }
            selected_quality = audio_quality or self._audio_quality_str
            media = media_stream(
                url,
                audio_parameters=quality_map.get(
                    selected_quality, audio_quality_type.STUDIO
                ),
                ffmpeg_parameters="-af volume=1.5",
            )

            for attempt in range(attempts, self.max_reconnect + 1):
                try:
                    await self.pytgcalls.play(chat_id, media)
                    break
                except not_in_call_error:
                    logger.info("لا توجد مكالمة صوتية في %s", chat_id)
                    return False
                except Exception as exc:
                    error_text = str(exc)
                    if (
                        "BOT_METHOD_INVALID" in error_text
                        or "NotInCallError" in error_text
                    ):
                        logger.info("يجب بدء مكالمة صوتية يدويًا في %s", chat_id)
                        return False
                    if attempt >= self.max_reconnect:
                        logger.exception(
                            "فشل البث في %s بعد %s محاولات",
                            chat_id,
                            self.max_reconnect + 1,
                        )
                        return False
                    delay = self._retry_delay(attempt)
                    logger.warning(
                        "فشل البث في %s (%s/%s): %s؛ إعادة بعد %.1f ث",
                        chat_id,
                        attempt + 1,
                        self.max_reconnect + 1,
                        exc,
                        delay,
                    )
                    await asyncio.sleep(delay)

            duration = (
                duration_min if duration_min is not None else self.default_duration_min
            )
            async with self._state_lock:
                self._streams[chat_id] = {
                    "url": url,
                    "title": title,
                    "started_at": utc_now(),
                    "status": "active",
                    "loop": loop,
                    "duration_min": duration,
                    "audio_quality": selected_quality,
                }
            self._schedule_stop(chat_id, duration)
            logger.info(
                "بث نشط في %s: %s (loop=%s, dur=%smin)", chat_id, title, loop, duration
            )
            return True
        finally:
            await self._release_reservation(chat_id)

    def _schedule_stop(self, chat_id: int, duration_min: int) -> None:
        old_timer = self._timers.get(chat_id)
        if old_timer:
            old_timer.cancel()

        async def _auto_stop() -> None:
            try:
                await asyncio.sleep(duration_min * 60)
                logger.info("انتهت مدة البث في %s", chat_id)
                await self.stop(chat_id)
            except asyncio.CancelledError:
                return

        self._timers[chat_id] = asyncio.create_task(_auto_stop())

    async def stop(self, chat_id: int) -> bool:
        """إيقاف بث واحد وإخلاء حجز السعة حتى عند خطأ المكتبة الخارجية."""
        timer = self._timers.pop(chat_id, None)
        if timer:
            timer.cancel()
        try:
            await self.pytgcalls.leave_call(chat_id)
        except Exception:
            logger.exception("تعذر مغادرة المكالمة الصوتية في %s", chat_id)
        finally:
            await self._release_reservation(chat_id)

        existed = self._streams.pop(chat_id, None) is not None
        if existed:
            logger.info("أوقف البث في %s", chat_id)
        return existed

    def active_streams(self) -> dict[int, dict[str, Any]]:
        """إرجاع لقطة غير قابلة لتعديل حالة البث الداخلية."""
        return {chat_id: data.copy() for chat_id, data in self._streams.items()}

    def get_local_files(
        self, folder_path: str | None = None
    ) -> dict[int, dict[str, Any]]:
        """مسح ملفات صوتية محلية؛ يجب استدعاؤها من executor عند المسارات الكبيرة."""
        path = Path(folder_path or "./music")
        extensions = {".mp3", ".wav", ".flac", ".m4a", ".ogg"}
        try:
            return {
                index: {
                    "name": file.name,
                    "path": str(file.absolute()),
                    "size": file.stat().st_size,
                }
                for index, file in enumerate(sorted(path.iterdir()), 1)
                if file.suffix.lower() in extensions and file.is_file()
            }
        except OSError:
            logger.exception("تعذر قراءة مجلد الوسائط %s", folder_path)
            return {}
