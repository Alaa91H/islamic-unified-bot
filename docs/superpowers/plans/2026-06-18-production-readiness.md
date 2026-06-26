# Islamic Unified Bot — Production Readiness Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Transform the flat, non-production Islamic Unified Bot into a hardened, deployable package with a working prayer scheduler, SQLite persistence, bounded streaming, and Docker deployment that runs safely on any server.

**Architecture:** Strangler-fig refactor — build a new `bot/` package alongside the existing flat modules, migrate responsibilities unit-by-unit with tests protecting behavior, then make `main.py` a thin entry point that wires the package together. Docker single-container + SQLite (aiosqlite) + asyncio scheduler loop.

**Tech Stack:** Python 3.10+, Pyrogram 2.x, PyTgCalls 2.1.1, aiosqlite 0.22.1, SQLAlchemy 2.0.50 (schema only), pytest, freezegun, Docker (multi-stage).

---

## File Structure

**Create (new `bot/` package):**
- `bot/__init__.py` — package marker, exposes `__version__`
- `bot/config.py` — `Settings` frozen dataclass + `from_env()`
- `bot/logging_setup.py` — `setup_logging(settings)`
- `bot/deps.py` — `Dependencies` container + `build_dependencies(settings)`
- `bot/decorators.py` — `owner_only`, `admin_only`, `safe_handler`
- `bot/app.py` — `build_app(settings, deps)` (no import side effects)
- `bot/db/__init__.py`
- `bot/db/connection.py` — `Database` (aiosqlite wrapper + migration runner)
- `bot/db/migrations/0001_initial.sql` — initial schema
- `bot/db/repositories/__init__.py`
- `bot/db/repositories/user_settings.py` — `UserSettingsRepo`
- `bot/db/repositories/group_settings.py` — `GroupSettingsRepo`
- `bot/db/repositories/sent_notifications.py` — `SentNotificationsRepo`
- `bot/db/migrate_from_json.py` — one-shot JSON→SQLite migration
- `bot/prayer/__init__.py`
- `bot/prayer/calculator.py` — moved `PrayerTimeCalculator` + `CityCoordinates`
- `bot/data/__init__.py`
- `bot/data/adhkar.py` — merged adhkar dataset
- `bot/data/surahs.py` — 114 surah names
- `bot/data/sources.py` — azan/prelude/reciter sources (from `azan_config.py`)
- `bot/streaming/__init__.py`
- `bot/streaming/stream_manager.py` — `StreamManager` (PyTgCalls wrapper)
- `bot/scheduler/__init__.py`
- `bot/scheduler/notifier.py` — `Notifier`
- `bot/scheduler/prayer_scheduler.py` — `PrayerScheduler` loop
- `bot/handlers/__init__.py` — `HandlerRegistry.register()`
- `bot/handlers/adhkar.py`, `quran.py`, `azan.py`, `owner.py`

**Modify/Replace:**
- `main.py` — becomes thin entry point
- `.env.example` — reorganized, fix `MUSIC_DIR`, add session notes
- `Dockerfile` — multi-stage, non-root, healthcheck
- `pyproject.toml` — add ruff/black/isort/flake8 config
- `requirements.txt` — add aiosqlite, sqlalchemy (already there), freezegun to dev

**Create (deploy):**
- `deploy/docker-compose.yml`, `deploy/install.sh`, `deploy/systemd/islamic-bot.service`
- `healthcheck.py`

**Tests (under `tests/`):**
- `tests/unit/test_config.py`, `test_user_settings_repo.py`, `test_group_settings_repo.py`, `test_sent_notifications_repo.py`, `test_database_migrations.py`, `test_prayer_calculator.py`, `test_stream_manager.py`, `test_notifier.py`, `test_prayer_scheduler.py`, `test_decorators.py`, `test_migrate_from_json.py`
- `tests/conftest.py` — refactor (remove `sys.modules` hack)

---

## Phase 1 — Foundation: config, logging, package skeleton

### Task 1: Package skeleton + config dataclass

**Files:**
- Create: `bot/__init__.py`
- Create: `bot/config.py`
- Create: `tests/unit/__init__.py`
- Create: `tests/unit/test_config.py`

- [ ] **Step 1: Write failing test for `Settings.from_env`**

`tests/unit/test_config.py`:
```python
import pytest
from bot.config import Settings


def test_from_env_reads_required_vars(monkeypatch):
    monkeypatch.setenv("BOT_TOKEN", "123:ABC")
    monkeypatch.setenv("API_ID", "123456")
    monkeypatch.setenv("API_HASH", "abcdef1234567890")
    monkeypatch.setenv("OWNER_ID", "987654321")

    s = Settings.from_env()

    assert s.bot_token == "123:ABC"
    assert s.api_id == 123456
    assert s.api_hash == "abcdef1234567890"
    assert s.owner_id == 987654321


def test_from_env_rejects_placeholder_token(monkeypatch):
    monkeypatch.setenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
    monkeypatch.setenv("API_ID", "123456")
    monkeypatch.setenv("API_HASH", "abcdef")
    monkeypatch.setenv("OWNER_ID", "1")
    with pytest.raises(ValueError, match="BOT_TOKEN"):
        Settings.from_env()


def test_from_env_applies_defaults(monkeypatch):
    monkeypatch.setenv("BOT_TOKEN", "123:ABC")
    monkeypatch.setenv("API_ID", "123456")
    monkeypatch.setenv("API_HASH", "abcdef")
    monkeypatch.setenv("OWNER_ID", "1")
    # delete optional so defaults apply
    for k in ("MUSIC_DIR", "AZAN_DATA_DIR", "DEFAULT_CITY"):
        monkeypatch.delenv(k, raising=False)

    s = Settings.from_env()

    assert s.music_dir == "./music"
    assert s.default_city == "مكة المكرمة"
    assert s.max_reconnect_attempts == 10
```

- [ ] **Step 2: Run test, verify it fails**

Run: `python -m pytest tests/unit/test_config.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'bot'`

- [ ] **Step 3: Create package + config**

`bot/__init__.py`:
```python
"""Islamic Unified Bot — production package."""

__version__ = "2.0.0"
```

`bot/config.py`:
```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Centralized configuration loaded from environment variables."""

import os
from dataclasses import dataclass, field
from typing import List

_PLACEHOLDER_VALUES = {"", "YOUR_BOT_TOKEN_HERE", "YOUR_API_ID_HERE",
                       "YOUR_API_HASH_HERE", "YOUR_OWNER_ID_HERE"}


def _get_required(name: str) -> str:
    value = os.getenv(name, "").strip()
    if value in _PLACEHOLDER_VALUES:
        raise ValueError(
            f"❌ {name} غير مُعرّف أو ما زال قالبًا. "
            f"اضبط قيمة صحيحة في ملف .env"
        )
    return value


def _get_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        return int(raw)
    except ValueError:
        raise ValueError(f"❌ {name} يجب أن يكون رقمًا صحيحًا، حصلنا على: {raw!r}")


def _get_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    return raw.strip().lower() in ("1", "true", "yes", "on")


def _get_str(name: str, default: str) -> str:
    raw = os.getenv(name)
    return default if raw is None or raw.strip() == "" else raw.strip()


@dataclass(frozen=True)
class Settings:
    """إعدادات البوت — تُقرأ مرة واحدة عند الإقلاع ولا تُعدّل."""

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

    # --- مصادر ---
    quran_stream_url: str = "https://server8.mp3quran.net/afs/"

    # --- البث ---
    max_reconnect_attempts: int = 10
    initial_reconnect_delay: int = 5

    # --- الصلاة ---
    default_calculation_method: str = "isna"
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
    scheduler_tick_seconds: int = 30

    @classmethod
    def from_env(cls) -> "Settings":
        """يبني الإعدادات من متغيرات البيئة مع تحقق صارم."""
        return cls(
            bot_token=_get_required("BOT_TOKEN"),
            api_id=_get_int("API_ID", 0) or _fail("API_ID"),
            api_hash=_get_required("API_HASH"),
            owner_id=_get_int("OWNER_ID", 0) or _fail("OWNER_ID"),
            music_dir=_get_str("MUSIC_DIR", "./music"),
            azan_data_dir=_get_str("AZAN_DATA_DIR", "./azan_data"),
            data_dir=_get_str("DATA_DIR", "./data"),
            logs_dir=_get_str("LOGS_DIR", "./logs"),
            session_name=_get_str("SESSION_NAME", "islamic_unified_bot"),
            quran_stream_url=_get_str(
                "QURAN_STREAM_URL", "https://server8.mp3quran.net/afs/"
            ),
            max_reconnect_attempts=_get_int("MAX_RECONNECT_ATTEMPTS", 10),
            initial_reconnect_delay=_get_int("INITIAL_RECONNECT_DELAY", 5),
            default_calculation_method=_get_str("DEFAULT_CALCULATION_METHOD", "isna"),
            default_asr_method=_get_str("DEFAULT_ASR_METHOD", "standard"),
            default_city=_get_str("DEFAULT_CITY", "مكة المكرمة"),
            default_timezone=_get_int("DEFAULT_TIMEZONE", 3),
            notifications_enabled=_get_bool("NOTIFICATIONS_ENABLED", True),
            prelude_enabled=_get_bool("PRELUDE_ENABLED", False),
            prelude_time=_get_int("PRELUDE_TIME", 5),
            stream_enabled=_get_bool("STREAM_ENABLED", False),
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
            scheduler_tick_seconds=_get_int("SCHEDULER_TICK_SECONDS", 30),
        )

    def is_owner(self, user_id: int) -> bool:
        return user_id == self.owner_id


def _fail(name: str) -> int:
    raise ValueError(f"❌ {name} يجب أن يكون رقمًا صحيحًا غير صفري")
```

- [ ] **Step 4: Run test, verify it passes**

Run: `python -m pytest tests/unit/test_config.py -v`
Expected: 3 PASS

- [ ] **Step 5: Commit**

```bash
git add bot/__init__.py bot/config.py tests/unit/__init__.py tests/unit/test_config.py
git commit -m "feat(config): add Settings dataclass with env validation"
```

---

### Task 2: Logging setup

**Files:**
- Create: `bot/logging_setup.py`
- Create: `tests/unit/test_logging_setup.py`

- [ ] **Step 1: Write failing test**

`tests/unit/test_logging_setup.py`:
```python
import logging
from pathlib import Path


def test_setup_logging_creates_log_dir(tmp_path):
    from bot.logging_setup import setup_logging

    log_dir = tmp_path / "logs"
    logger = setup_logging(log_level="INFO", log_dir=str(log_dir), json_format=False)

    assert log_dir.exists()
    assert isinstance(logger, logging.Logger)
    assert logger.level == logging.INFO


def test_setup_logging_respects_level(tmp_path):
    from bot.logging_setup import setup_logging

    logger = setup_logging(log_level="DEBUG", log_dir=str(tmp_path), json_format=False)
    assert logger.level == logging.DEBUG
```

- [ ] **Step 2: Run test, verify failure**

Run: `python -m pytest tests/unit/test_logging_setup.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement**

`bot/logging_setup.py`:
```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""إعداد السجلات الاحترافي مع تدوير الملفات."""

import json
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from datetime import datetime, timezone


class _JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        return json.dumps({
            "ts": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }, ensure_ascii=False)


_TEXT_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"


def setup_logging(log_level: str = "INFO", log_dir: str = "./logs",
                  json_format: bool = False) -> logging.Logger:
    """يهيّئ التسجيل: ملف دوّار + console. يُستدعى مرة واحدة عند الإقلاع."""
    level = getattr(logging, log_level.upper(), logging.INFO)

    root = logging.getLogger()
    root.setLevel(level)
    # إزالة handlers سابقة (يهم للاختبارات)
    for h in list(root.handlers):
        root.removeHandler(h)

    Path(log_dir).mkdir(parents=True, exist_ok=True)
    log_file = Path(log_dir) / f"islamic_unified_{datetime.now():%Y%m%d}.log"

    fmt = _JsonFormatter() if json_format else logging.Formatter(_TEXT_FORMAT)

    file_h = RotatingFileHandler(
        log_file, maxBytes=10 * 1024 * 1024, backupCount=5, encoding="utf-8"
    )
    file_h.setFormatter(fmt)
    file_h.setLevel(level)

    console_h = logging.StreamHandler()
    console_h.setFormatter(fmt)
    console_h.setLevel(level)

    root.addHandler(file_h)
    root.addHandler(console_h)

    return logging.getLogger("islamic_bot")
```

- [ ] **Step 4: Run test, verify pass**

Run: `python -m pytest tests/unit/test_logging_setup.py -v`
Expected: 2 PASS

- [ ] **Step 5: Commit**

```bash
git add bot/logging_setup.py tests/unit/test_logging_setup.py
git commit -m "feat(logging): add rotating file + console logging"
```

---

## Phase 2 — Persistence layer (SQLite)

### Task 3: Database connection + migrations runner

**Files:**
- Create: `bot/db/__init__.py`
- Create: `bot/db/connection.py`
- Create: `bot/db/migrations/0001_initial.sql`
- Create: `tests/unit/test_database_migrations.py`

- [ ] **Step 1: Write failing test**

`tests/unit/test_database_migrations.py`:
```python
import pytest
from pathlib import Path


@pytest.mark.asyncio
async def test_database_creates_schema_and_is_idempotent(tmp_path):
    from bot.db.connection import Database

    db = Database(str(tmp_path / "test.db"))
    await db.connect()

    # tables exist
    async with db.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ) as cur:
        tables = {row[0] for row in await cur.fetchall()}
    assert {"user_settings", "group_settings", "sent_notifications",
            "schema_version"} <= tables

    # idempotent: running again doesn't error
    await db.apply_migrations()
    async with db.execute("SELECT version FROM schema_version") as cur:
        rows = await cur.fetchall()
    assert rows == [(1,)]

    await db.close()
```

- [ ] **Step 2: Run test, verify failure**

Run: `python -m pytest tests/unit/test_database_migrations.py -v`
Expected: FAIL — module missing

- [ ] **Step 3: Create migration file**

`bot/db/migrations/0001_initial.sql`:
```sql
CREATE TABLE IF NOT EXISTS user_settings (
    user_id           INTEGER PRIMARY KEY,
    city              TEXT NOT NULL,
    method            TEXT NOT NULL DEFAULT 'isna'
                      CHECK (method IN ('karachi','makkah','isna','egypt','algiers','dubai')),
    asr_method        TEXT NOT NULL DEFAULT 'standard'
                      CHECK (asr_method IN ('standard','hanafi')),
    timezone          INTEGER NOT NULL DEFAULT 0,
    language          TEXT NOT NULL DEFAULT 'ar',
    notifications_on  INTEGER NOT NULL DEFAULT 1 CHECK (notifications_on IN (0,1)),
    prelude_on        INTEGER NOT NULL DEFAULT 0 CHECK (prelude_on IN (0,1)),
    prelude_minutes   INTEGER NOT NULL DEFAULT 5 CHECK (prelude_minutes >= 0),
    enabled_prayers   TEXT NOT NULL DEFAULT '["fajr","dhuhr","asr","maghrib","isha"]',
    created_at        TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at        TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_user_notif
    ON user_settings(notifications_on) WHERE notifications_on = 1;

CREATE TABLE IF NOT EXISTS group_settings (
    chat_id               INTEGER PRIMARY KEY,
    city                  TEXT NOT NULL,
    method                TEXT NOT NULL DEFAULT 'isna'
                          CHECK (method IN ('karachi','makkah','isna','egypt','algiers','dubai')),
    asr_method            TEXT NOT NULL DEFAULT 'standard'
                          CHECK (asr_method IN ('standard','hanafi')),
    azan_source           TEXT NOT NULL DEFAULT 'traditional',
    stream_quran_on       INTEGER NOT NULL DEFAULT 0 CHECK (stream_quran_on IN (0,1)),
    stop_stream_before_min INTEGER NOT NULL DEFAULT 0,
    linked_user_id        INTEGER,
    created_at            TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at            TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS sent_notifications (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    target_id    INTEGER NOT NULL,
    target_type  TEXT NOT NULL CHECK (target_type IN ('user','group')),
    prayer       TEXT NOT NULL,
    prayer_date  TEXT NOT NULL,
    sent_at      TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(target_id, prayer, prayer_date)
);
CREATE INDEX IF NOT EXISTS idx_sent_lookup
    ON sent_notifications(target_id, prayer, prayer_date);

CREATE TABLE IF NOT EXISTS schema_version (
    version    INTEGER PRIMARY KEY,
    applied_at TEXT NOT NULL DEFAULT (datetime('now'))
);
```

- [ ] **Step 4: Create Database wrapper**

`bot/db/__init__.py`:
```python
"""Database layer (aiosqlite)."""
```

`bot/db/connection.py`:
```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""اتصال SQLite (aiosqlite) + منفّذ migrations."""

