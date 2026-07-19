# AGENTS.md — دليل العمل في هذا المستودع

## الأوامر الأساسية

### الفحص والتنسيق
```bash
# فحص جودة الكود
ruff check bot/ main.py

# فحص التنسيق (بدون تعديل)
ruff format --check bot/ main.py

# تطبيق التنسيق
ruff format bot/ main.py
```

### الاختبارات
```bash
# تثبيت أدوات الاختبار
pip install pytest pytest-asyncio pytest-cov pytest-timeout pytest-mock aioresponses freezegun

# تشغيل كل الاختبارات
pytest

# اختبارات الوحدة فقط مع التغطية
pytest tests/unit/ -v --cov=bot --cov-report=term-missing --cov-fail-under=50

# اختبار محدد
pytest tests/unit/test_prayer_calculator.py -v
```

### التشغيل المحلي
```bash
# تفعيل البيئة الافتراضية
source venv/bin/activate    # Windows: venv\Scripts\activate

# تشغيل البوت
python main.py
```

## النشر على خادم Oracle Cloud المجاني

### الطريقة الموصى بها (systemd + script شامل)
```bash
# على الخادم (SSH) — نشر من الصفر بضغطة زر:
sudo bash scripts/deploy.sh

# أو بعد استنساخ يدوي:
sudo bash scripts/install.sh

# تحرير الإعدادات:
sudo nano /opt/islamic-unified-bot/.env

# تشغيل البوت:
sudo systemctl start islamic-bot

# متابعة السجلّات:
sudo journalctl -u islamic-bot -f
```

### التحديث اليدوي الفوري
```bash
# تحديث كامل (نظام + كود + مكتبات + إعادة تشغيل):
sudo systemctl start islamic-bot-update.service

# تنظيف يدوي:
sudo bash scripts/cleanup.sh

# عرض حالة الـ timers المجدولة:
systemctl list-timers 'islamic-bot-*'
```

### بديل Docker
```bash
docker compose up -d
docker compose logs -f
```

## بنية المشروع

```
islamic-unified-bot/
├── main.py                       # نقطة الدخول + مراقب الذاكرة
├── bot/
│   ├── config.py                 # إعدادات من .env (frozen dataclass)
│   ├── deps.py                   # حاوية التبعيات (DI)
│   ├── decorators.py             # owner_only / admin_only / safe_handler
│   ├── app.py                    # بناء Pyrogram Client
│   ├── logging_setup.py          # RotatingFileHandler
│   ├── handlers/                 # معالجات الأوامر (Plugin Registry)
│   ├── scheduler/                # جدولة الصلاة + الأذكار
│   ├── streaming/                # غلاف PyTgCalls
│   ├── prayer/                   # حساب أوقات الصلاة
│   ├── services/                 # QuranRadio
│   ├── db/                       # aiosqlite + migrations
│   └── data/                     # بيانات ثابتة (أذكار، سور، مدن)
├── scripts/                      # سكربتات النشر والصيانة
│   ├── deploy.sh                 # نشر من الصفر
│   ├── install.sh                # تثبيت كامل (swap + systemd + venv)
│   ├── weekly-update.sh          # تحديث أسبوعي (نظام + كود + مكتبات)
│   ├── cleanup.sh                # تنظيف أسبوعي
│   ├── islamic-bot.service       # systemd unit للبوت
│   ├── islamic-bot-update.{service,timer}   # تحديث أسبوعي
│   └── islamic-bot-cleanup.{service,timer} # تنظيف أسبوعي
├── tests/                        # اختبارات pytest
├── Dockerfile                    # صورة خفيفة (slim)
├── docker-compose.yml            # نشر Docker مع حدود موارد
├── requirements.txt              # مكتبات بايثون
└── .env.example                  # قالب الإعدادات
```

## قواعد مهمة

- **عدم الالتزام (commit)** إلا إذا طُلب صراحة.
- **عدم إضافة تعليقات** في الكود إلا إذا طُلبت.
- **اتّباع نمط الكود الحالي**: استيراد كسلي داخل الدوال، `from __future__ import annotations`، type hints.
- **عدم تغيير migrations المُطبّقة**: أضف migration جديدًا مرقّمًا بدلًا من تعديل القديم.
- **كل ميزة جديدة**: ملف في `bot/handlers/` + سطر في `HandlerRegistry.register()`.
- **الإعدادات**: تُقرأ من `.env` فقط، لا تكتب `os.getenv` مباشرة في المعالجات.
- **الأخطاء**: استخدم `@safe_handler()` لمعالجات الأوامر، `logger.exception` للأخطاء الحرجة.

## حدود الموارد (خادم Oracle المجاني 1GB RAM)

| المكوّن | الحد |
|---------|------|
| systemd MemoryMax | 700 MB |
| systemd MemoryHigh | 600 MB |
| مراقب الذاكرة الداخلي | 600 MB (قابل للضبط عبر `HIGH_MEMORY_THRESHOLD_MB`) |
| Swap الموصى به | 2× RAM (يُنشأ تلقائيًا عبر `install.sh`) |
| Docker mem_limit | 700 MB |

## الفحوصات قبل النشر

```bash
# 1) تنسيق الكود
ruff format bot/ main.py
ruff check bot/ main.py

# 2) الاختبارات
pytest tests/unit/ -v

# 3) فحص الأمان
bandit -r bot/ main.py --severity-level high
pip-audit -r requirements.txt

# 4) فحص الاستيراد (smoke test)
python -c "import main"
```
