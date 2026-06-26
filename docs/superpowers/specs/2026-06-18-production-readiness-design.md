# Islamic Unified Bot — Production Readiness Design

**التاريخ:** 2026-06-18
**الحالة:** معتمد (Approved)
**المقاربة:** Strangler Fig Pattern (هجرة تدريجية مع اختبارات تحمي السلوك)

---

## 1. السياق والمشكلة

البوت الحالي (`main.py` + وحدات مسطّحة) يُعلن README أنه "production-grade"، لكن الفحص الفعلي يكشف فجوات حرجة بين الادّعاء والتنفيذ:

### ثغرات وظيفية حرجة
1. **التنبيهات التلقائية لا تعمل** — `AzanNotificationManager` يخزّن قائمة في الذاكرة لكن لا توجد حلقة جدولة تُطلقها عند أوقات الصلاة. الميزة الأساسية غير مُنفّذة فعليًا.
2. **بث الأذان التلقائي غير مربوط** — `AzanStreamer` مجرّد قاموس في الذاكرة لا يستدعي `PyTgCalls`.
3. **أزرار ميتة (11+):** `azan_view_times`, `azan_next_prayer`, `azan_prayer_selection`, `azan_change_city`, `azan_change_method`, `azan_set_prelude_time`, `azan_enable_stream`, `azan_refresh_times`, `azan_refresh_next`, `azan_view_all_times`, `azan_view_settings` — مُشار إليها في لوحات المفاتيح لكن بلا معالجات.
4. **`app.run(main())`** — تمرير coroutine إلى `run()` وهو خطأ في Pyrogram 2.x.
5. **إيقاف غير آمن** — `asyncio.Event().wait()` لا يستجيب لـ SIGTERM/SIGINT من Docker/systemd → القتل القسري.

### تناقض بين التوثيق والتنفيذ
- README يدّعي "SQLite via SQLAlchemy + aiosqlite" لكن الكود يستخدم **ملف JSON** فقط.
- `MUSIC_DIR` الافتراضي متناقض: `/home/ubuntu/islamic_bot/music` في `main.py` مقابل `./music` في `.env.example`.

### مشاكل بنية ونشر
- `main.py` = 1010 سطر يخلط الإعدادات + البيانات + البث + المعالجات + التحقق.
- آثار جانبية عند الاستيراد (module-level `app = Client(...)`) — لهذا تضطر الاختبارات لحذف الوحدة من `sys.modules`.
- لا `docker-compose.yml` فعلي، لا healthcheck، لا تدوير سجلات، لا إغلاق آمن للإشارات.

---

## 2. القرارات المعمارية المعتمدة

| القرار | الخيار المختار | السبب |
|--------|----------------|-------|
| المقاربة | Strangler Fig (تدريجي) | البوت يعمل طوال التطوير؛ كل خطوة قابلة للمراجعة والاختبار |
| النشر | Docker أحادي (docker-compose) | أبسط للنقل بين السيرفرات، نقطة دخول واحدة، مناسب لـ VPS واحد |
| التخزين | SQLite عبر aiosqlite | مطابق لما يدّعيه README، بدون خادم، مناسب للحاوية مع volume |
| الجدولة | حلقة asyncio داخلية | بدون مكتبات إضافية، كافٍ لحجم البوت |
| المستخدمون | خاص (نص) + مجموعات (voice chat) | يدعم التنبيهات الفردية وبث الأذان/القرآن الجماعي |

---

## 3. البنية المستهدفة (Target Architecture)