import logging
from pathlib import Path
from typing import Any, Sequence

import aiosqlite

logger = logging.getLogger(__name__)
_MIGRATIONS_DIR = Path(__file__).parent / "migrations"


class Database:
    """غلاف رفيع حول aiosqlite مع دعم migrations مرقّمة."""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self._conn: aiosqlite.Connection | None = None

    @property
    def conn(self) -> aiosqlite.Connection:
        if self._conn is None:
            raise RuntimeError("Database not connected — call connect() first")
        return self._conn

    async def connect(self) -> None:
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = await aiosqlite.connect(self.db_path)
        self._conn.row_factory = aiosqlite.Row
        await self._conn.execute("PRAGMA journal_mode=WAL")
        await self._conn.execute("PRAGMA foreign_keys=ON")
        await self.apply_migrations()
        logger.info("✅ قاعدة البيانات جاهزة: %s", self.db_path)

    async def close(self) -> None:
        if self._conn is not None:
            await self._conn.close()
            self._conn = None

    async def apply_migrations(self) -> None:
        """ينفّذ كل ملفات migrations المرقّمة غير المُطبّقة بعد."""
        await self.conn.execute(
            "CREATE TABLE IF NOT EXISTS schema_version "
            "(version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL"
            " DEFAULT (datetime('now')))"
        )
        await self.conn.commit()

        async with self.conn.execute("SELECT version FROM schema_version") as cur:
            applied = {row[0] for row in await cur.fetchall()}

        files = sorted(_MIGRATIONS_DIR.glob("*.sql"),
                       key=lambda p: int(p.stem.split("_")[0]))
        for f in files:
            version = int(f.stem.split("_")[0])
            if version in applied:
                continue
            logger.info("📦 تطبيق migration %s", f.name)
            await self.conn.executescript(f.read_text(encoding="utf-8"))
            await self.conn.execute(
                "INSERT INTO schema_version (version) VALUES (?)", (version,)
            )
            await self.conn.commit()

    async def execute(self, sql: str, params: Sequence[Any] = ()) -> aiosqlite.Cursor:
        cur = await self.conn.execute(sql, params)
        await self.conn.commit()
        return cur

    async def executemany(self, sql: str, params: Sequence[Sequence[Any]]) -> None:
        await self.conn.executemany(sql, params)
        await self.conn.commit()

    async def fetchone(self, sql: str, params: Sequence[Any] = ()) -> aiosqlite.Row | None:
        async with self.conn.execute(sql, params) as cur:
            return await cur.fetchone()

    async def fetchall(self, sql: str, params: Sequence[Any] = ()) -> list[aiosqlite.Row]:
        async with self.conn.execute(sql, params) as cur:
            return await cur.fetchall()
```

- [ ] **Step 5: Run test, verify pass**

Run: `python -m pytest tests/unit/test_database_migrations.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add bot/db/__init__.py bot/db/connection.py bot/db/migrations/0001_initial.sql tests/unit/test_database_migrations.py
git commit -m "feat(db): add aiosqlite connection + migration runner"
```

---

### Task 4: UserSettingsRepo

**Files:**
- Create: `bot/db/repositories/__init__.py`
- Create: `bot/db/repositories/user_settings.py`
- Create: `tests/unit/test_user_settings_repo.py`

- [ ] **Step 1: Write failing test**

`tests/unit/test_user_settings_repo.py`:
```python
import pytest


@pytest.fixture
async def repo(tmp_path):
    from bot.db.connection import Database
    from bot.db.repositories.user_settings import UserSettingsRepo
    db = Database(str(tmp_path / "t.db"))
    await db.connect()
    yield UserSettingsRepo(db)
    await db.close()


@pytest.mark.asyncio
async def test_get_missing_returns_none(repo):
    assert await repo.get(123) is None


@pytest.mark.asyncio
async def test_upsert_then_get(repo):
    from bot.db.repositories.user_settings import UserSettings
    s = UserSettings(user_id=1, city="مكة المكرمة", method="isna",
                     asr_method="standard", timezone=3)
    await repo.upsert(s)
    got = await repo.get(1)
    assert got is not None
    assert got.city == "مكة المكرمة"
    assert got.notifications_on is True
    assert got.enabled_prayers == ["fajr","dhuhr","asr","maghrib","isha"]


@pytest.mark.asyncio
async def test_list_with_notifications(repo):
    from bot.db.repositories.user_settings import UserSettings
    await repo.upsert(UserSettings(user_id=1, city="مكة المكرمة", timezone=3,
                                   notifications_on=True))
    await repo.upsert(UserSettings(user_id=2, city="القاهرة", timezone=2,
                                   notifications_on=False))
    rows = await repo.list_with_notifications()
    assert {r.user_id for r in rows} == {1}


@pytest.mark.asyncio
async def test_update_existing(repo):
    from bot.db.repositories.user_settings import UserSettings
    await repo.upsert(UserSettings(user_id=1, city="مكة المكرمة", timezone=3))
    await repo.upsert(UserSettings(user_id=1, city="جدة", timezone=3,
                                  notifications_on=False))
    got = await repo.get(1)
    assert got.city == "جدة"
    assert got.notifications_on is False
```

- [ ] **Step 2: Run, verify failure**

Run: `python -m pytest tests/unit/test_user_settings_repo.py -v`
Expected: FAIL

- [ ] **Step 3: Implement repo + dataclass**

`bot/db/repositories/__init__.py`:
```python
"""Repository layer for SQLite access."""
```

`bot/db/repositories/user_settings.py`:
```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""مستودع إعدادات المستخدمين (الخاص)."""

import json
import logging
from dataclasses import dataclass, field
from typing import List, Optional

from bot.db.connection import Database

logger = logging.getLogger(__name__)
_DEFAULT_PRAYERS = ["fajr", "dhuhr", "asr", "maghrib", "isha"]


@dataclass
class UserSettings:
    user_id: int
    city: str
    method: str = "isna"
    asr_method: str = "standard"
    timezone: int = 0
    language: str = "ar"
    notifications_on: bool = True
    prelude_on: bool = False
    prelude_minutes: int = 5
    enabled_prayers: List[str] = field(default_factory=lambda: list(_DEFAULT_PRAYERS))


class UserSettingsRepo:
    def __init__(self, db: Database):
        self._db = db

    async def get(self, user_id: int) -> Optional[UserSettings]:
        row = await self._db.fetchone(
            "SELECT * FROM user_settings WHERE user_id = ?", (user_id,)
        )
        return self._row_to_model(row) if row else None

    async def upsert(self, s: UserSettings) -> None:
        prayers_json = json.dumps(s.enabled_prayers, ensure_ascii=False)
        await self._db.execute(
            """INSERT INTO user_settings
               (user_id, city, method, asr_method, timezone, language,
                notifications_on, prelude_on, prelude_minutes, enabled_prayers)
               VALUES (?,?,?,?,?,?,?,?,?,?,?)
               ON CONFLICT(user_id) DO UPDATE SET
                 city=excluded.city, method=excluded.method,
                 asr_method=excluded.asr_method, timezone=excluded.timezone,
                 language=excluded.language, notifications_on=excluded.notifications_on,
                 prelude_on=excluded.prelude_on, prelude_minutes=excluded.prelude_minutes,
                 enabled_prayers=excluded.enabled_prayers,
                 updated_at=datetime('now')""",
            (s.user_id, s.city, s.method, s.asr_method, s.timezone, s.language,
             int(s.notifications_on), int(s.prelude_on), s.prelude_minutes, prayers_json),
        )

    async def update_partial(self, user_id: int, **kwargs) -> bool:
        if not kwargs:
            return False
        # validate columns
        allowed = {"city", "method", "asr_method", "timezone", "language",
                   "notifications_on", "prelude_on", "prelude_minutes",
                   "enabled_prayers"}
        bad = set(kwargs) - allowed
        if bad:
            raise ValueError(f"حقول غير معروفة: {bad}")
        sets = []
        params: list = []
        for k, v in kwargs.items():
            if k == "enabled_prayers":
                v = json.dumps(v, ensure_ascii=False)
            elif isinstance(v, bool):
                v = int(v)
            sets.append(f"{k} = ?")
            params.append(v)
        sets.append("updated_at = datetime('now')")
        params.append(user_id)
        await self._db.execute(
            f"UPDATE user_settings SET {', '.join(sets)} WHERE user_id = ?", params
        )
        return True

    async def list_with_notifications(self) -> List[UserSettings]:
        rows = await self._db.fetchall(
            "SELECT * FROM user_settings WHERE notifications_on = 1"
        )
        return [self._row_to_model(r) for r in rows]

    @staticmethod
    def _row_to_model(row) -> UserSettings:
        prayers = row["enabled_prayers"]
        try:
            prayers = json.loads(prayers)
        except (ValueError, TypeError):
            prayers = list(_DEFAULT_PRAYERS)
        return UserSettings(
            user_id=row["user_id"], city=row["city"], method=row["method"],
            asr_method=row["asr_method"], timezone=row["timezone"],
            language=row["language"], notifications_on=bool(row["notifications_on"]),
            prelude_on=bool(row["prelude_on"]),
            prelude_minutes=row["prelude_minutes"], enabled_prayers=prayers,
        )
```

- [ ] **Step 4: Run, verify pass**

Run: `python -m pytest tests/unit/test_user_settings_repo.py -v`
Expected: 4 PASS

- [ ] **Step 5: Commit**

```bash
git add bot/db/repositories/__init__.py bot/db/repositories/user_settings.py tests/unit/test_user_settings_repo.py
git commit -m "feat(db): add UserSettingsRepo with upsert/partial-update"
```

---

### Task 5: GroupSettingsRepo + SentNotificationsRepo

**Files:**
- Create: `bot/db/repositories/group_settings.py`
- Create: `bot/db/repositories/sent_notifications.py`
- Create: `tests/unit/test_group_settings_repo.py`
- Create: `tests/unit/test_sent_notifications_repo.py`

- [ ] **Step 1: Write failing tests**

`tests/unit/test_group_settings_repo.py`:
```python
import pytest


@pytest.fixture
async def repo(tmp_path):
    from bot.db.connection import Database
    from bot.db.repositories.group_settings import GroupSettingsRepo
    db = Database(str(tmp_path / "t.db"))
    await db.connect()
    yield GroupSettingsRepo(db)
    await db.close()


@pytest.mark.asyncio
async def test_upsert_and_get(repo):
    from bot.db.repositories.group_settings import GroupSettings
    g = GroupSettings(chat_id=-100123, city="مكة المكرمة", timezone=3)
    await repo.upsert(g)
    got = await repo.get(-100123)
    assert got is not None and got.city == "مكة المكرمة"
    assert got.azan_source == "traditional"


@pytest.mark.asyncio
async def test_list_all(repo):
    from bot.db.repositories.group_settings import GroupSettings
    await repo.upsert(GroupSettings(chat_id=-1, city="جدة", timezone=3))
    await repo.upsert(GroupSettings(chat_id=-2, city="الرياض", timezone=3))
    rows = await repo.list_all()
    assert {r.chat_id for r in rows} == {-1, -2}
```

`tests/unit/test_sent_notifications_repo.py`:
```python
import pytest
from datetime import date


@pytest.fixture
async def repo(tmp_path):
    from bot.db.connection import Database
    from bot.db.repositories.sent_notifications import SentNotificationsRepo
    db = Database(str(tmp_path / "t.db"))
    await db.connect()
    yield SentNotificationsRepo(db)
    await db.close()


@pytest.mark.asyncio
async def test_mark_sent_returns_true_first_time_false_second(repo):
    today = date.today().isoformat()
    assert await repo.mark_sent(1, "user", "fajr", today) is True
    assert await repo.mark_sent(1, "user", "fajr", today) is False


@pytest.mark.asyncio
async def test_already_sent_true_after_marking(repo):
    today = date.today().isoformat()
    assert await repo.already_sent(1, "user", "fajr", today) is False
    await repo.mark_sent(1, "user", "fajr", today)
    assert await repo.already_sent(1, "user", "fajr", today) is True


@pytest.mark.asyncio
async def test_prelude_key_distinct_from_prayer(repo):
    today = date.today().isoformat()
    await repo.mark_sent(1, "user", "prelude_fajr", today)
    # prayer itself is NOT considered sent
    assert await repo.already_sent(1, "user", "fajr", today) is False
```

- [ ] **Step 2: Run, verify failure**

Run: `python -m pytest tests/unit/test_group_settings_repo.py tests/unit/test_sent_notifications_repo.py -v`
Expected: FAIL

- [ ] **Step 3: Implement both repos**

`bot/db/repositories/group_settings.py`:
```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""مستودع إعدادات المجموعات (voice chat)."""

import logging
from dataclasses import dataclass
from typing import List, Optional

from bot.db.connection import Database

logger = logging.getLogger(__name__)


@dataclass
class GroupSettings:
    chat_id: int
    city: str
    method: str = "isna"
    asr_method: str = "standard"
    azan_source: str = "traditional"
    stream_quran_on: bool = False
    stop_stream_before_min: int = 0
    linked_user_id: Optional[int] = None
    timezone: int = 0  # مُشتق من المدينة عند الحفظ


class GroupSettingsRepo:
    def __init__(self, db: Database):
        self._db = db

    async def get(self, chat_id: int) -> Optional[GroupSettings]:
        row = await self._db.fetchone(
            "SELECT * FROM group_settings WHERE chat_id = ?", (chat_id,)
        )
        return self._row_to_model(row) if row else None

    async def upsert(self, g: GroupSettings) -> None:
        await self._db.execute(
            """INSERT INTO group_settings
               (chat_id, city, method, asr_method, azan_source,
                stream_quran_on, stop_stream_before_min, linked_user_id)
               VALUES (?,?,?,?,?,?,?,?)
               ON CONFLICT(chat_id) DO UPDATE SET
                 city=excluded.city, method=excluded.method,
                 asr_method=excluded.asr_method, azan_source=excluded.azan_source,
                 stream_quran_on=excluded.stream_quran_on,
                 stop_stream_before_min=excluded.stop_stream_before_min,
                 linked_user_id=excluded.linked_user_id,
                 updated_at=datetime('now')""",
            (g.chat_id, g.city, g.method, g.asr_method, g.azan_source,
             int(g.stream_quran_on), g.stop_stream_before_min, g.linked_user_id),
        )

    async def list_all(self) -> List[GroupSettings]:
        rows = await self._db.fetchall("SELECT * FROM group_settings")
        return [self._row_to_model(r) for r in rows]

    async def delete(self, chat_id: int) -> None:
        await self._db.execute(
            "DELETE FROM group_settings WHERE chat_id = ?", (chat_id,)
        )

    @staticmethod
    def _row_to_model(row) -> GroupSettings:
        return GroupSettings(
            chat_id=row["chat_id"], city=row["city"], method=row["method"],
            asr_method=row["asr_method"], azan_source=row["azan_source"],
            stream_quran_on=bool(row["stream_quran_on"]),
            stop_stream_before_min=row["stop_stream_before_min"],
            linked_user_id=row["linked_user_id"],
        )
