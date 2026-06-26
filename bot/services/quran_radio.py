import asyncio
import logging
import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from bot.data.sources import QURANIC_RECITERS
from bot.data.surahs import SURAHS

logger = logging.getLogger(__name__)


def estimate_duration(surah_num: int) -> int:
    if surah_num == 1:
        return 1
    if surah_num == 2:
        return 55
    if surah_num <= 10:
        return 14
    if surah_num <= 20:
        return 10
    if surah_num <= 35:
        return 7
    if surah_num <= 55:
        return 5
    if surah_num <= 75:
        return 4
    if surah_num <= 95:
        return 3
    return 2


AUDIO_QUALITY_OPTIONS = ["low", "medium", "high", "studio"]
AUDIO_QUALITY_LABELS = {"low": "منخفضة", "medium": "متوسطة", "high": "عالية", "studio": "استوديو"}

@dataclass
class RadioState:
    chat_id: int
    reciter_key: str = "abdul_basit"
    queue: List[int] = field(default_factory=lambda: list(range(1, 115)))
    current_index: int = 0
    shuffle: bool = False
    playing: bool = False
    paused: bool = False
    audio_quality: str = "high"
    task: Optional[asyncio.Task] = None


class QuranRadio:
    def __init__(self, stream_manager, settings):
        self._stream = stream_manager
        self._settings = settings
        self._states: Dict[int, RadioState] = {}

    @property
    def current_surah(self, state: RadioState) -> int:
        if 0 <= state.current_index < len(state.queue):
            return state.queue[state.current_index]
        return 1

    def _build_url(self, reciter_key: str, surah_num: int) -> str:
        base = QURANIC_RECITERS.get(reciter_key, {}).get("stream_url", "")
        return f"{base}{surah_num:03d}.mp3"

    async def start(
        self, chat_id: int, reciter_key: str = "abdul_basit", surah_start: Optional[int] = None
    ) -> bool:
        old = self._states.get(chat_id)
        if old and old.task:
            old.task.cancel()

        queue = list(range(1, 115))
        start_idx = 0
        if surah_start is not None and 1 <= surah_start <= 114:
            start_idx = queue.index(surah_start)

        state = RadioState(
            chat_id=chat_id,
            reciter_key=reciter_key,
            queue=queue,
            current_index=start_idx,
            shuffle=False,
        )
        self._states[chat_id] = state
        return await self._play_current(chat_id)

    async def stop(self, chat_id: int) -> bool:
        state = self._states.pop(chat_id, None)
        if state and state.task:
            state.task.cancel()
        return await self._stream.stop(chat_id)

    async def next(self, chat_id: int) -> bool:
        state = self._states.get(chat_id)
        if not state:
            return False
        if state.task:
            state.task.cancel()
            state.task = None
        state.current_index = (state.current_index + 1) % len(state.queue)
        return await self._play_current(chat_id)

    async def prev(self, chat_id: int) -> bool:
        state = self._states.get(chat_id)
        if not state:
            return False
        if state.task:
            state.task.cancel()
            state.task = None
        state.current_index = (state.current_index - 1) % len(state.queue)
        return await self._play_current(chat_id)

    async def toggle_shuffle(self, chat_id: int) -> bool:
        state = self._states.get(chat_id)
        if not state:
            return False
        state.shuffle = not state.shuffle
        if state.shuffle:
            current = state.queue[state.current_index]
            remaining = [s for s in state.queue if s != current]
            random.shuffle(remaining)
            state.queue = [current] + remaining
            state.current_index = 0
        else:
            current = state.queue[state.current_index]
            state.queue = list(range(1, 115))
            state.current_index = state.queue.index(current)
        return True

    async def set_reciter(self, chat_id: int, reciter_key: str) -> bool:
        state = self._states.get(chat_id)
        if not state or reciter_key not in QURANIC_RECITERS:
            return False
        state.reciter_key = reciter_key
        if state.playing:
            return await self._play_current(chat_id)
        return True

    def get_state(self, chat_id: int) -> Optional[RadioState]:
        return self._states.get(chat_id)

    async def _play_current(self, chat_id: int) -> bool:
        state = self._states.get(chat_id)
        if not state:
            return False

        surah_num = state.queue[state.current_index]
        url = self._build_url(state.reciter_key, surah_num)
        name = SURAHS.get(surah_num, f"{surah_num}")
        dur = estimate_duration(surah_num)

        ok = await self._stream.play(chat_id, url, f"{surah_num} - {name}", loop=False, duration_min=dur + 5)
        if ok:
            state.playing = True
            state.paused = False
            self._schedule_next(chat_id, dur)
            logger.info("📻 راديو: %s ← سورة %s (%s)", chat_id, surah_num, name)
        else:
            state.playing = False
        return ok

    def _schedule_next(self, chat_id: int, delay_min: int) -> None:
        state = self._states.get(chat_id)
        if not state:
            return
        if state.task:
            state.task.cancel()

        async def _advance():
            try:
                await asyncio.sleep(delay_min * 60)
                if chat_id in self._states:
                    logger.info("📻 راديو: تلقائي → التالي في %s", chat_id)
                    await self.next(chat_id)
            except asyncio.CancelledError:
                pass

        state.task = asyncio.create_task(_advance())

    async def set_quality(self, chat_id: int, quality: str) -> bool:
        from bot.streaming.stream_manager import StreamManager
        state = self._states.get(chat_id)
        if not state or quality not in AUDIO_QUALITY_OPTIONS:
            return False
        state.audio_quality = quality
        if state.playing and not state.paused:
            return await self._play_current(chat_id)
        return True

    async def pause(self, chat_id: int) -> bool:
        state = self._states.get(chat_id)
        if not state:
            return False
        state.paused = True
        if state.task:
            state.task.cancel()
            state.task = None
        return await self._stream.stop(chat_id)

    async def resume(self, chat_id: int) -> bool:
        state = self._states.get(chat_id)
        if not state:
            return False
        if not state.paused:
            return True
        state.paused = False
        return await self._play_current(chat_id)