```
islamic-unified-bot/
├── bot/                               # الحزمة الرئيسية (جديدة)
│   ├── __init__.py
│   ├── app.py                         # build_app() — لا أثر جانبي عند الاستيراد
│   ├── config.py                      # Settings dataclass + from_env()
│   ├── logging_setup.py               # RotatingFileHandler + مستوى + JSON اختياري
│   ├── deps.py                        # حاوية التبعيات (DI container)
│   ├── decorators.py                  # @owner_only, @admin_only, @safe_handler
│   ├── db/
│   │   ├── __init__.py
│   │   ├── connection.py              # aiosqlite singleton + migrations runner
│   │   ├── models.py                  # SQLAlchemy schema (للتعريف)
│   │   ├── migrate_from_json.py       # هجرة JSON → SQLite (تُشغّل مرة)
│   │   └── repositories/
│   │       ├── __init__.py
│   │       ├── user_settings.py       # CRUD المستخدمين (خاص)
│   │       └── group_settings.py      # CRUD المجموعات (voice)
│   ├── scheduler/
│   │   ├── __init__.py
│   │   ├── prayer_scheduler.py        # حلقة asyncio (30 ثانية)
│   │   └── notifier.py                # إرسال نص (خاص) + بث (مجموعة)
│   ├── streaming/
│   │   ├── __init__.py
│   │   └── stream_manager.py          # غلاف PyTgCalls + reconnect محدود
│   ├── data/
│   │   ├── __init__.py
│   │   ├── adhkar.py                  # دمج main + advanced_adhkar_library
│   │   ├── surahs.py                  # قائمة السور 1-114
│   │   └── sources.py                 # مصادر الأذان/المقدمات/القراء
│   ├── prayer/
│   │   ├── __init__.py
│   │   └── calculator.py              # PrayerTimeCalculator + CityCoordinates
│   └── handlers/
│       ├── __init__.py                # HandlerRegistry.register()
│       ├── adhkar.py
│       ├── quran.py
│       ├── azan.py                    # كل الأزرار الميتة تصبح لها معالجات
│       └── owner.py
├── main.py                            # نقطة دخول رفيعة: validate → build → run
├── healthcheck.py                     # فحص صحي للحاوية
├── deploy/
│   ├── docker-compose.yml
│   ├── install.sh                     # نص تثبيت تفاعلي
│   └── systemd/
│       └── islamic-bot.service        # (اختياري) لمن لا يريد Docker
├── tests/                             # موسّعة (وحدة + تكامل)
├── .env.example                       # محدّث ومنظّم
├── pyproject.toml                     # black/isort/flake8/ruff config
└── requirements.txt
```

### مبادئ معمارية
- **لا أثر جانبي عند الاستيراد:** `app = Client(...)` ينتقل إلى `build_app()` تُستدعى فقط من `main()`.
- **حقن التبعيات:** `StreamManager`, `PrayerScheduler`, repos تُنشأ مرة في `main()` وتمرر عبر `Dependencies` (لا singletons عالمية).
- **Config مركزي:** `Settings` dataclass واحد، يُمرر لكل المكوّنات (لا `os.getenv` متناثر).
- **فصل البيانات عن المنطق:** بيانات الأذكار/السور/المصادر في `bot/data/` كـ constants نقية.
- **Plugin Registry:** إضافة ميزة = ملف handler واحد + تسجيل في `HandlerRegistry`.

---

## 4. نموذج البيانات (SQLite Schema)

```sql
-- المستخدمون في الخاص (التنبيهات النصية)
CREATE TABLE user_settings (
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
CREATE INDEX idx_user_notif ON user_settings(notifications_on) WHERE notifications_on = 1;

-- المجموعات (بث الأذان/القرآن في voice chat)
CREATE TABLE group_settings (
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

-- سجل التنبيهات المُرسلة (منع التكرار بعد restart + race condition)
CREATE TABLE sent_notifications (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    target_id    INTEGER NOT NULL,          -- user_id (موجب) أو chat_id (سالب للمجموعة)
    target_type  TEXT NOT NULL CHECK (target_type IN ('user','group')),
    prayer       TEXT NOT NULL,
    prayer_date  TEXT NOT NULL,             -- 'YYYY-MM-DD'
    sent_at      TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(target_id, prayer, prayer_date)
);
CREATE INDEX idx_sent_lookup ON sent_notifications(target_id, prayer, prayer_date);

-- إدارة الإصدارات (migrations)
CREATE TABLE schema_version (
    version    INTEGER PRIMARY KEY,
    applied_at TEXT NOT NULL DEFAULT (datetime('now'))
);
```

