#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""إعداد السجلات الاحترافي مع تدوير الملفات.

يدعم:
- ملف دوّار (RotatingFileHandler) بحد أقصى 10MB × 5 نسخ.
- إخراج للطرفية (console).
- تنسيق JSON اختياري لتجميع السجلات.
- غير مُكرّر: الاستدعاء المتكرر لا يضيف handlers.
"""

import json
import logging
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from pathlib import Path

_TEXT_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"


class _JsonFormatter(logging.Formatter):
    """منسّق JSON خفيف — يُخرج سطر JSON واحد لكل سجل."""

    def format(self, record: logging.LogRecord) -> str:
        return json.dumps(
            {
                "ts": datetime.fromtimestamp(
                    record.created, tz=timezone.utc
                ).isoformat(),
                "level": record.levelname,
                "logger": record.name,
                "msg": record.getMessage(),
            },
            ensure_ascii=False,
        )


def setup_logging(
    log_level: str = "INFO",
    log_dir: str = "./logs",
    json_format: bool = False,
) -> logging.Logger:
    """يهيّئ التسجيل. يجب استدعاؤها مرة واحدة عند الإقلاع.

    المعاملات:
        log_level: مستوى التسجيل (DEBUG/INFO/WARNING/ERROR).
        log_dir: مجلد ملفات السجل (يُنشأ إن لم يوجد).
        json_format: إن كان True، تُنسق السجلات كـ JSON.

    يُرجع: logger الجذر للمشروع.
    """
    level = getattr(logging, log_level.upper(), logging.INFO)

    root = logging.getLogger()
    root.setLevel(level)
    # إزالة handlers السابقة لضمان عدم التكرار (يهم عند الاستدعاء المتكرر في الاختبارات)
    for handler in list(root.handlers):
        root.removeHandler(handler)

    Path(log_dir).mkdir(parents=True, exist_ok=True)
    log_file = Path(log_dir) / f"islamic_unified_{datetime.now():%Y%m%d}.log"

    formatter = _JsonFormatter() if json_format else logging.Formatter(_TEXT_FORMAT)

    file_handler = RotatingFileHandler(
        log_file, maxBytes=10 * 1024 * 1024, backupCount=5, encoding="utf-8"
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(level)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(level)

    root.addHandler(file_handler)
    root.addHandler(console_handler)

    # اضبط المستوى على الـ logger المُعاد صراحةً (لأن propagation لا يغيّر .level)
    named = logging.getLogger("islamic_bot")
    named.setLevel(level)
    return named
