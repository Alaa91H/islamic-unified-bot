#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""غلاف آمن حول PyTgCalls للقرآن والأذان.

يوفّر:
- إعادة اتصال محدودة بـ backoff أُسيّ + jitter.
- مهلة قصوى للبث (auto-stop) عبر asyncio.Task مؤجّل.
- منع الحلقة اللانهائية: علم loop يتحكم في إعادة البث عند on_stream_end.

استيراد pytgcalls كسول (lazy) داخل __init__ ليفصل المنطق عن native binding،
مما يسمح باختبار StreamManager على بيئات لا تتوفر فيها مكتبة ntgcalls المُجمّعة.
"""

import asyncio
import logging
import random
from datetime import datetime
from typing import Dict, Optional

logger = logging.getLogger(__name__)


def _import_pytgcalls():
    """يستورد PyTgCalls و MediaStream/AudioQuality كسليًا. يُسهّل الاستهزاء."""
    from pytgcalls import PyTgCalls
    from pytgcalls.exceptions import NotInCallError
    from pytgcalls.types import AudioQuality, MediaStream

    return PyTgCalls, NotInCallError, AudioQuality, MediaStream


class StreamManager:
    """بث صوتي مع reconnect محدود ومهلة قصوى."""

    def __init__(
        self,
        app,
        max_reconnect: int = 10,
        base_delay: int = 5,
        default_duration_min: int = 120,
        audio_quality: str = "studio",
        pytgcalls_factory=None,
        import_func=None,
    ):
        self._app = app
        self.max_reconnect = max_reconnect
        self.base_delay = base_delay
        self.default_duration_min = default_duration_min
        self._audio_quality_str = audio_quality
        self._streams: Dict[int, dict] = {}
        self._timers: Dict[int, asyncio.Task] = {}
        self._started = False
        # دالة الاستيراد قابلة للحقن للاختبار (تفصل المنطق عن native binding)
        self._import_func = import_func or _import_pytgcalls
        # factory قابل للحقن للاختبار؛ الافتراضي يستورد pytgcalls
        if pytgcalls_factory is None:
            PyTgCalls, _, _, _ = self._import_func()
            pytgcalls_factory = PyTgCalls
        self.pytgcalls = pytgcalls_factory(app)

    async def start(self) -> None:
        """يبدأ خدمة المكالمات ويسجّل معالج نهاية البث."""
        if self._started:
            return
        await self.pytgcalls.start()

        @self.pytgcalls.on_update()
        async def _on_update(_client, update):
            chat_id = getattr(update, "chat_id", None)
            if chat_id is None:
                return
            info = self._streams.get(chat_id)
            if info and info.get("loop") and info.get("status") == "active":
                logger.info("🔄 إعادة بث (loop) في %s", chat_id)
                await self.play(
                    chat_id,
                    info["url"],
                    info["title"],
                    loop=True,
                    duration_min=info.get("duration_min"),
                )

        self._started = True
        logger.info("✅ خدمة المكالمات جاهزة")

    async def stop_all(self) -> None:
        """يوقف كل المؤقتات وخدمة pytgcalls."""
        for timer in list(self._timers.values()):
            timer.cancel()
        self._timers.clear()
        self._streams.clear()

    async def play(
        self,
        chat_id: int,
        url: str,
        title: str = "بث",
        loop: bool = False,
        duration_min: Optional[int] = None,
        attempts: int = 0,
    ) -> bool:
        """يبدأ بثًا. يُرجع True عند النجاح، False عند استنفاد المحاولات."""
        _, NotInCallError, AudioQuality, MediaStream = self._import_func()
        quality_map = {
            "low": AudioQuality.LOW,
            "medium": AudioQuality.MEDIUM,
            "high": AudioQuality.HIGH,
            "studio": AudioQuality.STUDIO,
        }
        audio_params = quality_map.get(self._audio_quality_str, AudioQuality.STUDIO)
        media = MediaStream(
            url,
            audio_parameters=audio_params,
            ffmpeg_parameters="-af volume=1.5",
        )
        try:
            await self.pytgcalls.play(chat_id, media)
        except NotInCallError:
            logger.info("ℹ️ البوت يبث بالفعل في %s", chat_id)
        except Exception as e:
            if attempts < self.max_reconnect:
                delay = self.base_delay * (2**attempts) + random.uniform(0, 1)
                logger.error(
                    "❌ فشل البث (%d/%d): %s — إعادة بعد %.1fث",
                    attempts + 1,
                    self.max_reconnect,
                    e,
                    delay,
                )
                await asyncio.sleep(delay)
                return await self.play(
                    chat_id, url, title, loop, duration_min, attempts + 1
                )
            logger.error("❌ فشل البث نهائيًا بعد %d محاولة", self.max_reconnect)
            return False

        dur = duration_min if duration_min is not None else self.default_duration_min
        self._streams[chat_id] = {
            "url": url,
            "title": title,
            "started_at": datetime.now(),
            "status": "active",
            "loop": loop,
            "duration_min": dur,
        }
        self._schedule_stop(chat_id, dur)
        logger.info(
            "✅ بث نشط في %s: %s (loop=%s, dur=%smin)",
            chat_id,
            title,
            loop,
            dur,
        )
        return True

    def _schedule_stop(self, chat_id: int, duration_min: int) -> None:
        old = self._timers.get(chat_id)
        if old:
            old.cancel()

        async def _auto_stop():
            try:
                await asyncio.sleep(duration_min * 60)
                logger.info("⏹️ انتهت مدة البث في %s", chat_id)
                await self.stop(chat_id)
            except asyncio.CancelledError:
                pass

        self._timers[chat_id] = asyncio.create_task(_auto_stop())

    async def stop(self, chat_id: int) -> bool:
        """يوقف البث في chat_id. يُرجع True إذا كان هناك بث نشط."""
        timer = self._timers.pop(chat_id, None)
        if timer:
            timer.cancel()
        try:
            await self.pytgcalls.leave_call(chat_id)
        except Exception as e:
            logger.warning("⚠️ خطأ leave_call في %s: %s", chat_id, e)
        existed = self._streams.pop(chat_id, None) is not None
        if existed:
            logger.info("✅ أُوقف البث في %s", chat_id)
        return existed

    def active_streams(self) -> Dict[int, dict]:
        """لقطة من البثات النشطة."""
        return dict(self._streams)

    def get_local_files(self, folder_path: str = None) -> Dict:
        """مسح ملفات صوتية محلية. دالة متزامنة (تُستدعى عبر executor)."""
        from pathlib import Path

        if folder_path is None:
            folder_path = "./music"
        files = {}
        try:
            path = Path(folder_path)
            extensions = {".mp3", ".wav", ".flac", ".m4a", ".ogg"}
            for i, file in enumerate(sorted(path.iterdir()), 1):
                if file.suffix.lower() in extensions and file.is_file():
                    files[i] = {
                        "name": file.name,
                        "path": str(file.absolute()),
                        "size": file.stat().st_size,
                    }
        except Exception as e:
            logger.error("❌ خطأ في قراءة المجلد %s: %s", folder_path, e)
        return files