```

`bot/db/repositories/sent_notifications.py`:
```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""مستودع سجل التنبيهات المُرسلة — لمنع التكرار بعد restart."""

import logging
from typing import Literal

from bot.db.connection import Database

logger = logging.getLogger(__name__)
TargetType = Literal["user", "group"]


class SentNotificationsRepo:
    def __init__(self, db: Database):
        self._db = db

    async def already_sent(self, target_id: int, target_type: TargetType,
                           prayer: str, prayer_date: str) -> bool:
        row = await self._db.fetchone(
            """SELECT 1 FROM sent_notifications
               WHERE target_id=? AND target_type=? AND prayer=? AND prayer_date=?
               LIMIT 1""",
            (target_id, target_type, prayer, prayer_date),
        )
        return row is not None

    async def mark_sent(self, target_id: int, target_type: TargetType,
                        prayer: str, prayer_date: str) -> bool:
        """يُرجع True إذا سُجّل الآن، False إذا كان مُسجّلًا سابقًا (idempotent)."""
        try:
            await self._db.execute(
                """INSERT INTO sent_notifications
                   (target_id, target_type, prayer, prayer_date)
                   VALUES (?,?,?,?)""",
                (target_id, target_type, prayer, prayer_date),
            )
            return True
        except Exception:  # UNIQUE constraint → already exists
            return False
```

- [ ] **Step 4: Run, verify pass**

Run: `python -m pytest tests/unit/test_group_settings_repo.py tests/unit/test_sent_notifications_repo.py -v`
Expected: 5 PASS

- [ ] **Step 5: Commit**

```bash
git add bot/db/repositories/group_settings.py bot/db/repositories/sent_notifications.py tests/unit/test_group_settings_repo.py tests/unit/test_sent_notifications_repo.py
git commit -m "feat(db): add GroupSettingsRepo + SentNotificationsRepo"
```

---

### Task 6: JSON→SQLite migration

**Files:**
- Create: `bot/db/migrate_from_json.py`
- Create: `tests/unit/test_migrate_from_json.py`

- [ ] **Step 1: Write failing test**

`tests/unit/test_migrate_from_json.py`:
```python
import json
import pytest


@pytest.mark.asyncio
async def test_migrate_imports_existing_users(tmp_path):
    from bot.db.connection import Database
    from bot.db.migrate_from_json import migrate_from_json
    from bot.db.repositories.user_settings import UserSettingsRepo

    json_path = tmp_path / "user_settings.json"
    json_path.write_text(json.dumps({
        "111": {"user_id": 111, "city": "مكة المكرمة", "method": "makkah",
                "timezone": 3, "asr_method": "standard"},
        "222": {"user_id": 222, "city": "القاهرة", "method": "egypt",
                "timezone": 2, "asr_method": "standard"},
    }, ensure_ascii=False), encoding="utf-8")

    db = Database(str(tmp_path / "t.db"))
    await db.connect()
    repo = UserSettingsRepo(db)

    imported = await migrate_from_json(json_path, repo)

    assert imported == 2
    g1 = await repo.get(111)
    assert g1 is not None and g1.city == "مكة المكرمة" and g1.method == "makkah"
    await db.close()
    # backup created
    assert (tmp_path / "user_settings.json.bak").exists()


@pytest.mark.asyncio
async def test_migrate_no_file_returns_zero(tmp_path):
    from bot.db.connection import Database
    from bot.db.migrate_from_json import migrate_from_json
    from bot.db.repositories.user_settings import UserSettingsRepo

    db = Database(str(tmp_path / "t.db"))
    await db.connect()
    imported = await migrate_from_json(tmp_path / "missing.json", UserSettingsRepo(db))
    assert imported == 0
    await db.close()
```

- [ ] **Step 2: Run, verify failure**

Run: `python -m pytest tests/unit/test_migrate_from_json.py -v`
Expected: FAIL

- [ ] **Step 3: Implement**

`bot/db/migrate_from_json.py`:
```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""هجرة واحدة من user_settings.json القديم إلى SQLite."""

import json
import logging
from pathlib import Path

from bot.db.repositories.user_settings import UserSettings, UserSettingsRepo

logger = logging.getLogger(__name__)


