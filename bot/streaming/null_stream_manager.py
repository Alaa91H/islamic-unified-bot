"""مدير بث فارغ (no-op) للاستخدام بدون PyTgCalls.

يوفّر نفس واجهة StreamManager لكن بدون أي وظائف صوتية.
يُستخدم عندما لا تكون مكتبة py-tgcalls مثبتة.
"""

import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class NullStreamManager:
    """مدير بث فارغ — كل العمليات ترجع فورًا بدون خطأ."""

    def __init__(self, app=None, **kwargs):
        self._app = app

    async def start(self) -> None:
        logger.info("ℹ️ StreamManager معطّل (py-tgcalls غير مثبت)")

    async def stop_all(self) -> None:
        pass

    async def play(
        self,
        chat_id: int,
        url: str,
        title: str = "بث",
        loop: bool = False,
        duration_min: Optional[int] = None,
        attempts: int = 0,
    ) -> bool:
        logger.info("ℹ️ البث الصوتي غير متاح (py-tgcalls غير مثبت)")
        return False

    async def stop(self, chat_id: int) -> bool:
        return False

    def active_streams(self) -> Dict[int, dict]:
        return {}

    def get_local_files(self, folder_path: str = None) -> Dict:
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
