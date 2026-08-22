"""رسائل قصيرة مشتركة للوظائف الحديثة التي تدعم العربية والإنجليزية."""

from __future__ import annotations

MESSAGES = {
    "ar": {
        "miniapp_saved": "تم حفظ إعدادات محراب اليوم بنجاح.",
        "miniapp_setup_first": "أكمل إعداد المدينة أولًا عبر /azan_setup ثم أعد الحفظ.",
        "miniapp_invalid": "تعذر حفظ الإعدادات. أعد فتح التطبيق من البوت وحاول مرة أخرى.",
    },
    "en": {
        "miniapp_saved": "Your Mihrab Today settings have been saved.",
        "miniapp_setup_first": "Set up your city with /azan_setup first, then save again.",
        "miniapp_invalid": "Settings could not be saved. Reopen the app from the bot and try again.",
    },
}


def message_for(language: str, key: str) -> str:
    """إرجاع رسالة مترجمة مع العربية كخيار رجوع آمن."""
    return MESSAGES.get(language, MESSAGES["ar"]).get(key, MESSAGES["ar"][key])