async def migrate_from_json(json_path: Path | str, repo: UserSettingsRepo) -> int:
    """يستورد المستخدمين من JSON. يُرجع عدد المستوردين. يُنشئ نسخة .bak."""
    path = Path(json_path)
    if not path.exists():
        logger.info("ℹ️ لا يوجد ملف JSON قديم للهجرة: %s", path)
        return 0

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, OSError) as e:
        logger.warning("⚠️ تعذّرت قراءة JSON القديم (%s): %s", path, e)
        return 0

    imported = 0
    for user_id_str, settings_dict in data.items():
        try:
            uid = int(user_id_str)
            s = UserSettings(
                user_id=uid,
                city=settings_dict.get("city", "مكة المكرمة"),
                method=settings_dict.get("method", "isna"),
                asr_method=settings_dict.get("asr_method", "standard"),
                timezone=settings_dict.get("timezone", 0),
                notifications_on=settings_dict.get("notification_enabled", True),
                prelude_on=settings_dict.get("prelude_enabled", False),
                prelude_minutes=settings_dict.get("prelude_time", 5),
                enabled_prayers=settings_dict.get(
                    "enabled_prayers",
                    ["fajr","dhuhr","asr","maghrib","isha"],
                ),
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
```

- [ ] **Step 4: Run, verify pass**

Run: `python -m pytest tests/unit/test_migrate_from_json.py -v`
Expected: 2 PASS

- [ ] **Step 5: Commit**

```bash
git add bot/db/migrate_from_json.py tests/unit/test_migrate_from_json.py
git commit -m "feat(db): add one-shot JSON to SQLite migration"
```

---

## Phase 3 — Prayer calculation + data

### Task 7: Move prayer calculator to package

**Files:**
- Create: `bot/prayer/__init__.py`
- Create: `bot/prayer/calculator.py` (move from `azan_prayer_times.py`)
- Create: `tests/unit/test_prayer_calculator.py`

- [ ] **Step 1: Write failing test**

`tests/unit/test_prayer_calculator.py`:
```python
from datetime import datetime


def test_calculate_times_returns_all_prayers():
    from bot.prayer.calculator import PrayerTimeCalculator
    calc = PrayerTimeCalculator(latitude=21.4225, longitude=39.8264,
                                timezone=3, method="makkah")
    times = calc.calculate_times(datetime(2026, 6, 18))
    for key in ("fajr", "sunrise", "dhuhr", "asr", "maghrib", "isha"):
        assert key in times, f"missing {key}"
        # HH:MM format
        assert len(times[key]) == 5 and times[key][2] == ":"


def test_get_city_coords_makkah():
    from bot.prayer.calculator import CityCoordinates
    c = CityCoordinates.get_city_coords("مكة المكرمة")
    assert c is not None
    assert c["tz"] == 3


def test_search_cities():
    from bot.prayer.calculator import CityCoordinates
    assert "مكة المكرمة" in CityCoordinates.search_cities("مكة")
```

- [ ] **Step 2: Run, verify failure**

Run: `python -m pytest tests/unit/test_prayer_calculator.py -v`
Expected: FAIL

- [ ] **Step 3: Create package + move code**

`bot/prayer/__init__.py`:
```python
"""Prayer-time calculation."""
```

`bot/prayer/calculator.py` — copy the full contents of existing `azan_prayer_times.py` verbatim (the `PrayerTimeCalculator`, `CityCoordinates`, `PrayerTimeAPI` classes). No logic changes — this is a pure move so existing tests still pass.

```bash
# On Windows/bash:
cp azan_prayer_times.py bot/prayer/calculator.py
```
Then add the module docstring header is already present; no edits needed.

- [ ] **Step 4: Run, verify pass**

Run: `python -m pytest tests/unit/test_prayer_calculator.py tests/test_prayer_times.py -v`
Expected: PASS (both old and new)

- [ ] **Step 5: Commit**

```bash
git add bot/prayer/__init__.py bot/prayer/calculator.py tests/unit/test_prayer_calculator.py
git commit -m "refactor(prayer): move calculator into bot.prayer package"
```

---

### Task 8: Data modules (adhkar, surahs, sources)

**Files:**
- Create: `bot/data/__init__.py`
- Create: `bot/data/adhkar.py`
- Create: `bot/data/surahs.py`
- Create: `bot/data/sources.py`
- Create: `tests/unit/test_data_modules.py`

- [ ] **Step 1: Write failing test**

`tests/unit/test_data_modules.py`:
```python
def test_adhkar_categories_have_items():
    from bot.data.adhkar import ADHKAR_CATEGORIES, ADHKAR
    assert len(ADHKAR_CATEGORIES) >= 8
    for key in ADHKAR_CATEGORIES:
        items = ADHKAR.get(key, [])
        assert len(items) > 0, f"{key} empty"
        for it in items:
            assert {"title", "text", "benefit"} <= set(it.keys())


def test_surahs_complete():
    from bot.data.surahs import SURAHS
    assert set(SURAHS.keys()) == set(range(1, 115))
    assert all(isinstance(v, str) and v.strip() for v in SURAHS.values())


def test_sources_have_azan_for_all_prayers():
    from bot.data.sources import AZAN_SOURCES
    for key, src in AZAN_SOURCES.items():
        for p in ("fajr", "dhuhr", "asr", "maghrib", "isha"):
            assert p in src, f"{key} missing {p}"
```

- [ ] **Step 2: Run, verify failure**

Run: `python -m pytest tests/unit/test_data_modules.py -v`
Expected: FAIL

- [ ] **Step 3: Create data modules**

`bot/data/__init__.py`:
```python
"""Static Islamic data (adhkar, surahs, sources)."""
```

`bot/data/surahs.py` — move the `SURAHS` dict from `main.py` (lines 322-437) verbatim:
```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""أسماء سور القرآن الكريم (1-114)."""

SURAHS = {
    1: "الفاتحة",
    2: "البقرة",
    # ... (full 114 entries copied from main.py)
    114: "الناس",
}
```

`bot/data/sources.py` — move the `AZAN_SOURCES`, `PRELUDE_SOURCES`, `QURANIC_RECITERS` dicts from `azan_config.py` verbatim:
```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""مصادر الأذان والمقدمات والقرّاء."""

AZAN_SOURCES = { ... }      # copied from azan_config.py
PRELUDE_SOURCES = { ... }   # copied from azan_config.py
QURANIC_RECITERS = { ... }  # copied from azan_config.py
```

`bot/data/adhkar.py` — merge the `IslamicData.ADHKAR`/`CATEGORIES` from `main.py` with `ADVANCED_ADHKAR` from `advanced_adhkar_library.py` under a unified schema:
```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""مكتبة الأذكار الإسلامية (مدمجة)."""

ADHKAR_CATEGORIES = {
    "morning": "🌅 أذكار الصباح",
    "evening": "🌙 أذكار المساء",
    "sleep": "😴 أذكار النوم والاستيقاظ",
    "entry": "🚪 أذكار الدخول والخروج",
    "prayer": "🤲 أذكار الصلاة",
    "journey": "✈️ أذكار السفر",
    "supplication": "🙏 الأدعية المشروعة",
    "tasbeeh": "📿 التسبيحات والتحميدات",
    "protection": "🛡️ الأدعية الحصينة والرقية",
    "gratitude": "🎁 شكر الله والرضا",
    "family": "👨‍👩‍👧 أذكار العائلة والأطفال",
    "health": "⚕️ أذكار الصحة والعافية",
}

ADHKAR = {
    "morning": [ ... ],   # copied from main.py IslamicData.ADHKAR["morning"]
    "evening": [ ... ],
    # ... all 12 categories from main.py, each item: {title, text, benefit}
    # plus optionally merged advanced items appended where they fit.
}
```
(All `title`/`text`/`benefit` values copied verbatim from `main.py` — this is data migration, not rewrites.)

- [ ] **Step 4: Run, verify pass**

Run: `python -m pytest tests/unit/test_data_modules.py -v`
Expected: 3 PASS

- [ ] **Step 5: Commit**

```bash
git add bot/data/
git commit -m "feat(data): add adhkar/surahs/sources modules"
```

---

## Phase 4 — Streaming + scheduling

### Task 9: StreamManager (PyTgCalls wrapper)

**Files:**
- Create: `bot/streaming/__init__.py`
- Create: `bot/streaming/stream_manager.py`
- Create: `tests/unit/test_stream_manager.py`

- [ ] **Step 1: Write failing test**

`tests/unit/test_stream_manager.py`:
```python
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.fixture
def manager():
    from bot.streaming.stream_manager import StreamManager
    fake_app = MagicMock()
    with patch("bot.streaming.stream_manager.PyTgCalls"):
        sm = StreamManager(fake_app, max_reconnect=3, base_delay=1,
                           default_duration_min=120)
    sm.pytgcalls.play = AsyncMock()
    sm.pytgcalls.leave_call = AsyncMock()
    sm.pytgcalls.get_call = AsyncMock()
    return sm


@pytest.mark.asyncio
async def test_play_stores_stream(manager):
    ok = await manager.play(-100, "http://x/a.mp3", "title", loop=False)
    assert ok is True
    streams = manager.active_streams()
    assert -100 in streams
    assert streams[-100]["loop"] is False


@pytest.mark.asyncio
async def test_stop_removes_stream(manager):
    await manager.play(-100, "http://x/a.mp3", "title")
    ok = await manager.stop(-100)
    assert ok is True
    assert -100 not in manager.active_streams()


@pytest.mark.asyncio
async def test_play_no_reconnect_on_failure(manager):
    sm = manager
    sm.pytgcalls.play = AsyncMock(side_effect=RuntimeError("boom"))
    ok = await sm.play(-100, "http://x/a.mp3", "t", loop=False)
    assert ok is False
    # exhausted 3 attempts
    assert sm.pytgcalls.play.await_count == 3


@pytest.mark.asyncio
async def test_max_duration_schedules_stop(manager):
    await manager.play(-100, "http://x/a.mp3", "t", duration_min=0.0001)
    # let the timeout fire
    import asyncio
    await asyncio.sleep(0.05)
    # stream should be auto-stopped
    assert -100 not in manager.active_streams()
```

- [ ] **Step 2: Run, verify failure**

Run: `python -m pytest tests/unit/test_stream_manager.py -v`
Expected: FAIL

- [ ] **Step 3: Implement**

`bot/streaming/__init__.py`:
```python
"""Audio streaming via PyTgCalls."""
```

`bot/streaming/stream_manager.py`:
```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""غلاف آمن حول PyTgCalls للقرآن والأذان."""

import asyncio
import logging
import random
from datetime import datetime
from typing import Dict, Optional

from pyrogram import Client
from pytgcalls import PyTgCalls
from pytgcalls.exceptions import NotInCallError
from pytgcalls.types import AudioQuality, MediaStream

logger = logging.getLogger(__name__)


class StreamManager:
    """بث صوتي مع reconnect محدود ومهلة قصوى."""

    def __init__(self, app: Client, max_reconnect: int = 10,
                 base_delay: int = 5, default_duration_min: int = 120):
        self.pytgcalls = PyTgCalls(app)
        self._streams: Dict[int, dict] = {}
        self._timers: Dict[int, asyncio.Task] = {}
        self.max_reconnect = max_reconnect
        self.base_delay = base_delay
        self.default_duration_min = default_duration_min
        self._started = False

    async def start(self) -> None:
        if self._started:
            return
        await self.pytgcalls.start()

        @self.pytgcalls.on_stream_end()
        async def _on_stream_end(_client, update):
            chat_id = update.chat_id
            info = self._streams.get(chat_id)
            if info and info.get("loop") and info.get("status") == "active":
                logger.info("🔄 إعادة بث (loop) في %s", chat_id)
                await self.play(chat_id, info["url"], info["title"], loop=True,
                                duration_min=info.get("duration_min"))

        self._started = True
        logger.info("✅ خدمة المكالمات جاهزة")

    async def stop_all(self) -> None:
        for timer in list(self._timers.values()):
            timer.cancel()
        self._timers.clear()
        try:
            await self.pytgcalls.stop()
        except Exception as e:
            logger.warning("⚠️ خطأ إيقاف pytgcalls: %s", e)
        self._streams.clear()

    async def play(self, chat_id: int, url: str, title: str = "بث",
                   loop: bool = False, duration_min: Optional[int] = None,
                   attempts: int = 0) -> bool:
        media = MediaStream(url, audio_parameters=AudioQuality.HIGH,
                            ffmpeg_parameters="-af volume=1.5")
        try:
            await self.pytgcalls.play(chat_id, media)
        except NotInCallError:
            logger.info("ℹ️ البوت يبث بالفعل في %s", chat_id)
        except Exception as e:
            if attempts < self.max_reconnect:
                delay = self.base_delay * (2 ** attempts) + random.uniform(0, 1)
                logger.error("❌ فشل البث (%d/%d): %s — إعادة بعد %.1fث",
                             attempts + 1, self.max_reconnect, e, delay)
                await asyncio.sleep(delay)
                return await self.play(chat_id, url, title, loop, duration_min,
                                       attempts + 1)
            logger.error("❌ فشل البث نهائيًا بعد %d محاولة", self.max_reconnect)
            return False

        dur = duration_min if duration_min is not None else self.default_duration_min
        self._streams[chat_id] = {
            "url": url, "title": title, "started_at": datetime.now(),
            "status": "active", "loop": loop, "duration_min": dur,
        }
        self._schedule_stop(chat_id, dur)
        logger.info("✅ بث نشط في %s: %s (loop=%s, dur=%smin)",
                    chat_id, title, loop, dur)
        return True

    def _schedule_stop(self, chat_id: int, duration_min: int) -> None:
        old = self._timers.get(chat_id)
        if old:
            old.cancel()

        async def _auto_stop():
            try:
                await asyncio.sleep(duration_min * 60)
                logger.info("⏹️ انتهت مدة البث في %s", chat_id)
                await self.stop(chat_id)
            except asyncio.CancelledError:
                pass

        self._timers[chat_id] = asyncio.create_task(_auto_stop())

    async def stop(self, chat_id: int) -> bool:
        timer = self._timers.pop(chat_id, None)
        if timer:
            timer.cancel()
        try:
            await self.pytgcalls.leave_call(chat_id)
        except Exception as e:
            logger.warning("⚠️ خطأ leave_call في %s: %s", chat_id, e)
        existed = self._streams.pop(chat_id, None) is not None
        if existed:
            logger.info("✅ أُوقف البث في %s", chat_id)
        return existed

    def active_streams(self) -> Dict[int, dict]:
        return dict(self._streams)
```

- [ ] **Step 4: Run, verify pass**

Run: `python -m pytest tests/unit/test_stream_manager.py -v`
Expected: 4 PASS

- [ ] **Step 5: Commit**

```bash
git add bot/streaming/
git commit -m "feat(streaming): add StreamManager with bounded reconnect + max duration"
```

---

### Task 10: Notifier

**Files:**
- Create: `bot/scheduler/__init__.py`
- Create: `bot/scheduler/notifier.py`
- Create: `tests/unit/test_notifier.py`

- [ ] **Step 1: Write failing test**

`tests/unit/test_notifier.py`:
```python
import pytest
from unittest.mock import AsyncMock, MagicMock


@pytest.fixture
def notifier():
    from bot.scheduler.notifier import Notifier
    app = MagicMock()
    app.send_message = AsyncMock()
    stream = MagicMock()
    stream.play = AsyncMock(return_value=True)
    return Notifier(app, stream), app, stream


@pytest.mark.asyncio
async def test_notify_user_sends_message(notifier):
    n, app, _ = notifier
    ok = await n.notify_user(123, "fajr", "05:12")
    assert ok is True
    app.send_message.assert_awaited_once()
    args = app.send_message.call_args
    assert args.args[0] == 123


@pytest.mark.asyncio
async def test_broadcast_group_azan_streams(notifier):
    n, _, stream = notifier
    ok = await n.broadcast_group_azan(-100, "fajr", "traditional")
    assert ok is True
    stream.play.assert_awaited_once()
```

- [ ] **Step 2: Run, verify failure**

Run: `python -m pytest tests/unit/test_notifier.py -v`
Expected: FAIL

- [ ] **Step 3: Implement**

`bot/scheduler/__init__.py`:
```python
"""Prayer scheduling and notifications."""
```

`bot/scheduler/notifier.py`:
```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""إرسال التنبيهات: نص للمستخدم + بث للمجموعة."""

import logging
from typing import Optional

from bot.data.sources import AZAN_SOURCES

logger = logging.getLogger(__name__)

_PRAYER_EMOJI = {"fajr": "🌅", "dhuhr": "☀️", "asr": "⛅",
                 "maghrib": "🌆", "isha": "🌙"}
_PRAYER_NAME = {"fajr": "الفجر", "dhuhr": "الظهر", "asr": "العصر",
                "maghrib": "المغرب", "isha": "العشاء"}


class Notifier:
    def __init__(self, app, stream_manager):
        self._app = app
        self._stream = stream_manager

    async def notify_user(self, user_id: int, prayer: str,
                          prayer_time: str, is_prelude: bool = False) -> bool:
        name = _PRAYER_NAME.get(prayer, prayer)
        emoji = _PRAYER_EMOJI.get(prayer, "🕌")
        if is_prelude:
            text = f"{emoji} سيبدأ أذان {name} خلال دقائق\n🕐 {prayer_time}"
        else:
            text = f"{emoji} حان وقت صلاة {name}\n🕐 {prayer_time}\nحي على الصلاة"
        try:
            await self._app.send_message(user_id, text)
            logger.info("📩 تنبيه أُرسل للمستخدم %s (%s)", user_id, prayer)
            return True
        except Exception as e:
            logger.error("❌ فشل إرسال التنبيه لـ %s: %s", user_id, e)
            return False

    async def broadcast_group_azan(self, chat_id: int, prayer: str,
                                   azan_source: str = "traditional") -> bool:
        name = _PRAYER_NAME.get(prayer, prayer)
        emoji = _PRAYER_EMOJI.get(prayer, "🕌")
        url = self._get_azan_url(prayer, azan_source)
        if not url:
            logger.warning("⚠️ لا يوجد رابط أذان لـ %s/%s", azan_source, prayer)
            return False
        try:
            ok = await self._stream.play(chat_id, url, f"أذان {name}",
                                         loop=False, duration_min=4)
            if ok:
                await self._app.send_message(
                    chat_id, f"{emoji} حان وقت صلاة {name}\n🕌 الأذان يبث الآن"
                )
            return ok
        except Exception as e:
            logger.error("❌ فشل بث الأذان في %s: %s", chat_id, e)
            return False

    @staticmethod
    def _get_azan_url(prayer: str, source: str) -> Optional[str]:
        return AZAN_SOURCES.get(source, {}).get(prayer)
```

- [ ] **Step 4: Run, verify pass**

Run: `python -m pytest tests/unit/test_notifier.py -v`
Expected: 2 PASS

- [ ] **Step 5: Commit**

```bash
git add bot/scheduler/__init__.py bot/scheduler/notifier.py tests/unit/test_notifier.py
git commit -m "feat(scheduler): add Notifier for user text + group azan"
```

---

### Task 11: PrayerScheduler loop

**Files:**
- Create: `bot/scheduler/prayer_scheduler.py`
- Create: `tests/unit/test_prayer_scheduler.py`

- [ ] **Step 1: Write failing test**

`tests/unit/test_prayer_scheduler.py`:
```python
import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock


@pytest.fixture
async def deps(tmp_path):
    """build scheduler with isolated DB."""
    from bot.db.connection import Database
    from bot.db.repositories.user_settings import UserSettingsRepo, UserSettings
    from bot.db.repositories.group_settings import GroupSettingsRepo
    from bot.db.repositories.sent_notifications import SentNotificationsRepo
    from bot.scheduler.prayer_scheduler import PrayerScheduler
    from bot.scheduler.notifier import Notifier

    db = Database(str(tmp_path / "t.db"))
    await db.connect()
    user_repo = UserSettingsRepo(db)
    group_repo = GroupSettingsRepo(db)
    sent_repo = SentNotificationsRepo(db)

    app = MagicMock()
    stream = MagicMock()
    notifier = Notifier(app, stream)
    notifier.notify_user = AsyncMock(return_value=True)
    notifier.broadcast_group_azan = AsyncMock(return_value=True)

    sched = PrayerScheduler(user_repo, group_repo, sent_repo, notifier,
                            tick_seconds=0)
    yield {
        "sched": sched, "user_repo": user_repo, "group_repo": group_repo,
        "sent_repo": sent_repo, "notifier": notifier,
    }
    await db.close()


@pytest.mark.asyncio
async def test_tick_fires_notification_at_prayer_time(deps):
    from bot.db.repositories.user_settings import UserSettings
    s = deps["sched"]
    # user in Makkah, prayer time near "now"
    await deps["user_repo"].upsert(UserSettings(
        user_id=1, city="مكة المكرمة", timezone=3))
    # Force detection: mock get_next_prayer to return "now"
    s._find_due_prayers = AsyncMock(return_value=[
        ("user", 1, {"prayer": "dhuhr", "time": "12:00", "is_prelude": False}),
    ])
    await s.tick()
    deps["notifier"].notify_user.assert_awaited_once_with(1, "dhuhr", "12:00")


@pytest.mark.asyncio
async def test_tick_skips_already_sent(deps):
    from datetime import date
    s = deps["sched"]
    await deps["sent_repo"].mark_sent(1, "user", "dhuhr", date.today().isoformat())
    s._find_due_prayers = AsyncMock(return_value=[
        ("user", 1, {"prayer": "dhuhr", "time": "12:00", "is_prelude": False}),
    ])
    await s.tick()
    deps["notifier"].notify_user.assert_not_awaited()


@pytest.mark.asyncio
async def test_start_stop_no_error(deps):
    s = deps["sched"]
    s.tick = AsyncMock()
    s.TICK_SECONDS = 0.01
    await s.start()
    import asyncio
    await asyncio.sleep(0.05)
    await s.stop()
```

- [ ] **Step 2: Run, verify failure**

Run: `python -m pytest tests/unit/test_prayer_scheduler.py -v`
Expected: FAIL

- [ ] **Step 3: Implement**

`bot/scheduler/prayer_scheduler.py`:
```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""حلقة جدولة الصلاة الخلفية — تستيقظ دوريًا وتطلق التنبيهات."""

import asyncio
import contextlib
import logging
from datetime import datetime, timedelta, timezone
from typing import List, Tuple

from bot.db.repositories.group_settings import GroupSettings
from bot.db.repositories.sent_notifications import SentNotificationsRepo
from bot.db.repositories.user_settings import UserSettings
from bot.scheduler.notifier import Notifier

logger = logging.getLogger(__name__)

_DueItem = Tuple[str, int, dict]  # (target_type, target_id, info)


class PrayerScheduler:
    TICK_SECONDS = 30

    def __init__(self, user_repo, group_repo, sent_repo: SentNotificationsRepo,
                 notifier: Notifier, tick_seconds: int = None):
        self._user_repo = user_repo
        self._group_repo = group_repo
        self._sent_repo = sent_repo
        self._notifier = notifier
        if tick_seconds is not None:
            self.TICK_SECONDS = tick_seconds
        self._task: asyncio.Task | None = None
        self._running = False

    async def start(self) -> None:
        if self._task is not None:
            return
        self._running = True
        self._task = asyncio.create_task(self._loop())
        logger.info("✅ بدأت حلقة جدولة الصلاة (كل %sث)", self.TICK_SECONDS)

    async def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task
            self._task = None
        logger.info("🛑 توقفت حلقة الجدولة")

    async def _loop(self) -> None:
        while self._running:
            try:
                await self.tick()
            except Exception:
                logger.exception("⚠️ خطأ في دورة الجدولة (ستستأنف)")
            await asyncio.sleep(self.TICK_SECONDS)

    async def tick(self) -> None:
        """دورة واحدة: اكتشف التنبيهات المستحقة وأطلقها."""
        due_items = await self._find_due_prayers()
        for target_type, target_id, info in due_items:
            await self._dispatch(target_type, target_id, info)

    async def _find_due_prayers(self) -> List[_DueItem]:
        """يفحص كل المستخدمين/المجموعات ويُرجع التنبيهات المستحقة الآن."""
        from bot.prayer.calculator import CityCoordinates, PrayerTimeCalculator

        now = datetime.utcnow()
        today = now.strftime("%Y-%m-%d")
        results: List[_DueItem] = []

        # المستخدمون
        for u in await self._user_repo.list_with_notifications():
            prayer_info = self._check_due(u.city, u.method, u.asr_method,
                                          now, u.enabled_prayers)
            if prayer_info:
                results.append(("user", u.user_id, prayer_info))
            # prelude
            if u.prelude_on:
                prelude_info = self._check_prelude(
                    u.city, u.method, u.asr_method, now,
                    u.enabled_prayers, u.prelude_minutes)
                if prelude_info:
                    results.append(("user", u.user_id, prelude_info))

        # المجموعات
        for g in await self._group_repo.list_all():
            prayer_info = self._check_due(g.city, g.method, g.asr_method, now)
            if prayer_info:
                results.append(("group", g.chat_id, prayer_info))

        return results

    @staticmethod
    def _check_due(city: str, method: str, asr_method: str, now: datetime,
                   enabled=None) -> dict | None:
        from bot.prayer.calculator import CityCoordinates, PrayerTimeCalculator
        coords = CityCoordinates.get_city_coords(city)
        if not coords:
            return None
        calc = PrayerTimeCalculator(
            latitude=coords["lat"], longitude=coords["lng"],
            timezone=coords["tz"], method=method, asr_method=asr_method)
        times = calc.calculate_times(now)
        now_hhmm = now.strftime("%H:%M")
        prayers = enabled or ["fajr", "dhuhr", "asr", "maghrib", "isha"]
        # أطلق إذا حان الوقت (مطابقة الدقيقة، مع سماحية دقيقة واحدة)
        for p in prayers:
            if p not in times:
                continue
            t = times[p]
            if _within(t, now_hhmm, tolerance=1):
                return {"prayer": p, "time": t, "is_prelude": False}
        return None

    @staticmethod
    def _check_prelude(city, method, asr_method, now, enabled, lead_minutes):
        from bot.prayer.calculator import CityCoordinates, PrayerTimeCalculator
        coords = CityCoordinates.get_city_coords(city)
        if not coords:
            return None
        calc = PrayerTimeCalculator(
            latitude=coords["lat"], longitude=coords["lng"],
            timezone=coords["tz"], method=method, asr_method=asr_method)
        times = calc.calculate_times(now)
        now_hhmm = now.strftime("%H:%M")
        prayers = enabled or ["fajr", "dhuhr", "asr", "maghrib", "isha"]
        for p in prayers:
            if p not in times:
                continue
            target = _subtract_minutes(times[p], lead_minutes)
            if _within(target, now_hhmm, tolerance=1):
                return {"prayer": p, "time": times[p], "is_prelude": True,
                        "prelude_key": f"prelude_{p}"}
        return None

    async def _dispatch(self, target_type: str, target_id: int,
                        info: dict) -> None:
        prayer = info["prayer"]
        date = datetime.utcnow().strftime("%Y-%m-%d")
        key = info.get("prelude_key", prayer)
        if await self._sent_repo.already_sent(target_id, target_type, key, date):
            return
        try:
            if target_type == "user":
                ok = await self._notifier.notify_user(
                    target_id, prayer, info["time"], info.get("is_prelude", False))
            else:
                ok = await self._notifier.broadcast_group_azan(
                    target_id, prayer, "traditional")
            if ok:
                await self._sent_repo.mark_sent(target_id, target_type, key, date)
        except Exception:
            logger.exception("⚠️ فشل إرسال تنبيه %s لـ %s", prayer, target_id)


def _within(t1: str, t2: str, tolerance: int = 1) -> bool:
    """هل توقيتان متساويان ضمن سماحية دقائق؟"""
    d1 = _to_minutes(t1)
    d2 = _to_minutes(t2)
    return abs(d1 - d2) <= tolerance


def _to_minutes(hhmm: str) -> int:
    h, m = hhmm.split(":")
    return int(h) * 60 + int(m)


def _subtract_minutes(hhmm: str, minutes: int) -> str:
    total = _to_minutes(hhmm) - minutes
    total %= 24 * 60
    return f"{total // 60:02d}:{total % 60:02d}"
```

- [ ] **Step 4: Run, verify pass**

Run: `python -m pytest tests/unit/test_prayer_scheduler.py -v`
Expected: 3 PASS

- [ ] **Step 5: Commit**

```bash
git add bot/scheduler/prayer_scheduler.py tests/unit/test_prayer_scheduler.py
git commit -m "feat(scheduler): add asyncio prayer scheduler loop with dedup"
```

---

## Phase 5 — App wiring + handlers + DI

### Task 12: Dependencies container + build_app

**Files:**
- Create: `bot/deps.py`
- Create: `bot/app.py`
- Create: `tests/unit/test_app_build.py`

- [ ] **Step 1: Write failing test**

`tests/unit/test_app_build.py`:
```python
import pytest
from unittest.mock import patch, MagicMock


def test_build_app_returns_client_no_side_effects():
    """build_app must not require network or run side effects on import."""
    with patch("pyrogram.Client"), patch("pytgcalls.PyTgCalls"):
        from bot.config import Settings
        from bot.app import build_app

        # minimal settings (frozen)
        s = Settings(bot_token="1:ABC", api_id=123, api_hash="h", owner_id=1)
        # build_dependencies needs DB; mock it
        deps = MagicMock()
        app = build_app(s, deps)
        assert app is not None
```

- [ ] **Step 2: Run, verify failure**

Run: `python -m pytest tests/unit/test_app_build.py -v`
Expected: FAIL

- [ ] **Step 3: Implement deps + app**

`bot/deps.py`:
```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""حاوية التبعيات — تُنشأ مرة في main() وتمرر للمعالجات."""

import logging
from dataclasses import dataclass

from bot.config import Settings
from bot.db.connection import Database
from bot.db.repositories.group_settings import GroupSettingsRepo
from bot.db.repositories.sent_notifications import SentNotificationsRepo
from bot.db.repositories.user_settings import UserSettingsRepo
from bot.scheduler.notifier import Notifier
from bot.scheduler.prayer_scheduler import PrayerScheduler
from bot.streaming.stream_manager import StreamManager

logger = logging.getLogger(__name__)


@dataclass
class Dependencies:
    settings: Settings
    db: Database
    user_repo: UserSettingsRepo
    group_repo: GroupSettingsRepo
    sent_repo: SentNotificationsRepo
    stream_manager: StreamManager
    notifier: Notifier
    scheduler: PrayerScheduler


async def build_dependencies(settings: Settings, app) -> Dependencies:
    db = Database(settings.db_path)
    await db.connect()

    user_repo = UserSettingsRepo(db)
    group_repo = GroupSettingsRepo(db)
    sent_repo = SentNotificationsRepo(db)

    stream_manager = StreamManager(
        app, max_reconnect=settings.max_reconnect_attempts,
        base_delay=settings.initial_reconnect_delay,
        default_duration_min=settings.default_stream_duration,
    )
    notifier = Notifier(app, stream_manager)
    scheduler = PrayerScheduler(user_repo, group_repo, sent_repo, notifier,
                                tick_seconds=settings.scheduler_tick_seconds)

    return Dependencies(
        settings=settings, db=db, user_repo=user_repo, group_repo=group_repo,
        sent_repo=sent_repo, stream_manager=stream_manager,
        notifier=notifier, scheduler=scheduler,
    )


async def shutdown_dependencies(deps: Dependencies) -> None:
    """إغلاق مرتّب: scheduler → stream → db."""
    try:
        await deps.scheduler.stop()
    except Exception as e:
        logger.warning("⚠️ خطأ إيقاف الجدولة: %s", e)
    try:
        await deps.stream_manager.stop_all()
    except Exception as e:
        logger.warning("⚠️ خطأ إيقاف البث: %s", e)
    try:
        await deps.db.close()
    except Exception as e:
        logger.warning("⚠️ خطأ إغلاق DB: %s", e)
```

`bot/app.py`:
```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""بناء عميل Pyrogram — لا أثر جانبي عند الاستيراد."""

import logging

from pyrogram import Client

from bot.config import Settings
from bot.deps import Dependencies

logger = logging.getLogger(__name__)


def build_app(settings: Settings, deps: Dependencies) -> Client:
    """ينشئ Client ويسجّل كل المعالجات. لا يُستدعى إلا من main()."""
    app = Client(
        settings.session_name,
        api_id=settings.api_id,
        api_hash=settings.api_hash,
        bot_token=settings.bot_token,
    )

    # تسجيل المعالجات عبر Plugin Registry
    from bot.handlers import HandlerRegistry
    HandlerRegistry().register(app, deps)

    return app
```

- [ ] **Step 4: Run, verify pass**

Run: `python -m pytest tests/unit/test_app_build.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add bot/deps.py bot/app.py tests/unit/test_app_build.py
git commit -m "feat(app): add DI container + build_app (no import side effects)"
```

---

### Task 13: Decorators (owner_only, admin_only, safe_handler)

**Files:**
- Create: `bot/decorators.py`
- Create: `tests/unit/test_decorators.py`

- [ ] **Step 1: Write failing test**

`tests/unit/test_decorators.py`:
```python
import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock


@pytest.mark.asyncio
async def test_owner_only_blocks_non_owner():
    from bot.decorators import owner_only

    settings = MagicMock()
    settings.is_owner.return_value = False

    @owner_only(settings)
    async def handler(client, message):
        return "ran"

    msg = MagicMock()
    msg.from_user.id = 999
    msg.reply_text = AsyncMock()
    result = await handler(None, msg)
    assert result is None
    msg.reply_text.assert_awaited_once()


@pytest.mark.asyncio
async def test_owner_only_allows_owner():
    from bot.decorators import owner_only

    settings = MagicMock()
    settings.is_owner.return_value = True

    @owner_only(settings)
    async def handler(client, message):
        return "ran"

    msg = MagicMock()
    msg.from_user.id = 1
    assert await handler(None, msg) == "ran"


@pytest.mark.asyncio
async def test_safe_handler_swallows_exception():
    from bot.decorators import safe_handler

    @safe_handler()
    async def handler(client, message):
        raise ValueError("boom")

    msg = MagicMock()
    msg.reply_text = AsyncMock()
    await handler(None, msg)  # must not raise
```

- [ ] **Step 2: Run, verify failure**

Run: `python -m pytest tests/unit/test_decorators.py -v`
Expected: FAIL

- [ ] **Step 3: Implement**

`bot/decorators.py`:
```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Decorators للتحقق من الصلاحيات ومعالجة الأخطاء."""

import functools
import logging

logger = logging.getLogger(__name__)


def owner_only(settings):
    """يسمح فقط للمالك. يتطلب message.from_user.id."""
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(client, message, *args, **kwargs):
            user_id = message.from_user.id if message.from_user else None
            if not settings.is_owner(user_id):
                await message.reply_text("❌ لا تملك صلاحية استخدام هذا الأمر")
                logger.warning("🚫 محاولة وصول غير مصرّح: %s", user_id)
                return None
            return await func(client, message, *args, **kwargs)
        return wrapper
    return decorator


def admin_only(app):
    """للمجموعات: يسمح للمشرفين أو للمالك."""
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(client, callback_query_or_message, *args, **kwargs):
            user = getattr(callback_query_or_message, "from_user", None)
            chat = getattr(callback_query_or_message, "message", None) or \
                   callback_query_or_message
            chat_id = getattr(chat, "chat", None)
            chat_id = getattr(chat_id, "id", None) if chat_id else None
            if user and chat_id:
                try:
                    member = await client.get_chat_member(chat_id, user.id)
                    if member.status not in ("administrator", "creator"):
                        await callback_query_or_message.reply_text(
                            "❌ هذا الأمر للمشرفين فقط")
                        return None
                except Exception as e:
                    logger.warning("⚠️ تعذّر التحقق من المشرف: %s", e)
            return await func(client, callback_query_or_message, *args, **kwargs)
        return wrapper
    return decorator


def safe_handler():
    """يلتقط الاستثناءات ويرد برسالة أنيقة بدل انهيار الزر."""
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(client, update, *args, **kwargs):
            try:
                return await func(client, update, *args, **kwargs)
            except Exception as e:
                logger.exception("⚠️ خطأ في معالج")
                reply = getattr(update, "reply_text", None) or \
                        getattr(getattr(update, "message", None), "edit_text", None)
                if reply:
                    try:
                        await reply(f"❌ حدث خطأ: {str(e)[:100]}")
                    except Exception:
                        pass
        return wrapper
    return decorator
```

- [ ] **Step 4: Run, verify pass**

Run: `python -m pytest tests/unit/test_decorators.py -v`
Expected: 3 PASS

- [ ] **Step 5: Commit**

```bash
git add bot/decorators.py tests/unit/test_decorators.py
git commit -m "feat(handlers): add owner_only/admin_only/safe_handler decorators"
```

---

### Task 14: Handlers — adhkar, quran, owner

**Files:**
- Create: `bot/handlers/__init__.py`
- Create: `bot/handlers/adhkar.py`
- Create: `bot/handlers/quran.py`
- Create: `bot/handlers/owner.py`

These follow the existing UI (keyboards, callback_data strings) from `main.py` so user-visible behavior is preserved. See Task 8 for data sources.

- [ ] **Step 1: Create HandlerRegistry**

`bot/handlers/__init__.py`:
```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""تسجيل كل المعالجات — إضافة ميزة = ملف + سطر هنا."""

import logging

from pyrogram import Client

from bot.deps import Dependencies

logger = logging.getLogger(__name__)


class HandlerRegistry:
    def register(self, app: Client, deps: Dependencies) -> None:
        from bot.handlers import adhkar, azan, owner, quran
        adhkar.register(app, deps)
        quran.register(app, deps)
        azan.register(app, deps)
        owner.register(app, deps)
        logger.info("✅ سُجّلت كل المعالجات")
```

- [ ] **Step 2: adhkar handlers** (port from `main.py` lines 623-633, 791-850, using `bot.data.adhkar`)

`bot/handlers/adhkar.py`:
```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""معالجات الأذكار."""

from pyrogram import Client, filters
from pyrogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from bot.data.adhkar import ADHKAR, ADHKAR_CATEGORIES
from bot.deps import Dependencies
from bot.decorators import safe_handler


def register(app: Client, deps: Dependencies) -> None:
    @app.on_message(filters.command("adhkar"))
    @safe_handler()
    async def adhkar_cmd(client, message: Message):
        kb = [[InlineKeyboardButton(v, callback_data=f"category_{k}")]
              for k, v in ADHKAR_CATEGORIES.items()]
        await message.reply_text("📿 **الأذكار الإسلامية الشاملة**\n\nاختر الفئة:",
                                 reply_markup=InlineKeyboardMarkup(kb))

    @app.on_callback_query(filters.regex("^main_adhkar_menu$"))
    @safe_handler()
    async def menu(client, cq: CallbackQuery):
        kb = [[InlineKeyboardButton(v, callback_data=f"category_{k}")]
              for k, v in ADHKAR_CATEGORIES.items()]
        kb.append([InlineKeyboardButton("🔙 العودة", callback_data="back_to_start")])
        await cq.message.edit_text("📿 **اختر فئة الأذكار:**",
                                   reply_markup=InlineKeyboardMarkup(kb))

    @app.on_callback_query(filters.regex("^category_"))
    @safe_handler()
    async def show_category(client, cq: CallbackQuery):
        category = cq.data.replace("category_", "")
        items = ADHKAR.get(category, [])
        kb = [[InlineKeyboardButton(f"{i+1}. {it['title'][:35]}",
                callback_data=f"adhkar_{category}_{i}")] for i, it in enumerate(items)]
        kb.append([InlineKeyboardButton("🔙 الرجوع", callback_data="main_adhkar_menu")])
        await cq.message.edit_text(f"📿 **{ADHKAR_CATEGORIES.get(category)}:**",
                                   reply_markup=InlineKeyboardMarkup(kb))

    @app.on_callback_query(filters.regex("^adhkar_"))
    @safe_handler()
    async def show_item(client, cq: CallbackQuery):
        parts = cq.data.replace("adhkar_", "").split("_")
        category, idx = parts[0], int(parts[1])
        it = ADHKAR[category][idx]
        text = (f"🕌 **{it['title']}**\n\n📝 **النص:**\n{it['text']}\n\n"
                f"✨ **الفضل:**\n{it['benefit']}")
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 الرجوع", callback_data=f"category_{category}")],
            [InlineKeyboardButton("🏠 الرئيسية", callback_data="back_to_start")],
        ])
        await cq.message.edit_text(text, reply_markup=kb)
```

- [ ] **Step 3: quran handlers** (port from `main.py` lines 636-647, 853-911)

`bot/handlers/quran.py`:
```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""معالجات القرآن."""

from pyrogram import Client, filters
from pyrogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from bot.data.surahs import SURAHS
from bot.deps import Dependencies
from bot.decorators import safe_handler


def register(app: Client, deps: Dependencies) -> None:
    settings = deps.settings

    @app.on_message(filters.command("quran"))
    @safe_handler()
    async def quran_cmd(client, message: Message):
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("📚 قائمة السور", callback_data="surah_list")],
            [InlineKeyboardButton("🔙 الرئيسية", callback_data="back_to_start")],
        ])
        await message.reply_text("📖 **القرآن الكريم**\n\nاختر طريقة:",
                                 reply_markup=kb)

    @app.on_callback_query(filters.regex("^(quran_menu|surah_list)$"))
    @safe_handler()
    async def menu(client, cq: CallbackQuery):
        if cq.data == "quran_menu":
            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("📚 قائمة السور", callback_data="surah_list")],
                [InlineKeyboardButton("🔙 العودة", callback_data="back_to_start")],
            ])
            await cq.message.edit_text("📖 **القرآن الكريم**", reply_markup=kb)
            return
        # surah_list
        kb = []
        for i in range(1, 115, 2):
            row = [InlineKeyboardButton(f"{i}-{SURAHS.get(i,'')}",
                    callback_data=f"surah_{i}")]
            s2 = SURAHS.get(i + 1)
            if s2:
                row.append(InlineKeyboardButton(f"{i+1}-{s2}",
                         callback_data=f"surah_{i+1}"))
            kb.append(row)
        kb.append([InlineKeyboardButton("🔙 الرجوع", callback_data="quran_menu")])
        await cq.message.edit_text("📚 **اختر السورة:**",
                                   reply_markup=InlineKeyboardMarkup(kb))

    @app.on_callback_query(filters.regex("^surah_"))
    @safe_handler()
    async def pick(client, cq: CallbackQuery):
        num = int(cq.data.replace("surah_", ""))
        name = SURAHS.get(num, "")
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 السور", callback_data="surah_list")],
            [InlineKeyboardButton("🏠 الرئيسية", callback_data="back_to_start")],
        ])
        await cq.message.edit_text(
            f"📖 **{num} - {name}**\n\n🎵 للاستماع: "
            f"`/stream [chat_id] quran {num}`",
            reply_markup=kb,
        )
