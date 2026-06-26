#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""تسجيل كل المعالجات — إضافة ميزة = ملف + سطر هنا (Plugin Registry)."""

import logging

logger = logging.getLogger(__name__)


class HandlerRegistry:
    """يسجّل كل وحدات المعالجات على Pyrogram Client."""

    def register(self, app, deps) -> None:
        from bot.handlers import (
            adhkar,
            azan,
            group_adhkar,
            group_quran,
            hadith,
            islamic_names,
            islamic_tools,
            main_menu,
            owner,
            quran,
            quran_radio_handler,
            quran_text,
        )

        # الترتيب يهم: main_menu أولًا (تسجّل /start الذي قد يُعاد توجيهه)
        main_menu.register(app, deps)
        adhkar.register(app, deps)
        quran.register(app, deps)
        quran_text.register(app, deps)
        hadith.register(app, deps)
        islamic_names.register(app, deps)
        azan.register(app, deps)
        group_quran.register(app, deps)
        group_adhkar.register(app, deps)
        quran_radio_handler.register(app, deps)
        islamic_tools.register(app, deps)
        owner.register(app, deps)
        logger.info("✅ سُجّلت كل المعالجات")
