#!/usr/bin/env bash
# ============================================================================
# التحديث الأسبوعي الشامل لـ Islamic Unified Bot
# - يحدّث حزم النظام (apt upgrade + autoremove)
# - يسحب أحدث كود من git
# - يحدّث مكتبات بايثون
# - يعيد تشغيل البوت بأمان
# - يُنفّذ بـ systemd timer أو cron كـ root (يتطلب sudo apt-get)
# ============================================================================
set -euo pipefail

LOG="${LOG:-/var/log/islamic-bot-update.log}"
BOT_DIR="${BOT_DIR:-/opt/islamic-unified-bot}"
VENV_PIP="$BOT_DIR/venv/bin/pip"
VENV_PYTHON="$BOT_DIR/venv/bin/python"
LOCK_FILE="/var/run/islamic-bot-update.lock"

ts() { date '+%Y-%m-%d %H:%M:%S'; }
log() { echo "[$(ts)] $*" >> "$LOG"; }

# منع التشغيل المتزامن (إذا تزامن مع cron يدويًا)
if [ -f "$LOCK_FILE" ]; then
    PID=$(cat "$LOCK_FILE" 2>/dev/null || echo "")
    if [ -n "$PID" ] && kill -0 "$PID" 2>/dev/null; then
        log "⚠️ تحديث آخر جارٍ (PID=$PID) — خروج"
        exit 0
    fi
fi
echo $$ > "$LOCK_FILE"
trap 'rm -f "$LOCK_FILE"' EXIT

log "=== بداية التحديث الأسبوعي ==="

# ---------------------------------------------------------------------------
# 1) تحديث حزم النظام
# ---------------------------------------------------------------------------
log "تحديث قائمة حزم النظام (apt-get update)..."
if command -v apt-get >/dev/null 2>&1; then
    apt-get update -qq >> "$LOG" 2>&1 || log "⚠️ apt-get update فشل (متابعة)"
    log "ترقية حزم النظام (apt-get upgrade)..."
    DEBIAN_FRONTEND=noninteractive apt-get -y -o Dpkg::Options::="--force-confdef" \
        -o Dpkg::Options::="--force-confold" upgrade >> "$LOG" 2>&1 || \
        log "⚠️ apt-get upgrade فشل جزئيًا (متابعة)"
    log "إزالة الحزم اليتيمة (apt-get autoremove)..."
    apt-get autoremove -y -qq >> "$LOG" 2>&1 || true
    log "تنظيف apt cache..."
    apt-get clean -qq >> "$LOG" 2>&1 || true
    log "✅ تم تحديث حزم النظام"
elif command -v dnf >/dev/null 2>&1; then
    # Oracle Linux / RHEL-based
    log "نظام RHEL-like — استخدام dnf..."
    dnf -y upgrade >> "$LOG" 2>&1 || log "⚠️ dnf upgrade فشل (متابعة)"
    dnf -y autoremove >> "$LOG" 2>&1 || true
    log "✅ تم تحديث حزم النظام (dnf)"
fi

# ---------------------------------------------------------------------------
# 2) سحب أحدث كود من git
# ---------------------------------------------------------------------------
if [ -d "$BOT_DIR/.git" ]; then
    log "سحب أحدث كود من git..."
    cd "$BOT_DIR"
    # احفظ التعديلات المحلية إن وُجدت (مثل .env محليًا — لكنه في .gitignore)
    if ! git diff --quiet HEAD 2>/dev/null; then
        log "⚠️ تغييرات محلية في الـ working tree — لا أُسحب فوقها"
    else
        git fetch --all --prune >> "$LOG" 2>&1 || log "⚠️ git fetch فشل (متابعة)"
        BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "main")
        git reset --hard "origin/$BRANCH" >> "$LOG" 2>&1 || \
            log "⚠️ git reset فشل (متابعة)"
        log "✅ تم تحديث الكود (فرع: $BRANCH)"
    fi
else
    log "ℹ️ لا يوجد .git في $BOT_DIR — تخطّي تحديث الكود"
fi

# ---------------------------------------------------------------------------
# 3) تحديث مكتبات بايثون
# ---------------------------------------------------------------------------
if [ -x "$VENV_PIP" ]; then
    log "تحديث pip..."
    "$VENV_PIP" install --upgrade pip -q >> "$LOG" 2>&1 || \
        log "⚠️ تحديث pip فشل (متابعة)"
    log "تحديث مكتبات بايثون من requirements.txt..."
    "$VENV_PIP" install --upgrade -r "$BOT_DIR/requirements.txt" -q >> "$LOG" 2>&1 || \
        log "⚠️ تحديث requirements فشل (متابعة)"
    log "تنظيف pip cache..."
    "$VENV_PIP" cache purge -q >> "$LOG" 2>&1 || true
    log "✅ تم تحديث مكتبات بايثون"
else
    log "⚠️ لم يُعثر على venv في $BOT_DIR — تخطّي تحديث بايثون"
fi

# ---------------------------------------------------------------------------
# 4) فحص سلامة الكود (import check) قبل إعادة التشغيل
# ---------------------------------------------------------------------------
if [ -x "$VENV_PYTHON" ]; then
    log "فحص سلامة الاستيراد..."
    if "$VENV_PYTHON" -c "import main" >> "$LOG" 2>&1; then
        log "✅ فحص الاستيراد نجح"
    else
        log "❌ فحص الاستيراد فشل — لن أعيد التشغيل لتجنّب الانقطاع"
        log "=== انتهى التحديث (بفشل الاستيراد) ==="
        exit 1
    fi
fi

# ---------------------------------------------------------------------------
# 5) إعادة تشغيل البوت
# ---------------------------------------------------------------------------
log "إعادة تشغيل البوت..."
systemctl restart islamic-bot >> "$LOG" 2>&1 || \
    log "⚠️ systemctl restart فشل"
sleep 5
if systemctl is-active --quiet islamic-bot; then
    log "✅ البوت يعمل بنجاح بعد التحديث"
else
    log "❌ البوت لم يُقلع بعد التحديث — راجع journalctl"
    systemctl status islamic-bot --no-pager >> "$LOG" 2>&1 || true
fi

log "=== انتهى التحديث الأسبوعي ==="
