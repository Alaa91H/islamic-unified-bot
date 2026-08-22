"""مساعدات رصد منظمة تمنع تضمين البيانات الحساسة في السجلات."""

from __future__ import annotations

import logging
from typing import Any


def log_event(
    logger: logging.Logger,
    event: str,
    *,
    level: int = logging.INFO,
    **context: Any,
) -> None:
    """سجّل حدثًا تشغيليًا منظمًا؛ لا تمرّر أسرارًا أو معرفات مستخدمين خامًا."""
    logger.log(level, event, extra={"event": event, "context": context})