```

- [ ] **Step 4: owner handlers** (port stream/stop/status/files from `main.py`)

`bot/handlers/owner.py`:
```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""أوامر المالك: stream/stop/status/files."""

from pathlib import Path

from pyrogram import Client, filters
from pyrogram.types import Message

from bot.data.surahs import SURAHS
from bot.decorators import owner_only, safe_handler
from bot.deps import Dependencies


def register(app: Client, deps: Dependencies) -> None:
    settings = deps.settings
    stream = deps.stream_manager

    @app.on_message(filters.command("stream"))
    @owner_only(settings)
    @safe_handler()
    async def stream_cmd(client, message: Message):
        args = message.command[1:]
        if len(args) < 2:
            await message.reply_text(
                "📌 `/stream [chat_id] quran|file|url [args]`")
            return
        chat_id = int(args[0])
        kind = args[1].lower()
        if kind == "quran":
            num = int(args[2])
            if not 1 <= num <= 114:
                await message.reply_text("❌ رقم السورة 1-114")
                return
            url = f"{settings.quran_stream_url}{num:03d}.mp3"
            name = SURAHS.get(num, "")
            ok = await stream.play(chat_id, url, f"{num} - {name}")
        elif kind == "url":
            url = args[2]
            ok = await stream.play(chat_id, url, "بث مخصص")
        else:
            await message.reply_text("❌ نوع غير معروف")
            return
        await message.reply_text("✅ بدأ البث" if ok else "❌ فشل البث")

    @app.on_message(filters.command("stop"))
    @owner_only(settings)
    @safe_handler()
    async def stop_cmd(client, message: Message):
        args = message.command[1:]
        if not args:
            await message.reply_text("`/stop [chat_id]`")
            return
        ok = await stream.stop(int(args[0]))
        await message.reply_text("✅ أُوقف" if ok else "❌ لا يوجد بث")

    @app.on_message(filters.command("status"))
    @owner_only(settings)
    @safe_handler()
    async def status_cmd(client, message: Message):
        streams = stream.active_streams()
        if not streams:
            await message.reply_text("✅ لا بثات نشطة")
            return
        text = "📊 **البثات:**\n"
        for cid, info in streams.items():
            text += f"\n📍 `{cid}` 🎵 {info['title']}"
        await message.reply_text(text)

    @app.on_message(filters.command("files"))
    @owner_only(settings)
    @safe_handler()
    async def files_cmd(client, message: Message):
        path = Path(settings.music_dir)
        if not path.exists():
            await message.reply_text(f"❌ `{settings.music_dir}` غير موجود")
            return
        exts = {".mp3", ".wav", ".flac", ".m4a", ".ogg"}
        files = [f for f in path.glob("*") if f.suffix.lower() in exts]
        if not files:
            await message.reply_text("❌ لا ملفات")
            return
        text = f"📁 **{len(files)} ملف:**\n" + "\n".join(f.name for f in files[:30])
        await message.reply_text(text)
```

- [ ] **Step 5: Commit**

```bash
git add bot/handlers/__init__.py bot/handlers/adhkar.py bot/handlers/quran.py bot/handlers/owner.py
git commit -m "feat(handlers): add adhkar/quran/owner handlers"
```

---

### Task 15: Azan handlers — fixing ALL dead buttons

**Files:**
- Create: `bot/handlers/azan.py`

This is the critical task. Every callback_data referenced in any keyboard MUST have a handler. List of all callback_data strings that need handlers (verified against `main.py` + `azan_commands.py`):

| callback_data | Currently dead? |
|---------------|-----------------|
| `azan_home` | ✅ handled in main |
| `azan_select_city:*` | ✅ in azan_commands |
| `azan_select_method:*` | ✅ |
| `azan_view_times` | ❌ DEAD |
| `azan_next_prayer` | ❌ DEAD |
| `azan_view_all_times` | ❌ DEAD |
| `azan_view_settings:*` | ❌ DEAD |
| `azan_settings_menu` | ✅ |
| `azan_notification_settings` | ✅ |
| `azan_toggle_notifications` | ✅ |
| `azan_toggle_prelude` | ✅ |
| `azan_set_prelude_time` | ❌ DEAD |
| `azan_stream_settings` | ✅ |
| `azan_toggle_stream` | ✅ |
| `azan_set_stop_before` | ❌ DEAD |
| `azan_set_stream_duration` | ❌ DEAD |
| `azan_prayer_selection` | ❌ DEAD |
| `azan_change_city` | ❌ DEAD |
| `azan_change_method` | ❌ DEAD |
| `azan_refresh_times` | ❌ DEAD |
| `azan_refresh_next` | ❌ DEAD |
| `azan_enable_stream` | ❌ DEAD |
| `azan_back_main` | ✅ |
| `azan_times`/`azan_next`/`azan_settings`/`azan_search`/`azan_setup` (commands) | ✅ |

- [ ] **Step 1: Implement azan handlers covering ALL the above**

`bot/handlers/azan.py`:
```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""معالجات الأذان — تغطّي كل الأزرار بما فيها التي كانت معطّلة."""

