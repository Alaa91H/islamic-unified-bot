#!/usr/bin/env python3

import asyncio
import contextlib
import gc
import logging
import os
import sys

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("islamic_bot")

# مراقب الذاكرة: يُضبط افتراضيًا ليتماشى مع حد systemd (MemoryMax=700M).
# عند تجاوز العتبة يتم تعطيل الأذكار لتفريغ الذاكرة قبل أن يقتل systemd العملية.
_MEMORY_CHECK_INTERVAL = 1800
_DEFAULT_HIGH_MEMORY_THRESHOLD = 600 * 1024 * 1024


def _get_env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        return int(raw)
    except ValueError:
        return default


_HIGH_MEMORY_THRESHOLD = _get_env_int(
    "HIGH_MEMORY_THRESHOLD_MB", _DEFAULT_HIGH_MEMORY_THRESHOLD // (1024 * 1024)
) * (1024 * 1024)


def _get_memory_usage() -> int:
    try:
        import psutil

        return psutil.Process(os.getpid()).memory_info().rss
    except ImportError:
        return 0


async def _memory_monitor(deps):
    """يراقب استهلاك الذاكرة كل 30 دقيقة ويعطّل الأذكار إذا تجاوز الحد.

    العتبة الافتراضية 600MB — أقل من حد systemd MemoryMax (700M) — حتى
    يتاح للبوت تنظيف نفسه قبل أن يُقتل من OOM killer.
    عند انخفاض الذاكرة تحت عتبة آمنة، تُستعادة الأذكار إن كانت متوقفة.
    """
    warn_threshold = int(_HIGH_MEMORY_THRESHOLD * 0.85)
    recovery_threshold = int(_HIGH_MEMORY_THRESHOLD * 0.70)
    adhkar_paused = False
    while True:
        try:
            await asyncio.sleep(_MEMORY_CHECK_INTERVAL)
        except asyncio.CancelledError:
            break
        mem = _get_memory_usage()
        if mem == 0:
            continue
        mem_mb = mem / (1024 * 1024)
        logger.info("📊 استخدام الذاكرة: %.1f MB", mem_mb)
        if mem > _HIGH_MEMORY_THRESHOLD:
            logger.warning(
                "⚠️ الذاكرة %.1f MB تجاوزت الحد %d MB — إيقاف أذكار وتنظيف",
                mem_mb,
                _HIGH_MEMORY_THRESHOLD // (1024 * 1024),
            )
            gc.collect()
            if deps.adhkar_scheduler and deps.adhkar_scheduler._task is not None:
                await deps.adhkar_scheduler.stop()
                adhkar_paused = True
        elif mem > warn_threshold:
            logger.warning("🔶 الذاكرة %.1f MB تقترب من الحد — تنظيف استباقي", mem_mb)
            gc.collect()
        elif adhkar_paused and mem < recovery_threshold:
            logger.info(
                "🔄 الذاكرة %.1f MB عادت للحد الآمن (< %d MB) — إعادة تشغيل الأذكار",
                mem_mb,
                recovery_threshold // (1024 * 1024),
            )
            if deps.adhkar_scheduler and deps.adhkar_scheduler._task is None:
                await deps.adhkar_scheduler.start()
            adhkar_paused = False


async def _heartbeat():
    """يكتب ملف heartbeat كل دقيقة ليفحصه Docker HEALTHCHECK.

    إن تجمّد الـ event loop (deadlock) أو انقطع اتصال Telegram، لن يُحدّث
    الملف وسيعتبر Docker الحاوية غير صحية ويعيد تشغيلها.
    """
    import time
    from pathlib import Path

    health_path = Path(".health")
    while True:
        try:
            await asyncio.to_thread(health_path.write_text, str(time.time()))
            await asyncio.sleep(60)
        except asyncio.CancelledError:
            break
        except OSError:
            logger.warning("تعذر تحديث ملف heartbeat", exc_info=True)
            await asyncio.sleep(60)


