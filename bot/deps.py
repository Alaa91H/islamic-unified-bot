#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""حاوية التبعيات (DI container) + دورة حياتها.

تُنشأ التبعيات مرة واحدة في main() وتُمرر للمعالجات بدل singletons عالمية.
هذا يفصل الإنشاء عن الاستهلاك ويُسهّل الاختبار.
"""

import logging
from dataclasses import dataclass

from bot.config import Settings
from bot.db.connection import Database
from bot.db.repositories.adhkar_settings import AdhkarSettingsRepo
from bot.db.repositories.group_settings import GroupSettingsRepo
from bot.db.repositories.sent_notifications import SentNotificationsRepo
from bot.db.repositories.user_settings import UserSettingsRepo
from bot.scheduler.adhkar_scheduler import AdhkarScheduler
from bot.scheduler.notifier import Notifier
from bot.scheduler.prayer_scheduler import PrayerScheduler
from bot.services.quran_radio import QuranRadio
from bot.streaming.null_stream_manager import NullStreamManager
from bot.streaming.stream_manager import StreamManager

logger = logging.getLogger(__name__)


@dataclass
class Dependencies:
    """كل التبعيات المشتركة بين المعالجات والخدمات."""

    settings: Settings
    db: Database
    user_repo: UserSettingsRepo
    group_repo: GroupSettingsRepo
    sent_repo: SentNotificationsRepo
    adhkar_repo: AdhkarSettingsRepo
    stream_manager: StreamManager
    notifier: Notifier
    scheduler: PrayerScheduler
    adhkar_scheduler: AdhkarScheduler
    quran_radio: QuranRadio


async def build_dependencies(
    settings: Settings, app, stream_factory=None
) -> Dependencies:
    """يبني كل التبعيات ويُرجعها في حاوية واحدة. app = Pyrogram Client.

    stream_factory قابل للحقن للاختبار (يتجاوز استيراد pytgcalls الافتراضي).
    """
    db = Database(settings.db_path)
    await db.connect()

    user_repo = UserSettingsRepo(db)
    group_repo = GroupSettingsRepo(db)
    sent_repo = SentNotificationsRepo(db)
    adhkar_repo = AdhkarSettingsRepo(db)

    try:
        if stream_factory is None:
            stream_manager = StreamManager(
                app,
                max_reconnect=settings.max_reconnect_attempts,
                base_delay=settings.initial_reconnect_delay,
                default_duration_min=settings.default_stream_duration,
                audio_quality=settings.audio_quality,
            )
        else:
            stream_manager = stream_factory(app)
    except ImportError:
        logger.warning("⚠️ py-tgcalls غير مثبت — البث الصوتي معطّل")
        stream_manager = NullStreamManager(app)

    notifier = Notifier(app, stream_manager)
    scheduler = PrayerScheduler(
        user_repo,
        group_repo,
        sent_repo,
        notifier,
        tick_seconds=settings.scheduler_tick_seconds,
    )
    adhkar_scheduler = AdhkarScheduler(adhkar_repo, app)
    quran_radio = QuranRadio(stream_manager, settings)

    return Dependencies(
        settings=settings,
        db=db,
        user_repo=user_repo,
        group_repo=group_repo,
        sent_repo=sent_repo,
        adhkar_repo=adhkar_repo,
        stream_manager=stream_manager,
        notifier=notifier,
        scheduler=scheduler,
        adhkar_scheduler=adhkar_scheduler,
        quran_radio=quran_radio,
    )


async def shutdown_dependencies(deps: Dependencies) -> None:
    """إغلاق مرتّب: scheduler → stream → db. آمن ضد الأخطاء المتداخلة."""
    for label, coro_factory in (
        ("scheduler", lambda: deps.scheduler.stop()),
        ("adhkar_scheduler", lambda: deps.adhkar_scheduler.stop()),
        ("stream", lambda: deps.stream_manager.stop_all()),
        ("db", lambda: deps.db.close()),
    ):
        try:
            await coro_factory()
        except Exception as e:  # noqa: BLE001 — الإغلاق يجب أن يستمر
            logger.warning("⚠️ خطأ أثناء إغلاق %s: %s", label, e)