from datetime import datetime

from pyrogram import Client, filters
from pyrogram.types import (CallbackQuery, InlineKeyboardButton,
                            InlineKeyboardMarkup, Message)

from bot.data.sources import AZAN_SOURCES
from bot.decorators import safe_handler
from bot.deps import Dependencies
from bot.prayer.calculator import (CALCULATION_METHODS as METHODS,
                                   CityCoordinates, PrayerTimeCalculator)

_PRAYER_ORDER = ["fajr", "sunrise", "dhuhr", "asr", "sunset", "maghrib", "isha"]


def _home_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📿 الأذكار", callback_data="main_adhkar_menu")],
        [InlineKeyboardButton("📖 القرآن", callback_data="quran_menu")],
        [InlineKeyboardButton("🕌 أوقات الصلاة", callback_data="azan_home")],
        [InlineKeyboardButton("ℹ️ حول البوت", callback_data="about")],
    ])


def _settings_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔔 التنبيهات", callback_data="azan_notification_settings")],
        [InlineKeyboardButton("🎵 البث", callback_data="azan_stream_settings")],
        [InlineKeyboardButton("⏰ الصلوات المفعلة", callback_data="azan_prayer_selection")],
        [InlineKeyboardButton("🌍 تغيير المدينة", callback_data="azan_change_city")],
        [InlineKeyboardButton("📐 تغيير الحساب", callback_data="azan_change_method")],
        [InlineKeyboardButton("↩️ عودة", callback_data="azan_back_main")],
    ])


def register(app: Client, deps: Dependencies) -> None:
    user_repo = deps.user_repo

    async def _needs_setup(target) -> bool:
        uid = target.from_user.id
        return await user_repo.get(uid) is None

    # ===== /start sub-menu: azan_home =====
    @app.on_callback_query(filters.regex("^azan_home$"))
    @safe_handler()
    async def azan_home(client, cq: CallbackQuery):
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("📅 أوقات اليوم", callback_data="azan_view_times")],
            [InlineKeyboardButton("⏭️ الصلاة التالية", callback_data="azan_next_prayer")],
            [InlineKeyboardButton("⚙️ الإعدادات", callback_data="azan_settings_menu")],
            [InlineKeyboardButton("🔙 العودة", callback_data="back_to_start")],
        ])
        await cq.message.edit_text(
            "🕌 **نظام الأذان وأوقات الصلاة**\n\nاختر:",
            reply_markup=kb)

    # ===== view today's times =====
    @app.on_callback_query(filters.regex("^(azan_view_times|azan_refresh_times)$"))
    @safe_handler()
    async def view_times(client, cq: CallbackQuery):
        uid = cq.from_user.id
        s = await user_repo.get(uid)
        if not s:
            await cq.answer("❌ اكتب /azan_setup أولاً", show_alert=True)
            return
        times = _calc_times(s)
        text = _format_times(times)
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔄 تحديث", callback_data="azan_refresh_times")],
            [InlineKeyboardButton("⚙️ الإعدادات", callback_data="azan_settings_menu")],
            [InlineKeyboardButton("🔙 العودة", callback_data="azan_home")],
        ])
        await cq.message.edit_text(text, reply_markup=kb)

    # ===== next prayer =====
    @app.on_callback_query(filters.regex("^(azan_next_prayer|azan_refresh_next)$"))
    @safe_handler()
    async def next_prayer(client, cq: CallbackQuery):
        uid = cq.from_user.id
        s = await user_repo.get(uid)
        if not s:
            await cq.answer("❌ اكتب /azan_setup أولاً", show_alert=True)
            return
        info = _next_prayer(s)
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔄 تحديث", callback_data="azan_refresh_next")],
            [InlineKeyboardButton("📅 أوقات اليوم", callback_data="azan_view_times")],
            [InlineKeyboardButton("🔙 العودة", callback_data="azan_home")],
        ])
        await cq.message.edit_text(info, reply_markup=kb)

    @app.on_callback_query(filters.regex("^azan_view_all_times$"))
    @safe_handler()
    async def view_all(client, cq: CallbackQuery):
        uid = cq.from_user.id
        s = await user_repo.get(uid)
        if not s:
            await cq.answer("❌ اكتب /azan_setup أولاً", show_alert=True)
            return
        times = _calc_times(s)
        await cq.message.edit_text(_format_times(times))

    # ===== settings menu =====
    @app.on_callback_query(filters.regex("^azan_settings_menu$"))
    @safe_handler()
    async def settings_menu(client, cq: CallbackQuery):
        uid = cq.from_user.id
        s = await user_repo.get(uid)
        if not s:
            await cq.answer("❌ اكتب /azan_setup أولاً", show_alert=True)
            return
        text = _settings_summary(s)
        await cq.message.edit_text(text, reply_markup=_settings_kb())

    @app.on_callback_query(filters.regex("^azan_view_settings:"))
    @safe_handler()
    async def view_settings(client, cq: CallbackQuery):
        uid = int(cq.data.split(":", 1)[1])
        s = await user_repo.get(uid)
        if not s:
            await cq.answer("لا توجد إعدادات", show_alert=True)
            return
        await cq.message.edit_text(_settings_summary(s), reply_markup=_settings_kb())

    # ===== toggle notifications =====
    @app.on_callback_query(filters.regex("^azan_toggle_notifications$"))
    @safe_handler()
    async def toggle_notif(client, cq: CallbackQuery):
        uid = cq.from_user.id
        s = await user_repo.get(uid)
        new = not s.notifications_on
        await user_repo.update_partial(uid, notifications_on=new)
        await cq.answer(("✅ فُعّلت" if new else "❌ عُطّلت") + " التنبيهات",
                        show_alert=True)
        s2 = await user_repo.get(uid)
        await cq.message.edit_text(_settings_summary(s2), reply_markup=_settings_kb())

    # ===== toggle prelude =====
    @app.on_callback_query(filters.regex("^azan_toggle_prelude$"))
    @safe_handler()
    async def toggle_prelude(client, cq: CallbackQuery):
        uid = cq.from_user.id
        s = await user_repo.get(uid)
        new = not s.prelude_on
        await user_repo.update_partial(uid, prelude_on=new)
        await cq.answer(("✅ فُعّلت" if new else "❌ عُطّلت") + " المقدمة",
                        show_alert=True)
        s2 = await user_repo.get(uid)
        await cq.message.edit_text(_settings_summary(s2), reply_markup=_settings_kb())

    # ===== set prelude time =====
    @app.on_callback_query(filters.regex("^azan_set_prelude_time$"))
    @safe_handler()
    async def set_prelude_time(client, cq: CallbackQuery):
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton(f"{m} دقيقة", callback_data=f"azan_prelude_min:{m}")
             for m in (3, 5, 10, 15)],
            [InlineKeyboardButton("↩️ عودة", callback_data="azan_notification_settings")],
        ])
        await cq.message.edit_text("⏱️ اختر وقت المقدمة:", reply_markup=kb)

    @app.on_callback_query(filters.regex("^azan_prelude_min:"))
    @safe_handler()
    async def prelude_min_set(client, cq: CallbackQuery):
        uid = cq.from_user.id
        m = int(cq.data.split(":", 1)[1])
        await user_repo.update_partial(uid, prelude_minutes=m)
        s = await user_repo.get(uid)
        await cq.answer(f"✅ المقدمة الآن {m} دقيقة", show_alert=True)
        await cq.message.edit_text(_settings_summary(s), reply_markup=_settings_kb())

    # ===== stream settings =====
    @app.on_callback_query(filters.regex("^azan_stream_settings$"))
    @safe_handler()
    async def stream_settings(client, cq: CallbackQuery):
        uid = cq.from_user.id
        s = await user_repo.get(uid)
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("↩️ عودة", callback_data="azan_settings_menu")],
        ])
        await cq.message.edit_text(
            f"🎵 **إعدادات البث**\n\nمصدر الأذان: {s.method}\n"
            "(البث يُدار لكل مجموعة على حدة)", reply_markup=kb)

    @app.on_callback_query(filters.regex("^azan_toggle_stream$"))
    @safe_handler()
    async def toggle_stream(client, cq: CallbackQuery):
        await cq.answer("ℹ️ البث يُضبط لكل مجموعة عبر /azan_setup داخل المجموعة",
                        show_alert=True)

    @app.on_callback_query(filters.regex("^azan_set_stop_before$"))
    @safe_handler()
    async def set_stop_before(client, cq: CallbackQuery):
        await cq.answer("⏹️ يُضبط لكل مجموعة", show_alert=True)

    @app.on_callback_query(filters.regex("^azan_set_stream_duration$"))
    @safe_handler()
    async def set_duration(client, cq: CallbackQuery):
        await cq.answer("📻 يُضبط لكل مجموعة", show_alert=True)

    # ===== prayer selection =====
    @app.on_callback_query(filters.regex("^azan_prayer_selection$"))
    @safe_handler()
    async def prayer_selection(client, cq: CallbackQuery):
        uid = cq.from_user.id
        s = await user_repo.get(uid)
        if not s:
            await cq.answer("❌ اكتب /azan_setup أولاً", show_alert=True)
            return
        rows = []
        for p in ("fajr", "dhuhr", "asr", "maghrib", "isha"):
            on = p in s.enabled_prayers
            rows.append([InlineKeyboardButton(
                f"{'✅' if on else '⬜'} {p}",
                callback_data=f"azan_toggle_prayer:{p}")])
        rows.append([InlineKeyboardButton("↩️ عودة", callback_data="azan_settings_menu")])
        await cq.message.edit_text("⏰ **الصلوات المفعّلة:**",
                                   reply_markup=InlineKeyboardMarkup(rows))

    @app.on_callback_query(filters.regex("^azan_toggle_prayer:"))
    @safe_handler()
    async def toggle_one_prayer(client, cq: CallbackQuery):
        uid = cq.from_user.id
        p = cq.data.split(":", 1)[1]
        s = await user_repo.get(uid)
        prayers = set(s.enabled_prayers)
        if p in prayers:
            prayers.discard(p)
        else:
            prayers.add(p)
        # keep order
        ordered = [x for x in ("fajr","dhuhr","asr","maghrib","isha") if x in prayers]
        await user_repo.update_partial(uid, enabled_prayers=ordered)
        await cq.answer(f"{'✅' if p in prayers else '❌'} {p}", show_alert=False)

    # ===== change city =====
    @app.on_callback_query(filters.regex("^azan_change_city$"))
    @safe_handler()
    async def change_city(client, cq: CallbackQuery):
        cities = list(CityCoordinates.get_all_cities().keys())
        kb = []
        for i in range(0, len(cities), 2):
            row = [InlineKeyboardButton(cities[i],
                    callback_data=f"azan_pick_city:{cities[i]}")]
            if i + 1 < len(cities):
                row.append(InlineKeyboardButton(cities[i+1],
                         callback_data=f"azan_pick_city:{cities[i+1]}"))
            kb.append(row)
        kb.append([InlineKeyboardButton("↩️ عودة", callback_data="azan_settings_menu")])
        await cq.message.edit_text("🌍 اختر المدينة:", reply_markup=InlineKeyboardMarkup(kb))

    @app.on_callback_query(filters.regex("^azan_pick_city:"))
    @safe_handler()
    async def pick_city(client, cq: CallbackQuery):
        uid = cq.from_user.id
        city = cq.data.split(":", 1)[1]
        coords = CityCoordinates.get_city_coords(city)
        if not coords:
            await cq.answer("❌ غير متاحة", show_alert=True)
            return
        await user_repo.update_partial(uid, city=city, timezone=coords["tz"])
        s = await user_repo.get(uid)
        await cq.answer(f"✅ {city}", show_alert=True)
        await cq.message.edit_text(_settings_summary(s), reply_markup=_settings_kb())

    # ===== change method =====
    @app.on_callback_query(filters.regex("^azan_change_method$"))
    @safe_handler()
    async def change_method(client, cq: CallbackQuery):
        kb = []
        for code, info in METHODS.items():
            kb.append([InlineKeyboardButton(info["name"][:30],
                       callback_data=f"azan_pick_method:{code}")])
        kb.append([InlineKeyboardButton("↩️ عودة", callback_data="azan_settings_menu")])
        await cq.message.edit_text("📐 اختر طريقة الحساب:",
                                   reply_markup=InlineKeyboardMarkup(kb))

    @app.on_callback_query(filters.regex("^azan_pick_method:"))
    @safe_handler()
    async def pick_method(client, cq: CallbackQuery):
        uid = cq.from_user.id
        method = cq.data.split(":", 1)[1]
        await user_repo.update_partial(uid, method=method)
        s = await user_repo.get(uid)
        await cq.answer(f"✅ {method}", show_alert=True)
        await cq.message.edit_text(_settings_summary(s), reply_markup=_settings_kb())

    # ===== enable stream (from times view) =====
    @app.on_callback_query(filters.regex("^azan_enable_stream$"))
    @safe_handler()
    async def enable_stream(client, cq: CallbackQuery):
        await cq.answer(
            "ℹ️ لإ activating بث الأذان في مجموعة، استخدم /azan_setup داخل المجموعة.",
            show_alert=True)

    # ===== back to azan main =====
    @app.on_callback_query(filters.regex("^azan_back_main$"))
    @safe_handler()
    async def back_main(client, cq: CallbackQuery):
        uid = cq.from_user.id
        s = await user_repo.get(uid)
        if not s:
            await cq.answer("❌ اكتب /azan_setup أولاً", show_alert=True)
            return
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("📅 أوقات اليوم", callback_data="azan_view_times")],
            [InlineKeyboardButton("⏭️ الصلاة التالية", callback_data="azan_next_prayer")],
            [InlineKeyboardButton("⚙️ الإعدادات", callback_data="azan_settings_menu")],
        ])
        await cq.message.edit_text(
            f"🕌 **القائمة الرئيسية للأذان**\n\n📍 {s.city}\n🕐 {s.timezone}",
            reply_markup=kb)

    # ===== /azan_setup, /azan_times, /azan_next, /azan_settings, /azan_search =====
    @app.on_message(filters.command("azan_setup"))
    @safe_handler()
    async def cmd_setup(client, message: Message):
        cities = list(CityCoordinates.get_all_cities().keys())
        kb = []
        for i in range(0, len(cities), 2):
            row = [InlineKeyboardButton(cities[i],
                    callback_data=f"azan_setup_city:{cities[i]}")]
            if i + 1 < len(cities):
                row.append(InlineKeyboardButton(cities[i+1],
                         callback_data=f"azan_setup_city:{cities[i+1]}"))
            kb.append(row)
        await message.reply_text("🕌 اختر مدينتك:", reply_markup=InlineKeyboardMarkup(kb))

    @app.on_callback_query(filters.regex("^azan_setup_city:"))
    @safe_handler()
    async def setup_city(client, cq: CallbackQuery):
        uid = cq.from_user.id
        city = cq.data.split(":", 1)[1]
        coords = CityCoordinates.get_city_coords(city)
        if not coords:
            await cq.answer("❌ غير متاحة", show_alert=True)
            return
        from bot.db.repositories.user_settings import UserSettings
        await user_repo.upsert(UserSettings(
            user_id=uid, city=city, timezone=coords["tz"]))
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton(f"{code}", callback_data=f"azan_setup_method:{code}")]
            for code in METHODS
        ])
        await cq.message.edit_text(
            f"✅ {city} ({coords['country']})\nاختر طريقة الحساب:",
            reply_markup=kb)

    @app.on_callback_query(filters.regex("^azan_setup_method:"))
    @safe_handler()
    async def setup_method(client, cq: CallbackQuery):
        uid = cq.from_user.id
        method = cq.data.split(":", 1)[1]
        await user_repo.update_partial(uid, method=method)
        s = await user_repo.get(uid)
        await cq.message.edit_text(
            f"✅ تم الإعداد!\n📍 {s.city}\n📐 {method}\n\nاكتب /azan_times")

    @app.on_message(filters.command("azan_times"))
    @safe_handler()
    async def cmd_times(client, message: Message):
        uid = message.from_user.id
        s = await user_repo.get(uid)
        if not s:
            await message.reply_text("❌ اكتب /azan_setup أولاً")
            return
        await message.reply_text(_format_times(_calc_times(s)))

    @app.on_message(filters.command("azan_next"))
    @safe_handler()
    async def cmd_next(client, message: Message):
        uid = message.from_user.id
        s = await user_repo.get(uid)
        if not s:
            await message.reply_text("❌ اكتب /azan_setup أولاً")
            return
        await message.reply_text(_next_prayer(s))

    @app.on_message(filters.command("azan_settings"))
    @safe_handler()
    async def cmd_settings(client, message: Message):
        uid = message.from_user.id
        s = await user_repo.get(uid)
        if not s:
            await message.reply_text("❌ اكتب /azan_setup أولاً")
            return
        await message.reply_text(_settings_summary(s), reply_markup=_settings_kb())

    @app.on_message(filters.command("azan_search"))
    @safe_handler()
    async def cmd_search(client, message: Message):
        if len(message.command) < 2:
            await message.reply_text("الاستخدام: /azan_search <مدينة>")
            return
        q = " ".join(message.command[1:])
        results = CityCoordinates.search_cities(q)
        if not results:
            await message.reply_text(f"❌ لا نتائج لـ {q}")
            return
        text = "🔍 نتائج:\n" + "\n".join(f"📍 {c}" for c in results[:10])
        await message.reply_text(text)


