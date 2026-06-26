#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""بناء عميل Pyrogram — لا أثر جانبي عند الاستيراد.

استيراد bot.app يجب ألا يُنشئ Client أو يتصل بالشبكة. build_app() فقط هي
تُنشئ Client وتُسجّل المعالجات، ويُستدعى من main().
"""

import logging

logger = logging.getLogger(__name__)


def build_app(settings, deps):
    """ينشئ Client (كسولًا) ويسجّل كل المعالجات عبر HandlerRegistry.

    يُرجع مثيل Client جاهزًا للتشغيل. لا يبدأ الاتصال — ذلك مسؤولية main().
    """
    # استيراد Pyrogram داخل الدالة (lazy) لتفصل المنطق عن النقل
    from pyrogram import Client

    from bot.handlers import HandlerRegistry

    app = Client(
        settings.session_name,
        api_id=settings.api_id,
        api_hash=settings.api_hash,
        bot_token=settings.bot_token,
    )
    HandlerRegistry().register(app, deps)
    logger.info("✅ بُني Pyrogram Client وسُجّلت المعالجات")
    return app
