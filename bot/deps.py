#!/usr/bin/env python3
"""حاوية التبعيات (DI container) + دورة حياتها.

تُنشأ التبعيات مرة واحدة في main() وتُمرر للمعالجات بدل singletons عالمية.
هذا يفصل الإنشاء عن الاستهلاك ويُسهّل الاختبار.
"""

import logging

logger = logging.getLogger(__name__)


class Dependencies:
    """كل التبعيات المشتركة بين المعالجات والخدمات."""

    __slots__ = (
        "adhkar_repo",
        "adhkar_scheduler",
        "db",
        "group_repo",
        "notifier",
        "quran_radio",
        "scheduler",
        "sent_repo",
        "settings",
        "stream_manager",
        "user_repo",
    )

    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


async def build_dependencies(
    settings, app, stream_factory=None, message_transport_factory=None
):
    """يبني كل التبعيات ويُرجعها في حاوية واحدة. app = Pyrogram Client.

    stream_factory قابل للحقن للاختبار أو لمسار Bot API بلا بث صوتي.
    message_transport_factory يسمح بربط notifier بمحول Pyrogram أو aiogram.
    """
    from bot.db.connection import Database

    db = Database(settings.db_path, pool_size=settings.db_pool_size)
    await db.connect()

    from bot.db.repositories.adhkar_settings import AdhkarSettingsRepo
    from bot.db.repositories.group_settings import GroupSettingsRepo
    from bot.db.repositories.sent_notifications import SentNotificationsRepo
    from bot.db.repositories.user_settings import UserSettingsRepo

    user_repo = UserSettingsRepo(db)
    group_repo = GroupSettingsRepo(db)
    sent_repo = SentNotificationsRepo(db)
    adhkar_repo = AdhkarSettingsRepo(db)

    try:
        if stream_factory is None:
            from bot.streaming.stream_manager import StreamManager

            stream_manager = StreamManager(
                app,
                max_reconnect=settings.max_reconnect_attempts,
                base_delay=settings.initial_reconnect_delay,
                default_duration_min=settings.default_stream_duration,
                audio_quality=settings.audio_quality,
                max_concurrent_streams=settings.max_concurrent_streams,
            )
        else:
            stream_manager = stream_factory(app)
    except ImportError:
        from bot.streaming.null_stream_manager import NullStreamManager

        logger.warning("⚠️ py-tgcalls غير مثبت — البث الصوتي معطّل")
        stream_manager = NullStreamManager(app)

    from bot.scheduler.adhkar_scheduler import AdhkarScheduler
    from bot.scheduler.notifier import Notifier
    from bot.scheduler.prayer_scheduler import PrayerScheduler
    from bot.services.quran_radio import QuranRadio

    if message_transport_factory is None:
        from bot.transport import PyrogramMessageTransport

        message_transport_factory = PyrogramMessageTransport

    notifier = Notifier(message_transport_factory(app), stream_manager)
    scheduler = PrayerScheduler(
        user_repo,
        group_repo,
        sent_repo,
        notifier,
        tick_seconds=settings.scheduler_tick_seconds,
    )
    adhkar_scheduler = AdhkarScheduler(
        adhkar_repo,
        app,
        tick_seconds=settings.scheduler_tick_seconds,
        group_repo=group_repo,
    )
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
        except Exception as e:
            logger.warning("⚠️ خطأ أثناء إغلاق %s: %s", label, e)
