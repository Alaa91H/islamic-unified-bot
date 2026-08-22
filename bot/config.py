#!/usr/bin/env python3
"""إعدادات البوت المركزية — تُقرأ من متغيرات البيئة مرة واحدة عند الإقلاع.

كل المكوّنات تتلقى نسخة من Settings بدل قراءة os.getenv مباشرة، مما يجعل
الإعدادات قابلة للاختبار (تُمرّر كـ dependency) وقابلة للتحقق المركزي.
"""

import os
from dataclasses import dataclass
from urllib.parse import urlparse

# قيم "قالب" تعتبر غير مضبوطة وترفض عند التحقق
_PLACEHOLDER_VALUES = {
    "",
    "YOUR_BOT_TOKEN_HERE",
    "YOUR_API_ID_HERE",
    "YOUR_API_HASH_HERE",
    "YOUR_OWNER_ID_HERE",
}


def _get_required(name: str) -> str:
    """قيمة إلزامية: تُرفض إذا كانت فارغة أو ما زالت قالبًا."""
    value = os.getenv(name, "").strip()
    if value in _PLACEHOLDER_VALUES:
        raise ValueError(
            f"❌ {name} غير مُعرّف أو ما زال قالبًا. اضبط قيمة صحيحة في ملف .env"
        )
    return value


def _get_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        return int(raw)
    except ValueError as exc:
        raise ValueError(
            f"❌ {name} يجب أن يكون رقمًا صحيحًا، حصلنا على: {raw!r}"
        ) from exc


def _get_port(name: str, default: int) -> int:
    value = _get_int(name, default)
    if not 1 <= value <= 65535:
        raise ValueError(f"❌ {name} يجب أن يكون بين 1 و65535")
    return value


def _get_positive_int(name: str, default: int) -> int:
    value = _get_int(name, default)
    if value <= 0:
        raise ValueError(f"❌ {name} يجب أن يكون رقمًا صحيحًا موجبًا")
    return value


def _get_choice(name: str, default: str, choices: set[str]) -> str:
    value = _get_str(name, default).lower()
    if value not in choices:
        allowed = ", ".join(sorted(choices))
        raise ValueError(f"❌ {name} يجب أن يكون واحدًا من: {allowed}")
    return value


def _validate_miniapp_api_settings(
    *, enabled: bool, host: str, allowed_origin: str
) -> None:
    """تمنع تفعيل API عامة بلا HTTPS أو بربط شبكة غير مقصود."""
    if not enabled:
        return
    if host not in {"127.0.0.1", "::1", "localhost"}:
        raise ValueError(
            "❌ MINIAPP_API_HOST يجب أن يبقى localhost أو عنوان loopback خلف reverse proxy"
        )
    parsed = urlparse(allowed_origin)
    if (
        parsed.scheme != "https"
        or not parsed.netloc
        or parsed.path
        or parsed.params
        or parsed.query
        or parsed.fragment
        or parsed.username
        or parsed.password
    ):
        raise ValueError(
            "❌ MINIAPP_ALLOWED_ORIGIN يجب أن يكون HTTPS origin دقيقًا بلا مسار، مثل https://miniapp.example.com"
        )


def _get_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    return raw.strip().lower() in ("1", "true", "yes", "on")


def _get_str(name: str, default: str) -> str:
    raw = os.getenv(name)
    return default if raw is None or raw.strip() == "" else raw.strip()


def _fail(name: str) -> int:
    raise ValueError(f"❌ {name} يجب أن يكون رقمًا صحيحًا غير صفري")