### Repository Pattern (واجهات قابلة للاستبدال)
```python
class UserSettingsRepo:
    async def get(self, user_id: int) -> Optional[UserSettings]
    async def upsert(self, settings: UserSettings) -> None
    async def list_with_notifications(self) -> list[UserSettings]

class GroupSettingsRepo:
    async def get(self, chat_id: int) -> Optional[GroupSettings]
    async def upsert(self, settings: GroupSettings) -> None
    async def list_all(self) -> list[GroupSettings]
```
التبديل إلى PostgreSQL مستقبلًا = استبدال تطبيق `Database` فقط، دون لمس بقية الكود.

### الهجرة من JSON الموجود
`bot/db/migrate_from_json.py` يُشغّل عند أول إقلاع: يقرأ `azan_data/user_settings.json` (إن وُجد) → يستورد إلى SQLite → يُعيد تسمية الملف إلى `.bak`. **لا فقدان لبيانات المستخدمين.**

### Migrations
جدول `schema_version` + ملفات `migrations/0001_initial.sql`, `0002_*.sql`... تُنفّذ تلقائيًا عند الإقلاع. يسمح بإضافة أعمدة/جداول مستقبلاً دون تدخل يدوي.

---

## 5. الجدولة والتنبيهات (PrayerScheduler)

### دورة العمل
```
PrayerScheduler (مهمة خلفية)
  كل 30 ثانية:
    1. اجلب المستخدمين/المجموعات التي فعّلت التنبيهات
    2. لكل هدف: احسب أوقات صلاة اليوم
    3. قارن بالوقت الحالي + تحقق من sent_notifications
    4. أطلق: نص للمستخدم / بث للمجموعة
  المقدمة: نفس الحلقة تكتشفها قبل الأذان بـN دقيقة (مفتاح prelude_<prayer>)
```

### ضمانات الجودة الإنتاجية
| المشكلة | الحل |
|---------|------|
| تكرار التنبيه بعد restart | فحص `sent_notifications` + `UNIQUE` constraint |
| المقدمة (prelude) | حدث منفصل بمفتاح `prelude_<prayer>` |
| التوقيت الصيفي/الشتوي | إعادة حساب الأوقات يوميًا (لا cache دائم) |
| فشل إرسال واحد | كل هدف في `try/except` مستقل + سجلّ |
| ساعة السيرفر | `datetime.utcnow()` + إزاحة التوقيت للمدينة |
| الإيقاف الآمن | `stop()` يُلغي المهمة عند SIGTERM |

### واجهة Notifier (قابلة للتوسعة)
```python
class Notifier:
    async def notify_user(self, user_id, prayer, prayer_time, is_prelude=False) -> bool
    async def broadcast_group_azan(self, chat_id, prayer, azan_source) -> bool
```
تدفق أحادي: Scheduler → Notifier → StreamManager → PyTgCalls (لا اعتماد دائري).

---

## 6. البث الصوتي (StreamManager)

- **منع الحلقة اللانهائية:** علم `loop=False` افتراضيًا. الأذان = مرة واحدة. القرآن المستمر = `loop=True` يُعاد فقط إن كان `status=active` ولم يُوقف يدويًا.
- **مهلة قصوى للبث:** `DEFAULT_STREAM_DURATION` يُطبَّق فعليًا عبر `asyncio.Task` مؤجّل.
- **`STREAM_STOP_BEFORE`:** الجدولة تطلب إيقاف بث القرآن قبل الأذان بـN دقيقة.
- **Reconnect محدود:** exponential backoff (5s, 10s, 20s...) + jitter، حدّ أقصى `MAX_RECONNECT_ATTEMPTS`.
- **PyTgCalls session:** حساب UserBot مساعد (ملف `.session`) مع تعليمات واضحة في `.env.example`.

---

## 7. المعالجات (Handlers) + Plugin Registry

```python
class HandlerRegistry:
    def register(self, app: Client, deps: Dependencies) -> None:
        from . import adhkar, quran, azan, owner
        for module in (adhkar, quran, azan, owner):
            module.register(app, deps)
```

