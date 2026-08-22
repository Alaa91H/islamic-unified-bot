import json
import logging
import os
from functools import lru_cache

_LOCALES_DIR = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "data", "locales"
)

logger = logging.getLogger("islamic_bot.i18n")

SUPPORTED_LANGUAGES = {
    "ar": "العربية",
    "en": "English",
    "af": "Afrikaans",
    "sq": "Shqip",
    "am": "አማርኛ",
    "az": "Azərbaycan",
    "bn": "বাংলা",
    "bs": "Bosanski",
    "bg": "Български",
    "my": "မြန်မာဘာသာ",
    "zh": "中文",
    "hr": "Hrvatski",
    "cs": "Čeština",
    "dv": "ދިވެހި",
    "nl": "Nederlands",
    "et": "Eesti",
    "fi": "Suomi",
    "fr": "Français",
    "ka": "ქართული",
    "de": "Deutsch",
    "el": "Ελληνικά",
    "ha": "Hausa",
    "hi": "हिन्दी",
    "hu": "Magyar",
    "ig": "Igbo",
    "id": "Bahasa Indonesia",
    "it": "Italiano",
    "ja": "日本語",
    "jv": "Basa Jawa",
    "kn": "ಕನ್ನಡ",
    "kk": "Қазақ",
    "ko": "한국어",
    "ku": "Kurdî",
    "ky": "Кыргызча",
    "lv": "Latviešu",
    "lt": "Lietuvių",
    "ms": "Bahasa Melayu",
    "ml": "മലയാളം",
    "mr": "मराठी",
    "mn": "Монгол",
    "ne": "नेपाली",
    "no": "Norsk",
    "fa": "فارسی",
    "pl": "Polski",
    "pt": "Português",
    "pa": "ਪੰਜਾਬੀ",
    "ro": "Română",
    "ru": "Русский",
    "sr": "Српски",
    "si": "සිංහල",
    "sk": "Slovenčina",
    "sl": "Slovenščina",
    "so": "Soomaali",
    "es": "Español",
    "sw": "Kiswahili",
    "sv": "Svenska",
    "tg": "Тоҷикӣ",
    "ta": "தமிழ்",
    "tt": "Татар",
    "te": "తెలుగు",
    "th": "ไทย",
    "tr": "Türkçe",
    "tk": "Türkmen",
    "ug": "ئۇيغۇرچە",
    "uk": "Українська",
    "ur": "اردو",
    "uz": "Oʻzbek",
    "vi": "Tiếng Việt",
    "yo": "Yorùbá",
    "zu": "isiZulu",
}


@lru_cache(maxsize=128)
def load_locale(lang: str) -> dict:
    if lang not in SUPPORTED_LANGUAGES:
        lang = "en"
    path = os.path.join(_LOCALES_DIR, f"{lang}.json")
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        if lang != "en":
            return load_locale("en")
        return {}


def t(key: str, lang: str = "en", **kwargs) -> str:
    locale = load_locale(lang)
    parts = key.split(".")
    val = locale
    for part in parts:
        if isinstance(val, dict):
            val = val.get(part)
        else:
            val = None
            break
    if val is None:
        fallback = load_locale("en")
        val = fallback
        for part in parts:
            if isinstance(val, dict):
                val = val.get(part)
            else:
                val = key
                break
        if val is None:
            val = key
    if kwargs:
        try:
            return str(val).format(**kwargs)
        except (KeyError, ValueError):
            return str(val)
    return str(val)


_script_cache: dict[str, str] = {}


def detect_script(lang: str) -> str:
    arabic_scripts = {"ar", "fa", "ur", "ku", "ug", "dv"}
    cyrillic_scripts = {"ru", "uk", "bg", "sr", "kk", "ky", "tg", "tt", "mn", "az"}
    if lang in arabic_scripts:
        return "arabic"
    if lang in cyrillic_scripts:
        return "cyrillic"
    return "latin"


def get_locale_dir() -> str:
    return _LOCALES_DIR
