#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
import logging
import sys

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("islamic_bot")


async def main():
    from bot.config import Settings
    from bot.logging_setup import setup_logging
    from bot.deps import build_dependencies, shutdown_dependencies
    from bot.db.migrate_from_json import migrate_from_json

    # 1. تهيئة التسجيل
    settings = Settings.from_env()
    setup_logging(
        log_level=settings.log_level,
        log_dir=settings.logs_dir,
        json_format=settings.log_format == "json",
    )

    logger.info("=" * 70)
    logger.info("🕌 البوت الإسلامي الموحد v2 - يبدأ التشغيل...")
    logger.info("=" * 70)

    # 2. بناء التطبيق والتبعيات
    app = None
    deps = None
    try:
        from pyrogram import Client

        app = Client(
            settings.session_name,
            api_id=settings.api_id,
            api_hash=settings.api_hash,
            bot_token=settings.bot_token,
        )
        deps = await build_dependencies(settings, app)

        # تسجيل المعالجات
        from bot.handlers import HandlerRegistry

        HandlerRegistry().register(app, deps)

        # 3. هجرة البيانات القديمة (إن وُجدت)
        old_json = f"{settings.azan_data_dir}/user_settings.json"
        await migrate_from_json(old_json, deps.user_repo)

        # 4. بدء الخدمات
        if hasattr(deps.stream_manager, "start"):
            await deps.stream_manager.start()
        await deps.scheduler.start()
        await deps.adhkar_scheduler.start()

        logger.info("✅ جميع الأنظمة جاهزة!")
        logger.info(f"👤 معرف المالك: {settings.owner_id}")

        # 5. انتظار إلى الأبد
        await asyncio.Event().wait()

    except Exception as e:
        logger.exception("❌ خطأ حرج: %s", e)
        sys.exit(1)
    finally:
        logger.info("🛑 إيقاف البوت...")
        if deps:
            await shutdown_dependencies(deps)
        if app:
            await app.stop()
        logger.info("✅ تم الإيقاف بنجاح")


if __name__ == "__main__":
    try:
        from pyrogram import Client

        Client  # noqa — التحقق من توفر المكتبة
    except ImportError:
        logger.error(
            "❌ المكتبة Pyrogram غير مثبتة. قم بتشغيل: pip install -r requirements.txt"
        )
        sys.exit(1)

    try:
        app_instance = Client("islamic_unified_bot")  # noqa — تحقق سريع
        del app_instance
    except Exception:
        pass  # لن يعمل بدون token وهذا طبيعي

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("🛑 تم الإيقاف بواسطة المستخدم")
    except Exception as e:
        logger.error("❌ خطأ حرج: %s", e, exc_info=True)
        sys.exit(1)