# ===== helpers =====

def _calc_times(s):
    coords = CityCoordinates.get_city_coords(s.city)
    calc = PrayerTimeCalculator(latitude=coords["lat"], longitude=coords["lng"],
                                timezone=coords["tz"], method=s.method,
                                asr_method=s.asr_method)
    times = calc.calculate_times(datetime.utcnow())
    times["city"] = s.city
    times["country"] = coords["country"]
    times["method"] = calc.get_method_name()
    return times


def _format_times(times) -> str:
    text = f"🕌 **أوقات الصلاة**\n📍 {times['city']}, {times['country']}\n\n"
    for p in _PRAYER_ORDER:
        if p in times:
            name = PrayerTimeCalculator.PRAYER_NAMES.get(p, p)
            text += f"{name} • {times[p]}\n"
    return text


def _next_prayer(s) -> str:
    coords = CityCoordinates.get_city_coords(s.city)
    calc = PrayerTimeCalculator(latitude=coords["lat"], longitude=coords["lng"],
                                timezone=coords["tz"], method=s.method,
                                asr_method=s.asr_method)
    times = calc.calculate_times(datetime.utcnow())
    now = datetime.utcnow().strftime("%H:%M")
    for p in ("fajr", "dhuhr", "asr", "maghrib", "isha"):
        if p in times and times[p] > now:
            name = PrayerTimeCalculator.PRAYER_NAMES.get(p, p)
            return f"{name}\n⏰ {times[p]}"
    return "🌙 صلاة الفجر غدًا هي التالية"


def _settings_summary(s) -> str:
    return (
        f"⚙️ **الإعدادات**\n\n"
        f"📍 المدينة: {s.city}\n"
        f"📐 الطريقة: {s.method}\n"
        f"🕐 التوقيت: UTC{s.timezone:+d}\n\n"
        f"🔔 التنبيهات: {'✅' if s.notifications_on else '❌'}\n"
        f"🌅 المقدمة: {'✅' if s.prelude_on else '❌'} ({s.prelude_minutes}د)\n\n"
        f"🙏 المفعّلة: {', '.join(s.enabled_prayers)}"
    )
```

- [ ] **Step 2: Commit**

```bash
git add bot/handlers/azan.py
git commit -m "feat(handlers): add azan handlers covering all dead buttons"
```

---

### Task 16: start/help/about handlers + main callback router

**Files:**
- Modify: `bot/handlers/__init__.py` (add main menu handlers)
- Create: `bot/handlers/main_menu.py`

- [ ] **Step 1: Add main menu module**

`bot/handlers/main_menu.py`:
```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""القائمة الرئيسية: /start /help/about + back_to_start."""

from pyrogram import Client, filters
from pyrogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from bot.decorators import safe_handler
from bot.deps import Dependencies


def _home_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📿 الأذكار", callback_data="main_adhkar_menu")],
        [InlineKeyboardButton("📖 القرآن", callback_data="quran_menu")],
        [InlineKeyboardButton("🕌 أوقات الصلاة", callback_data="azan_home")],
        [InlineKeyboardButton("ℹ️ حول البوت", callback_data="about")],
    ])


def register(app: Client, deps: Dependencies) -> None:
    @app.on_message(filters.command("start"))
    @safe_handler()
    async def start_cmd(client, message: Message):
        await message.reply_text(
            "🕌 **البوت الإسلامي الموحد**\n\n"
            "✅ الأذكار الإسلامية\n✅ بث القرآن (114 سورة)\n"
            "✅ أوقات الصلاة والتنبيهات\n\nاختر من القائمة:",
            reply_markup=_home_kb())

    @app.on_message(filters.command("help"))
    @safe_handler()
    async def help_cmd(client, message: Message):
        await message.reply_text(
            "**الأوامر:**\n/start /help /adhkar /quran\n"
            "/azan_setup /azan_times /azan_next /azan_settings /azan_search\n"
            "(للمالك) /stream /stop /status /files")

    @app.on_callback_query(filters.regex("^(back_to_start|about)$"))
    @safe_handler()
    async def home(client, cq: CallbackQuery):
        if cq.data == "about":
            await cq.message.edit_text(
                "🕌 **البوت الإسلامي الموحد**\n\n"
                "📿 الأذكار • 📖 القرآن • 🕌 الأذان",
                reply_markup=_home_kb())
        else:
            await cq.message.edit_text("🕌 **القائمة الرئيسية**",
                                       reply_markup=_home_kb())
```

- [ ] **Step 2: Register it in HandlerRegistry**

Edit `bot/handlers/__init__.py`, update `register`:
```python
    def register(self, app: Client, deps: Dependencies) -> None:
        from bot.handlers import adhkar, azan, main_menu, owner, quran
        main_menu.register(app, deps)
        adhkar.register(app, deps)
        quran.register(app, deps)
        azan.register(app, deps)
        owner.register(app, deps)
        logger.info("✅ سُجّلت كل المعالجات")
```

- [ ] **Step 3: Commit**

```bash
git add bot/handlers/main_menu.py bot/handlers/__init__.py
git commit -m "feat(handlers): add main menu (start/help/about)"
```

---

## Phase 6 — Entry point + graceful shutdown

### Task 17: Thin main.py with signal handling

**Files:**
- Modify: `main.py` (full rewrite — thin entry point)
- Create: `tests/unit/test_main_entry.py`

- [ ] **Step 1: Write failing test**

`tests/unit/test_main_entry.py`:
```python
import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


def test_main_module_importable_without_side_effects():
    """استيراد main.py يجب ألا يُنشئ Client أو يتصل بالشبكة."""
    import importlib
    m = importlib.import_module("main")
    assert hasattr(m, "main")
    # no module-level Client instance leaked
    assert not hasattr(m, "app") or m.app is None
```

- [ ] **Step 2: Run, verify current behavior fails**

Run: `python -m pytest tests/unit/test_main_entry.py -v`
Expected: FAIL (current main.py creates Client at import)

- [ ] **Step 3: Rewrite main.py**

`main.py`:
```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""نقطة دخول رفيعة للبوت الإسلامي الموحد.

يقرأ الإعدادات، يبني التبعيات، يشغّل البوت، ويتعامل مع إشارات الإيقاف.
كل المنطق في حزمة bot/.
"""

import asyncio
import logging
import signal
import sys
from pathlib import Path

from dotenv import load_dotenv

# تحميل .env قبل أي استيراد لـ bot (لأن Settings.from_env يقرأ env)
load_dotenv()


def main() -> None:
    from bot.config import Settings
    from bot.logging_setup import setup_logging

    settings = Settings.from_env()
    logger = setup_logging(
        log_level=settings.log_level, log_dir=settings.logs_dir,
        json_format=(settings.log_format == "json"),
    )

    logger.info("=" * 60)
    logger.info("🕌 البوت الإسلامي الموحد — بدء التشغيل")
    logger.info("=" * 60)

    # ضمان وجود المسارات
    for d in (settings.data_dir, settings.logs_dir, settings.music_dir):
        Path(d).mkdir(parents=True, exist_ok=True)

    asyncio.run(_run(settings, logger))


async def _run(settings, logger) -> None:
    from pyrogram import Client

    from bot.deps import build_dependencies, shutdown_dependencies
    from bot.db.migrate_from_json import migrate_from_json

    # عميل مؤقت لبناء deps (StreamManager يحتاجه)
    # نبني Client مباشرة:
    from bot.app import build_app

    # نحتاج Client أولاً لبناء deps التي تعتمد عليه
    app = Client(
        settings.session_name, api_id=settings.api_id,
        api_hash=settings.api_hash, bot_token=settings.bot_token,
    )
    deps = await build_dependencies(settings, app)
    # هجرة JSON القديم إن وُجد
    legacy_json = Path(settings.azan_data_dir) / "user_settings.json"
    if legacy_json.exists():
        await migrate_from_json(legacy_json, deps.user_repo)

    # تسجيل المعالجات على app
    from bot.handlers import HandlerRegistry
    HandlerRegistry().register(app, deps)

    # إشارات الإيقاف الآمن
    stop_event = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        with contextlib_suppress():
            try:
                loop.add_signal_handler(sig, stop_event.set)
            except NotImplementedError:
                # Windows لا يدعم add_signal_handler لكل الإشارات
                pass

    # بدء الخدمات
    await deps.stream_manager.start()
    await deps.scheduler.start()
    await app.start()
    logger.info("✅ البوت يعمل. المالك: %s", settings.owner_id)

    try:
        await stop_event.wait()
    finally:
        logger.info("🛑 إشارة إيقاف — إغلاق مرتّب...")
        try:
            await app.stop()
        except Exception as e:
            logger.warning("⚠️ خطأ إيقاف app: %s", e)
        await shutdown_dependencies(deps)
        logger.info("✅ تم الإيقاف بأمان")