### القرارات
1. **كل زر ميت سيحصل على معالج.**
2. **نمط factory:** كل معالج يستقبل `deps` عبر closure (لا global state).
3. **Decorators:** `@owner_only`, `@admin_only` (للمجموعات), `@safe_handler` (معالجة أخطاء موحّدة).
4. **دمج الأذكار:** `main.py` + `advanced_adhkar_library.py` → `bot/data/adhkar.py` بمخطط موحّد.

---

## 8. النشر والجاهزية التشغيلية

### Dockerfile (multi-stage, non-root, healthcheck)
- Stage 1 (builder): تثبيت المكتبات في `/install`.
- Stage 2 (runtime): `python:3.12-slim` + ffmpeg + runtime فقط.
- `USER nonroot`.
- `HEALTHCHECK`.

### docker-compose.yml
- خدمة واحدة + volumes (`./data`, `./logs`, `./music`).
- `healthcheck` عبر `healthcheck.py`.
- `logging.driver: json-file` + `max-size: 10m`, `max-file: 3`.
- `stop_grace_period: 30s`.

### الإغلاق الآمن (SIGTERM/SIGINT)
```python
stop_event = asyncio.Event()
for sig in (SIGINT, SIGTERM):
    loop.add_signal_handler(sig, stop_event.set)
await stop_event.wait()
# إغلاق مرتّب: scheduler → stream → app → db
```

### Config مركزي صارم
`Settings` dataclass `frozen=True` مع `from_env()` يقرأ ويتحقق ويعطي قيمًا افتراضية + أخطاء واضحة. يُصلح تناقض `MUSIC_DIR`.

### السجلات
`RotatingFileHandler` (10MB × 5) + `LOG_LEVEL` + `LOG_FORMAT=json` اختياري + احترام `LOG_SENSITIVE_DATA=false`.

### healthcheck.py
يتحقق: قاعدة البيانات تُفتح؟ الملفات الأساسية موجودة؟ يخرج `0`/`1`.

### deploy/install.sh
نص تفاعلي: تحقق متطلبات → نسخ `.env.example` → بناء الحاوية → بدء → عرض الحالة.

---

## 9. الاختبارات

- نقل/إعادة كتابة الاختبارات الحالية لتركّز على الوحدات الجديدة.
- اختبارات تكامل للجدولة باستخدام `freezegun` (تجميد الوقت).
- **إزالة الحاجة لحذف `sys.modules['main']`** (لأن `build_app()` لا أثر جانبي له).
- عتبة التغطية: **75%** (مطابق للـ CI الحالي).

---

## 10. نطاق العمل (ملخّص)

| المحور | الحالي | المستهدف |
|--------|--------|----------|
| التنبيهات التلقائية | غير منفّذة | حلقة asyncio + منع تكرار |
| بث الأذان التلقائي | قاموس وهمي | PyTgCalls مربوط بالجدولة |
| الأزرار الميتة (11+) | تُظهر خطأ | كلها لها معالجات |
| الإغلاق الآمن | قتل قسري | SIGTERM/SIGINT |
| التخزين | JSON هشّ | SQLite + migrations |
| البنية | `main.py` 1010 سطر | حزمة `bot/` + plugin registry |
| النقل بين السيرفرات | Dockerfile بسيط | compose + healthcheck + install.sh |
| المستخدمون | خاص فقط فعليًا | خاص (نص) + مجموعات (voice) |
| الاختبارات | تعتمد على hack | نظيفة + تكامل للجدولة |

---

## 11. معايير القبول (Definition of Done)

1. `python main.py` يُقلع بنجاح بـ env صحيح دون أخطاء.
2. `pytest` يمر بعتبة ≥ 75%.
3. حلقة الجدولة تُطلق تنبيهًا فعليًا عند وقت صلاة (مُتحقَّق بـ freezegun).
4. `docker compose up` يبني ويشغّل الحاوية + healthcheck يمر.
5. إرسال SIGTERM للحاوية → إغلاق آمن مرتّب (لا قتل قسري).
6. لا أزرار ميتة: كل callback مُشار إليه له معالج.
7. `pylint` ≥ 7.0 و`black --check` و`isort --check` تمر.
8. هجرة JSON → SQLite تعمل دون فقدان بيانات.