async def main():
    from bot.config import Settings
    from bot.db.migrate_from_json import migrate_from_json
    from bot.deps import build_dependencies, shutdown_dependencies
    from bot.logging_setup import setup_logging

    settings = Settings.from_env()
    setup_logging(
        log_level=settings.log_level,
        log_dir=settings.logs_dir,
        json_format=settings.log_format == "json",
    )

    logger.info("=" * 70)
    logger.info("🕌 البوت الإسلامي الموحد v2 - يبدأ التشغيل...")
    logger.info("=" * 70)

    app = None
    deps = None
    monitor_task = None
    heartbeat_task = None
    miniapp_api_server = None
    miniapp_api_task = None
    app_started = False
    try:
        from pyrogram import Client

        app = Client(
            settings.session_name,
            api_id=settings.api_id,
            api_hash=settings.api_hash,
            bot_token=settings.bot_token,
        )
        deps = await build_dependencies(settings, app)

        from bot.handlers import HandlerRegistry

        HandlerRegistry().register(app, deps)

        old_json = f"{settings.azan_data_dir}/user_settings.json"
        await migrate_from_json(old_json, deps.user_repo)

        app_started = True
        await app.start()
        logger.info("✅ اتصال Telegram جاهز")

        if hasattr(deps.stream_manager, "start"):
            await deps.stream_manager.start()
        await deps.scheduler.start()

        if settings.lightweight_mode:
            gc.collect()
            logger.info("🧹 تم تنظيف الذاكرة (gc.collect) في الوضع الخفيف")

        await deps.adhkar_scheduler.start()

        if settings.miniapp_api_enabled:
            import uvicorn

            from bot.miniapp_api import create_miniapp_api

            miniapp_api_server = uvicorn.Server(
                uvicorn.Config(
                    create_miniapp_api(settings, deps),
                    host=settings.miniapp_api_host,
                    port=settings.miniapp_api_port,
                    log_level=settings.log_level.lower(),
                    access_log=False,
                    server_header=False,
                    date_header=False,
                    limit_concurrency=settings.miniapp_api_concurrency_limit,
                    timeout_graceful_shutdown=10,
                )
            )
            miniapp_api_task = asyncio.create_task(
                miniapp_api_server.serve(), name="miniapp-api-server"
            )
            await asyncio.sleep(0)
            if miniapp_api_task.done():
                raise RuntimeError("تعذر بدء API Mini App")
            logger.info(
                "✅ API Mini App تعمل محليًا على %s:%s",
                settings.miniapp_api_host,
                settings.miniapp_api_port,
            )

        monitor_task = asyncio.create_task(_memory_monitor(deps))
        heartbeat_task = asyncio.create_task(_heartbeat())

        logger.info("✅ جميع الأنظمة جاهزة!")
        logger.info(f"👤 معرف المالك: {settings.owner_id}")

        await asyncio.Event().wait()

    except Exception:
        logger.exception("❌ خطأ حرج أثناء تشغيل البوت")
        raise
    finally:
        if miniapp_api_server:
            miniapp_api_server.should_exit = True
        if miniapp_api_task:
            with contextlib.suppress(asyncio.CancelledError, TimeoutError):
                await asyncio.wait_for(miniapp_api_task, timeout=10)
        if monitor_task:
            monitor_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await monitor_task
        if heartbeat_task:
            heartbeat_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await heartbeat_task
        logger.info("🛑 إيقاف البوت...")
        if deps:
            await shutdown_dependencies(deps)
        if app_started:
            await app.stop()
        logger.info("✅ تم الإيقاف بنجاح")


if __name__ == "__main__":
    try:
        import uvloop

        uvloop.install()
        logger.info("✅ uvloop مثبت — أداء أعلى")
    except ImportError:
        pass

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("🛑 تم الإيقاف بواسطة المستخدم")
    except Exception:
        logger.exception("❌ خطأ حرج أثناء إيقاف البوت")
        sys.exit(1)
