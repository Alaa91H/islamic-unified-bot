#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""هجرة واحدة من user_settings.json القديم إلى SQLite.

تُشغّل تلقائيًا عند أول إقلاع بعد التحديث (من main.py). تقرأ ملف JSON إن وُجد،
تستورد كل مستخدم صالح إلى SQLite، ثم تُؤرشف الملف الأصلي إلى .bak.
لا تُفقد أي بيانات مستخدمين موجودين.
"""

import json
import logging
from pathlib import Path

from bot.db.repositories.user_settings import UserSettings, UserSettingsRepo

logger = logging.getLogger(__name__)


async def migrate_from_json(json_path: Path | str, repo: UserSettingsRepo) -> int:
    """يستورد المستخدمين من JSON. يُرجع عدد المستوردين. يُنشئ نسخة .bak.

    متسامح مع الأخطاء: السجلات غير الصالحة تُتخطّى دون إيقاف الهجرة.
    """
    path = Path(json_path)
    if not path.exists():
        logger.info("ℹ️ لا يوجد ملف JSON قديم للهجرة: %s", path)
        return 0

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, OSError) as e:
        logger.warning("⚠️ تعذّرت قراءة JSON القديم (%s): %s", path, e)
        return 0

    if not isinstance(data, dict):
        logger.warning("⚠️ بنية JSON غير متوقعة في %s", path)
        return 0

    imported = 0
    for user_id_str, settings_dict in data.items():
        try:
            if not isinstance(settings_dict, dict):
                raise ValueError("قيمة غير قاموس")
            uid = int(user_id_str)
            prayers = settings_dict.get("enabled_prayers")
            if prayers is None:
                prayers = ["fajr", "dhuhr", "asr", "maghrib", "isha"]
            s = UserSettings(
                user_id=uid,
                city=settings_dict.get("city", "مكة المكرمة"),
                method=settings_dict.get("method", "isna"),
                asr_method=settings_dict.get("asr_method", "standard"),
                timezone=settings_dict.get("timezone", 0),
                notifications_on=settings_dict.get("notification_enabled", True),
                prelude_on=settings_dict.get("prelude_enabled", False),
                prelude_minutes=settings_dict.get("prelude_time", 5),
                enabled_prayers=prayers,
            )
            await repo.upsert(s)
            imported += 1
        except Exception as e:
            logger.warning("⚠️ تخطّي مستخدم %s: %s", user_id_str, e)

    # أرشفة الملف الأصلي
    backup = path.with_suffix(path.suffix + ".bak")
    try:
        path.rename(backup)
        logger.info("📦 تمت أرشفة JSON القديم إلى %s", backup)
    except OSError as e:
        logger.warning("⚠️ تعذّرت أرشفة JSON: %s", e)

    logger.info("✅ تمت هجرة %d مستخدم من JSON", imported)
    return imported