@dataclass(frozen=True)
class Settings:
    """إعدادات البوت — ثابتة بعد الإنشاء (frozen)."""

    # --- بيانات Telegram (إلزامية) ---
    bot_token: str
    api_id: int
    api_hash: str
    owner_id: int

    # --- المسارات ---
    music_dir: str = "./music"
    azan_data_dir: str = "./azan_data"
    data_dir: str = "./data"
    logs_dir: str = "./logs"
    session_name: str = "islamic_unified_bot"
    telegram_runtime: str = "pyrogram"

    # --- مصادر ---
    quran_stream_url: str = "https://server8.mp3quran.net/afs/"

    # --- البث ---
    max_reconnect_attempts: int = 10
    initial_reconnect_delay: int = 5
    audio_quality: str = "studio"

    # --- الصلاة ---
    default_calculation_method: str = "mwl"
    default_asr_method: str = "standard"
    default_city: str = "مكة المكرمة"
    default_timezone: int = 3

    # --- التنبيهات ---
    notifications_enabled: bool = True
    prelude_enabled: bool = False
    prelude_time: int = 5

    # --- البث التلقائي ---
    stream_enabled: bool = False
    default_azan_source: str = "traditional"
    stream_stop_before: int = 0
    default_stream_duration: int = 120

    # --- قاعدة البيانات ---
    db_type: str = "sqlite"
    db_path: str = "./data/bot.db"

    # --- الأمان والسجلات ---
    safe_mode: bool = True
    log_sensitive_data: bool = False
    request_timeout: int = 10
    max_retries: int = 3
    debug_mode: bool = False
    log_level: str = "INFO"
    log_format: str = "text"

    # --- الجدولة ---
    scheduler_tick_seconds: int = 60

    # --- Weak server optimizations ---
    db_pool_size: int = 3
    api_timeout: int = 5
    cache_ttl: int = 3600
    max_concurrent_streams: int = 2
    lightweight_mode: bool = True

    # --- Telegram Mini App API ---
    miniapp_api_enabled: bool = False
    miniapp_api_host: str = "127.0.0.1"
    miniapp_api_port: int = 8080
    miniapp_init_data_max_age: int = 3600
    miniapp_allowed_origin: str = ""
    miniapp_api_concurrency_limit: int = 50

    @classmethod
    def from_env(cls) -> "Settings":
        """يبني الإعدادات من متغيرات البيئة مع تحقق صارم وأخطاء واضحة."""
        api_id_raw = os.getenv("API_ID")
        owner_raw = os.getenv("OWNER_ID")
        # نتحقق من الـ placeholders أولاً لرسائل خطأ أوضح
        _get_required("BOT_TOKEN")
        _get_required("API_HASH")
        if api_id_raw is None or api_id_raw.strip() == "":
            raise ValueError("❌ API_ID غير مُعرّف. اضبط قيمة رقمية في .env")
        if owner_raw is None or owner_raw.strip() == "":
            raise ValueError("❌ OWNER_ID غير مُعرّف. اضبط قيمة رقمية في .env")

        api_id = _get_int("API_ID", 0)
        owner_id = _get_int("OWNER_ID", 0)
        if api_id == 0:
            _fail("API_ID")
        if owner_id == 0:
            _fail("OWNER_ID")

        miniapp_api_enabled = _get_bool("MINIAPP_API_ENABLED", False)
        miniapp_api_host = _get_str("MINIAPP_API_HOST", "127.0.0.1")
        miniapp_allowed_origin = _get_str("MINIAPP_ALLOWED_ORIGIN", "")
        _validate_miniapp_api_settings(
            enabled=miniapp_api_enabled,
            host=miniapp_api_host,
            allowed_origin=miniapp_allowed_origin,
        )

        stream_enabled = _get_bool("STREAM_ENABLED", False)
        telegram_runtime = _get_choice(
            "TELEGRAM_RUNTIME", "pyrogram", {"pyrogram", "aiogram"}
        )
        if telegram_runtime == "aiogram" and stream_enabled:
            raise ValueError(
                "❌ STREAM_ENABLED غير مدعوم مع TELEGRAM_RUNTIME=aiogram أثناء النقل المرحلي"
            )

        return cls(
            bot_token=_get_required("BOT_TOKEN"),
            api_id=api_id,
            api_hash=_get_required("API_HASH"),
            owner_id=owner_id,
            music_dir=_get_str("MUSIC_DIR", "./music"),
            azan_data_dir=_get_str("AZAN_DATA_DIR", "./azan_data"),
            data_dir=_get_str("DATA_DIR", "./data"),
            logs_dir=_get_str("LOGS_DIR", "./logs"),
            session_name=_get_str("SESSION_NAME", "islamic_unified_bot"),
            telegram_runtime=telegram_runtime,
            quran_stream_url=_get_str(
                "QURAN_STREAM_URL", "https://server8.mp3quran.net/afs/"
            ),
            max_reconnect_attempts=_get_int("MAX_RECONNECT_ATTEMPTS", 10),
            initial_reconnect_delay=_get_int("INITIAL_RECONNECT_DELAY", 5),
            audio_quality=_get_str("AUDIO_QUALITY", "studio"),
            default_calculation_method=_get_str("DEFAULT_CALCULATION_METHOD", "mwl"),
            default_asr_method=_get_str("DEFAULT_ASR_METHOD", "standard"),
            default_city=_get_str("DEFAULT_CITY", "مكة المكرمة"),
            default_timezone=_get_int("DEFAULT_TIMEZONE", 3),
            notifications_enabled=_get_bool("NOTIFICATIONS_ENABLED", True),
            prelude_enabled=_get_bool("PRELUDE_ENABLED", False),
            prelude_time=_get_int("PRELUDE_TIME", 5),
            stream_enabled=stream_enabled,
            default_azan_source=_get_str("DEFAULT_AZAN_SOURCE", "traditional"),
            stream_stop_before=_get_int("STREAM_STOP_BEFORE", 0),
            default_stream_duration=_get_int("DEFAULT_STREAM_DURATION", 120),
            db_type=_get_str("DB_TYPE", "sqlite"),
            db_path=_get_str("DB_PATH", "./data/bot.db"),
            safe_mode=_get_bool("SAFE_MODE", True),
            log_sensitive_data=_get_bool("LOG_SENSITIVE_DATA", False),
            request_timeout=_get_int("REQUEST_TIMEOUT", 10),
            max_retries=_get_int("MAX_RETRIES", 3),
            debug_mode=_get_bool("DEBUG_MODE", False),
            log_level=_get_str("LOG_LEVEL", "INFO"),
            log_format=_get_str("LOG_FORMAT", "text"),
            scheduler_tick_seconds=_get_int("SCHEDULER_TICK_SECONDS", 60),
            db_pool_size=_get_int("DB_POOL_SIZE", 3),
            api_timeout=_get_int("API_TIMEOUT", 5),
            cache_ttl=_get_int("CACHE_TTL", 3600),
            max_concurrent_streams=_get_int("MAX_CONCURRENT_STREAMS", 2),
            lightweight_mode=_get_bool("LIGHTWEIGHT_MODE", True),
            miniapp_api_enabled=miniapp_api_enabled,
            miniapp_api_host=miniapp_api_host,
            miniapp_api_port=_get_port("MINIAPP_API_PORT", 8080),
            miniapp_init_data_max_age=_get_positive_int(
                "MINIAPP_INIT_DATA_MAX_AGE", 3600
            ),
            miniapp_allowed_origin=miniapp_allowed_origin,
            miniapp_api_concurrency_limit=_get_positive_int(
                "MINIAPP_API_CONCURRENCY_LIMIT", 50
            ),
        )

    def is_owner(self, user_id: int) -> bool:
        """هل هذا المستخدم هو مالك البوت؟"""
        return user_id == self.owner_id