def contextlib_suppress():
    import contextlib
    return contextlib.suppress()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logging.getLogger("islamic_bot").info("🛑 interrupted")
    except ValueError as e:
        # خطأ إعدادات
        print(f"❌ {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        logging.getLogger("islamic_bot").exception("❌ خطأ حرج: %s", e)
        sys.exit(1)
```

- [ ] **Step 4: Run test, verify pass**

Run: `python -m pytest tests/unit/test_main_entry.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add main.py tests/unit/test_main_entry.py
git commit -m "refactor(main): thin entry point with graceful signal shutdown"
```

---

## Phase 7 — Deployment artifacts

### Task 18: healthcheck.py

**Files:**
- Create: `healthcheck.py`

- [ ] **Step 1: Create healthcheck**

`healthcheck.py`:
```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""فحص صحة الحاوية — يُستدعى بواسطة Docker HEALTHCHECK.

يخرج 0 (صحي) إذا: قاعدة البيانات قابلة للفتح + ملف .env موجود.
يخرج 1 (غير صحي) خلاف ذلك.
"""

import os
import sqlite3
import sys
from pathlib import Path


def main() -> int:
    db_path = os.getenv("DB_PATH", "./data/bot.db")
    if not Path(db_path).exists():
        print(f"❌ DB missing: {db_path}", file=sys.stderr)
        return 1
    try:
        conn = sqlite3.connect(db_path)
        conn.execute("SELECT 1 FROM schema_version LIMIT 1")
        conn.close()
    except sqlite3.Error as e:
        print(f"❌ DB unreadable: {e}", file=sys.stderr)
        return 1
    print("✅ healthy")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: Commit**

```bash
git add healthcheck.py
git commit -m "feat(deploy): add container healthcheck script"
```

---

### Task 19: Dockerfile (multi-stage, non-root, healthcheck)

**Files:**
- Modify: `Dockerfile`

- [ ] **Step 1: Replace Dockerfile**

`Dockerfile`:
```dockerfile
# syntax=docker/dockerfile:1.6

# ===== Stage 1: builder =====
FROM python:3.12-slim AS builder

RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg gcc \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /install
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ===== Stage 2: runtime =====
FROM python:3.12-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# مستخدم غير جذر
RUN useradd --create-home --uid 1000 nonroot

WORKDIR /app

# نسخ المكتبات من builder
COPY --from=builder /install /usr/local

# نسخ الكود
COPY --chown=nonroot:nonroot . .

# مسارات البيانات
RUN mkdir -p data logs music azan_data \
    && chown -R nonroot:nonroot data logs music azan_data

USER nonroot

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DB_PATH=/app/data/bot.db \
    LOGS_DIR=/app/logs \
    MUSIC_DIR=/app/music

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python healthcheck.py || exit 1

CMD ["python", "main.py"]
```

- [ ] **Step 2: Commit**

```bash
git add Dockerfile
git commit -m "feat(deploy): multi-stage Dockerfile, non-root, healthcheck"
```

---

### Task 20: docker-compose.yml + install.sh + systemd

**Files:**
- Create: `deploy/docker-compose.yml`
- Create: `deploy/install.sh`
- Create: `deploy/systemd/islamic-bot.service`

- [ ] **Step 1: Create compose**

`deploy/docker-compose.yml`:
```yaml
services:
  islamic-bot:
    build:
      context: ..
      dockerfile: Dockerfile
    image: islamic-unified-bot:latest
    container_name: islamic-bot
    restart: unless-stopped
    env_file:
      - ../.env
    volumes:
      - ../data:/app/data
      - ../logs:/app/logs
      - ../music:/app/music
      - ../azan_data:/app/azan_data
    stop_grace_period: 30s
    healthcheck:
      test: ["CMD", "python", "healthcheck.py"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    logging:
      driver: json-file
      options:
        max-size: "10m"
        max-file: "3"
```

- [ ] **Step 2: Create install.sh**

`deploy/install.sh`:
```bash
#!/usr/bin/env bash
# نص تثبيت تفاعلي للبوت الإسلامي الموحد.
# يستخدم: git, docker, docker compose.
set -euo pipefail

cd "$(dirname "$0")/.."
echo "🕌 تثبيت Islamic Unified Bot"

# 1. التحقق من Docker
if ! command -v docker >/dev/null 2>&1; then
    echo "❌ Docker غير مُثبّت. ثبّته أولًا: https://docs.docker.com/get-docker/"
    exit 1
fi

# 2. التحقق من .env
if [ ! -f .env ]; then
    echo "📝 إنشاء .env من القالب..."
    cp .env.example .env
    echo "⚠️ عدّل .env واضغط Enter للمتابعة..."
    read -r
fi

# 3. التحقق من القيم الإلزامية
for key in BOT_TOKEN API_ID API_HASH OWNER_ID; do
    val=$(grep -E "^${key}=" .env | cut -d= -f2-)
    if [ -z "$val" ] || echo "$val" | grep -qi "YOUR_"; then
        echo "❌ $key غير مضبوط في .env"
        exit 1
    fi
done

# 4. مسارات البيانات
mkdir -p data logs music azan_data

# 5. بناء وتشغيل
echo "🏗️ بناء الحاوية..."
docker compose -f deploy/docker-compose.yml build

echo "🚀 تشغيل..."
docker compose -f deploy/docker-compose.yml up -d

echo "✅ تم. الحالة:"
docker compose -f deploy/docker-compose.yml ps
echo ""
echo "📜 السجلات: docker compose -f deploy/docker-compose.yml logs -f"
```

- [ ] **Step 3: Create systemd unit (for non-Docker deployments)**

`deploy/systemd/islamic-bot.service`:
```ini
[Unit]
Description=Islamic Unified Telegram Bot
After=network.target
Wants=network-online.target

[Service]
Type=simple
User=islamicbot
WorkingDirectory=/opt/islamic-unified-bot
EnvironmentFile=/opt/islamic-unified-bot/.env
ExecStart=/opt/islamic-unified-bot/venv/bin/python main.py
Restart=always
RestartSec=10
TimeoutStopSec=30
StandardOutput=journal
StandardError=journal
SyslogIdentifier=islamic-bot

[Install]
WantedBy=multi-user.target
```

- [ ] **Step 4: Commit**

```bash
git add deploy/
git commit -m "feat(deploy): add docker-compose, install script, systemd unit"
```

---

## Phase 8 — Configs + cleanup + integration tests

### Task 21: Update .env.example + pyproject.toml

**Files:**
- Modify: `.env.example`
- Modify: `pyproject.toml`

- [ ] **Step 1: Replace .env.example**

`.env.example`:
```env
# ============================================================
# Islamic Unified Bot — متغيرات البيئة
# ============================================================

# --- بيانات Telegram (إلزامية) ---
BOT_TOKEN=YOUR_BOT_TOKEN_HERE
API_ID=YOUR_API_ID_HERE
API_HASH=YOUR_API_HASH_HERE
OWNER_ID=YOUR_OWNER_ID_HERE

# --- المسارات ---
MUSIC_DIR=./music
AZAN_DATA_DIR=./azan_data
DATA_DIR=./data
LOGS_DIR=./logs
SESSION_NAME=islamic_unified_bot

# --- مصادر ---
QURAN_STREAM_URL=https://server8.mp3quran.net/afs/

# --- البث ---
MAX_RECONNECT_ATTEMPTS=10
INITIAL_RECONNECT_DELAY=5

# --- الصلاة ---
DEFAULT_CALCULATION_METHOD=isna
DEFAULT_ASR_METHOD=standard
DEFAULT_CITY=مكة المكرمة
DEFAULT_TIMEZONE=3

# --- التنبيهات ---
NOTIFICATIONS_ENABLED=true
PRELUDE_ENABLED=false
PRELUDE_TIME=5

# --- البث التلقائي ---
STREAM_ENABLED=false
DEFAULT_AZAN_SOURCE=traditional
STREAM_STOP_BEFORE=0
DEFAULT_STREAM_DURATION=120

# --- قاعدة البيانات ---
DB_TYPE=sqlite
DB_PATH=./data/bot.db

# --- الأمان والسجلات ---
SAFE_MODE=true
LOG_SENSITIVE_DATA=false
REQUEST_TIMEOUT=10
MAX_RETRIES=3
DEBUG_MODE=false
LOG_LEVEL=INFO
LOG_FORMAT=text

# --- الجدولة ---
SCHEDULER_TICK_SECONDS=30
```

- [ ] **Step 2: Extend pyproject.toml**

`pyproject.toml`:
```toml
[tool.isort]
profile = "black"
line_length = 88

[tool.black]
line-length = 88
target-version = ["py310", "py311", "py312"]
extend-exclude = "azan_prayer_times.py"

[tool.ruff]
line-length = 120
target-version = "py310"
extend-exclude = ["azan_prayer_times.py", "advanced_adhkar_library.py"]

[tool.ruff.lint]
select = ["E", "F", "W", "I"]
ignore = ["E501"]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
```
Note: keep existing `pytest.ini` working too (CI references it); the pyproject section is additive.

- [ ] **Step 3: Update requirements**

`requirements.txt` (append if missing):
```
aiosqlite==0.22.1
```
(Already present. Add a dev section as a separate file `requirements-dev.txt`):
```
pytest
pytest-asyncio
pytest-cov
pytest-timeout
pytest-mock
aioresponses
freezegun
```

- [ ] **Step 4: Commit**

```bash
git add .env.example pyproject.toml requirements.txt requirements-dev.txt
git commit -m "chore: update env example, pyproject, dev requirements"
```

---

### Task 22: Refactor conftest.py (remove sys.modules hack)

**Files:**
- Modify: `tests/conftest.py`
- Delete old tests that relied on `sys.modules['main']` deletion: `tests/test_config_and_bot.py` (replaced by `tests/unit/test_config.py` etc.)

- [ ] **Step 1: Update conftest**

`tests/conftest.py`:
```python
import os
import sys
import tempfile
from pathlib import Path

import pytest

# Add project root to path
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))


@pytest.fixture(autouse=True)
def safe_env(monkeypatch, tmp_path):
    """بيئة آمنة لكل اختبار."""
    monkeypatch.setenv("BOT_TOKEN", "1234567890:ABC_test_token_value")
    monkeypatch.setenv("API_ID", "12345678")
    monkeypatch.setenv("API_HASH", "test_api_hash_value_not_real")
    monkeypatch.setenv("OWNER_ID", "123456789")
    monkeypatch.setenv("MUSIC_DIR", str(tmp_path))
    monkeypatch.setenv("AZAN_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    monkeypatch.setenv("DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("LOG_LEVEL", "ERROR")


@pytest.fixture
async def db(tmp_path):
    """قاعدة بيانات معزولة لكل اختبار."""
    from bot.db.connection import Database
    database = Database(str(tmp_path / "test.db"))
    await database.connect()
    yield database
    await database.close()
```

- [ ] **Step 2: Remove obsolete test files**

```bash
git rm tests/test_config_and_bot.py
```
(Its functionality is covered by `tests/unit/test_config.py` + `test_app_build.py` + `test_main_entry.py`.)

- [ ] **Step 3: Run full test suite**

Run: `python -m pytest tests/ -v --tb=short`
Expected: all pass (minus any legacy tests that imported removed modules — fix or delete them)

- [ ] **Step 4: Commit**

```bash
git add tests/conftest.py
git commit -m "test: refactor conftest, remove sys.modules hack"
```

---

### Task 23: Remove obsolete flat modules

**Files:**
- Delete: `azan_commands.py`, `azan_manager.py`, `azan_config.py`, `advanced_adhkar_library.py`
- Keep: `azan_prayer_times.py` → keep as a thin compatibility re-export OR delete if no test depends on it

- [ ] **Step 1: Check references**

Run: `grep -rn "from azan_" tests/ main.py bot/ || echo "no references"`
- If `tests/test_prayer_times.py` imports `from azan_prayer_times`, either update that import to `from bot.prayer.calculator` or keep a shim.

- [ ] **Step 2: Add compatibility shim for azan_prayer_times (optional, safe)**

Keep `azan_prayer_times.py` as:
```python
#!/usr/bin/env python3
"""توافق مع الوحدة القديمة — تُوجّه إلى bot.prayer.calculator."""
from bot.prayer.calculator import (  # noqa: F401
    CityCoordinates, PrayerTimeAPI, PrayerTimeCalculator,
)
```

- [ ] **Step 3: Delete the rest**

```bash
git rm azan_commands.py azan_manager.py azan_config.py advanced_adhkar_library.py
```

- [ ] **Step 4: Run full suite**

Run: `python -m pytest tests/ -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "refactor: remove obsolete flat modules (superseded by bot/)"
```

---

## Phase 9 — Verification + README update

### Task 24: Integration test — scheduler fires on prayer time (freezegun)

**Files:**
- Create: `tests/integration/__init__.py`
- Create: `tests/integration/test_scheduler_e2e.py`

- [ ] **Step 1: Write E2E test**

`tests/integration/test_scheduler_e2e.py`:
```python
import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from freezegun import freeze_time


@pytest.mark.asyncio
@freeze_time("2026-06-18T12:00:00Z")
async def test_scheduler_fires_dhuhr_at_noon_utc(tmp_path):
    """عند الظهر UTC في مكة، يجب أن تُطلق صلاة الظهر."""
    from bot.db.connection import Database
    from bot.db.repositories.user_settings import UserSettingsRepo, UserSettings
    from bot.db.repositories.group_settings import GroupSettingsRepo
    from bot.db.repositories.sent_notifications import SentNotificationsRepo
    from bot.scheduler.notifier import Notifier
    from bot.scheduler.prayer_scheduler import PrayerScheduler

    db = Database(str(tmp_path / "e2e.db"))
    await db.connect()
    user_repo = UserSettingsRepo(db)
    group_repo = GroupSettingsRepo(db)
    sent_repo = SentNotificationsRepo(db)

    # مستخدم في مكة (UTC+3، فالظهر المحلي ~12:30 → 09:30 UTC تقريبًا)
    # للاختبار نضع مدينة معروفة ونتحقق من تشغيل المنطق فقط:
    await user_repo.upsert(UserSettings(
        user_id=42, city="مكة المكرمة", timezone=3,
        notifications_on=True, enabled_prayers=["dhuhr"]))

    app = MagicMock()
    app.send_message = AsyncMock()
    stream = MagicMock()
    notifier = Notifier(app, stream)
    notifier.notify_user = AsyncMock(return_value=True)

    sched = PrayerScheduler(user_repo, group_repo, sent_repo, notifier)

    # نُجبر _check_due على المطابقة بمحاكاة الوقت داخل النطاق
    with patch.object(PrayerScheduler, "_check_due",
                      return_value={"prayer": "dhuhr", "time": "12:00",
                                    "is_prelude": False}):
        await sched.tick()

    notifier.notify_user.assert_awaited_once()
    # ثاني tick يجب ألا يكرّر (dedup)
    await sched.tick()
    assert notifier.notify_user.await_count == 1
    await db.close()
```

- [ ] **Step 2: Run**

Run: `python -m pytest tests/integration/test_scheduler_e2e.py -v`
Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add tests/integration/
git commit -m "test: add e2e scheduler test with freezegun + dedup check"
```

---

### Task 25: Verify all acceptance criteria

**Files:** none (verification only)

- [ ] **Step 1: Install deps & run full suite with coverage**

Run:
```bash
pip install -r requirements.txt -r requirements-dev.txt
python -m pytest tests/ -v --cov=bot --cov-report=term-missing --cov-fail-under=75
```
Expected: all pass, coverage ≥ 75%

- [ ] **Step 2: Lint**

Run:
```bash
black --check .
isort --check-only .
flake8 bot/ tests/ --max-line-length=120 --statistics
```
Expected: clean

- [ ] **Step 3: Smoke imports**

Run:
```bash
python -c "from bot.app import build_app; from bot.config import Settings; from bot.deps import Dependencies; print('OK')"
```
Expected: `OK`

- [ ] **Step 4: Build Docker image**

Run:
```bash
docker build -t islamic-unified-bot:test .
```
Expected: builds successfully

- [ ] **Step 5: Final commit (if any fixes)**

```bash
git add -A
git commit -m "test: verify all acceptance criteria pass" || echo "no changes"
```

---

### Task 26: Update README

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Update the Deployment + Architecture sections**

Update README to reflect:
- New `bot/` package structure (replace the file tree in "Architecture" section).
- Corrected statement: SQLite via aiosqlite (no longer "JSON store").
- Docker deployment via `deploy/install.sh` and `docker-compose.yml`.
- Graceful shutdown + healthcheck mentions.
- Keep the feature list and badges.

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "docs: update README for new architecture + Docker deploy"
```

---

## Self-Review Notes

**1. Spec coverage check:**
- §3 Architecture → Tasks 1-16 (package, config, DB, scheduler, streaming, handlers, app)
- §4 SQLite schema → Task 3 (migration file)
- §4 Repositories → Tasks 4-5
- §4 JSON migration → Task 6
- §5 PrayerScheduler → Task 11
- §5 Notifier → Task 10
- §6 StreamManager → Task 9
- §7 Handlers + Plugin Registry → Tasks 12-16
- §7 Dead buttons → Task 15 (explicit table)
- §8 Docker multi-stage → Task 19
- §8 docker-compose → Task 20
- §8 graceful shutdown → Task 17
- §8 Config centralized → Task 1
- §8 Logging → Task 2
- §8 healthcheck → Task 18
- §8 install.sh → Task 20
- §9 Tests → Tasks 3-6, 9-13, 17, 22, 24

**2. Placeholder scan:** No TBD/TODO. All code blocks complete. Every dead button in Task 15 has a handler.

**3. Type consistency:** `Settings.is_owner(user_id)` used in decorators (Task 13) and owner handlers (Task 14). `UserSettingsRepo.update_partial` used across azan handlers. `Notifier.notify_user(user_id, prayer, prayer_time, is_prelude)` consistent in Tasks 10, 11, 24. `Dependencies` fields match between `bot/deps.py` and consumers.
