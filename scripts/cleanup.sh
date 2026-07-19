#!/usr/bin/env bash
# ============================================================================
# التنظيف الأسبوعي الشامل لـ Islamic Unified Bot
# - يسجّلات البوت القديمة
# - ملفات الـ session القديمة
# - ذاكرة pip و apt المؤقتة
# - journalctl القديم
# - __pycache__ و .pyc
# - الصور والحاويات المعلّقة في Docker (إن وُجد)
# - ملفات /tmp المؤقتة
# ============================================================================
set -euo pipefail

LOG="${LOG:-/var/log/islamic-bot-cleanup.log}"
BOT_DIR="${BOT_DIR:-/opt/islamic-unified-bot}"
PIP="${BOT_DIR}/venv/bin/pip"

ts() { date '+%Y-%m-%d %H:%M:%S'; }
log() { echo "[$(ts)] $*" >> "$LOG"; }

log "=== بداية التنظيف الأسبوعي ==="

# ---------------------------------------------------------------------------
# 1) سجلات البوت — احتفظ بآخر 3 أيام فقط
# ---------------------------------------------------------------------------
log "تنظيف سجلات البوت القديمة..."
if [ -d "$BOT_DIR/logs" ]; then
    find "$BOT_DIR/logs" -name "*.log.20*" -mtime +3 -delete 2>/dev/null || true
    find "$BOT_DIR/logs" -name "*.log" -mtime +7 -delete 2>/dev/null || true
    log "✅ تم تنظيف السجلات"
fi

# ---------------------------------------------------------------------------
# 2) ملفات الـ session القديمة (أكثر من 30 يومًا)
# ---------------------------------------------------------------------------
log "تنظيف ملفات الـ session القديمة..."
find "$BOT_DIR" -maxdepth 1 -name "*.session" -mtime +30 -delete 2>/dev/null || true
find "$BOT_DIR" -maxdepth 1 -name "*.session-journal" -mtime +30 -delete 2>/dev/null || true
log "✅ تم تنظيف الجلسات"

# ---------------------------------------------------------------------------
# 3) ذاكرة pip المؤقتة
# ---------------------------------------------------------------------------
if [ -x "$PIP" ]; then
    log "تنظيف ذاكرة pip المؤقتة..."
    "$PIP" cache purge -q >> "$LOG" 2>&1 || true
    log "✅ تم تنظيف pip cache"
fi

# ---------------------------------------------------------------------------
# 4) ذاكرة apt المؤقتة
# ---------------------------------------------------------------------------
if command -v apt-get >/dev/null 2>&1; then
    log "تنظيف ذاكرة apt المؤقتة..."
    apt-get clean -qq >> "$LOG" 2>&1 || true
    apt-get autoremove -y --purge -qq >> "$LOG" 2>&1 || true
    log "✅ تم تنظيف apt cache"
elif command -v dnf >/dev/null 2>&1; then
    log "تنظيف ذاكرة dnf المؤقتة..."
    dnf clean all -q >> "$LOG" 2>&1 || true
    log "✅ تم تنظيف dnf cache"
fi

# ---------------------------------------------------------------------------
# 5) journalctl — احتفظ بآخر 7 أيام و100MB
# ---------------------------------------------------------------------------
log "تنظيف journalctl..."
journalctl --vacuum-time=7d --quiet >> "$LOG" 2>&1 || true
journalctl --vacuum-size=100M --quiet >> "$LOG" 2>&1 || true
log "✅ تم تنظيف journalctl"

# ---------------------------------------------------------------------------
# 6) ملفات __pycache__ و .pyc المنتشرة (لا تلمس venv)
# ---------------------------------------------------------------------------
log "تنظيف __pycache__..."
find "$BOT_DIR" -path "$BOT_DIR/venv" -prune -o -type d -name "__pycache__" \
    -exec rm -rf {} + 2>/dev/null || true
find "$BOT_DIR" -path "$BOT_DIR/venv" -prune -o -name "*.pyc" -print0 | \
    xargs -0 -r rm -f 2>/dev/null || true
find "$BOT_DIR" -path "$BOT_DIR/venv" -prune -o -name "*.pyo" -print0 | \
    xargs -0 -r rm -f 2>/dev/null || true
log "✅ تم تنظيف pycache"

# ---------------------------------------------------------------------------
# 7) ملفات مؤقتة في /tmp تخص البوت فقط (أكثر من يوم)
# ---------------------------------------------------------------------------
log "تنظيف /tmp (ملفات البوت فقط)..."
find /tmp -maxdepth 2 -name "tmp*islamic*" -mtime +1 -delete 2>/dev/null || true
find /tmp -maxdepth 2 -name "pyrogram*" -mtime +1 -delete 2>/dev/null || true
find /tmp -maxdepth 2 -name "ffconv*" -mtime +1 -delete 2>/dev/null || true
find /tmp -maxdepth 2 -name "py-tgcalls*" -mtime +1 -delete 2>/dev/null || true
find /tmp -maxdepth 2 -name "ntgcalls*" -mtime +1 -delete 2>/dev/null || true
log "✅ تم تنظيف /tmp (ملفات البوت فقط)"

# ---------------------------------------------------------------------------
# 8) صور وحاويات Docker المعلّقة (إن وُجد docker)
# ---------------------------------------------------------------------------
if command -v docker >/dev/null 2>&1; then
    log "تنظيف Docker المعلّق..."
    docker system prune -f --filter "until=72h" >> "$LOG" 2>&1 || true
    docker image prune -f -a --filter "until=168h" >> "$LOG" 2>&1 || true
    log "✅ تم تنظيف Docker"
fi

# ---------------------------------------------------------------------------
# 9) ملفات .log الكبيرة جدًا (أكثر من 50MB) — قصّها
# ---------------------------------------------------------------------------
if [ -d "$BOT_DIR/logs" ]; then
    log "فحص ملفات السجل الكبيرة..."
    find "$BOT_DIR/logs" -name "*.log" -size +50M -exec sh -c '
        for f; do
            tail -n 5000 "$f" > "$f.tmp" && mv "$f.tmp" "$f"
        done
    ' _ {} + 2>/dev/null || true
    log "✅ تم قص الملفات الكبيرة"
fi

log "=== انتهى التنظيف الأسبوعي ==="
