# ============================================================================
# Dockerfile — Islamic Unified Bot
# مُحسّن لخادم Oracle Cloud المجاني (x86_64 و ARM64/aarch64)
# يستخدم صورة slim خفيفة + تثبيت ffmpeg فقط (بدون build-essential)
# ============================================================================
FROM python:3.12-slim

# تثبيت ffmpeg فقط — لا build-essential لتقليل حجم الصورة
# ffmpeg مطلوب لـ py-tgcalls وبث القرآن
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ffmpeg \
        ca-certificates \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# تثبيت المكتبات أولاً للاستفادة من طبقة cache
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# نسخ الكود
COPY . .

# إنشاء المجلدات اللازمة
RUN mkdir -p music azan_data logs data

# متغيرات البيئة لتحسين الأداء على خادم ضعيف
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONHASHSEED=0 \
    LIGHTWEIGHT_MODE=true \
    DB_POOL_SIZE=3 \
    MAX_CONCURRENT_STREAMS=2 \
    LOG_LEVEL=INFO

# حدود الموارد — تعمل مع docker --memory=700m
# (تُطبّق عبر docker-compose أو docker run)

# فحص سلامة دوري: يفحص ملف heartbeat يُحدّثه البوت كل بضع دقائق
# إن تجاوز 5 دقائق دون تحديث، تُعتبر الحاوية غير صحية ويُعاد تشغيلها
HEALTHCHECK --interval=5m --timeout=10s --start-period=60s --retries=3 \
    CMD python -c "import os,time; assert time.time()-os.path.getmtime('/app/.health')<300" || exit 1

CMD ["python", "main.py"]
