#!/usr/bin/env bash
# ============================================================================
# install.sh — تثبيت كامل لـ Islamic Unified Bot على خادم Oracle Cloud المجاني
#
# يدعم:
#   - Ubuntu 20.04/22.04/24.04 (x86_64 و aarch64/ARM)
#   - إنشاء swap تلقائيًا للخوادم منخفضة الذاكرة (1GB)
#   - تثبيت Python + ffmpeg + git + venv
#   - نسخ ملفات systemd service و timer
#   - تكوين التحديث والتنظيف الأسبوعي
#
# الاستخدام:
#   sudo bash scripts/install.sh
#
# يجب تشغيله بعد استنساخ المستودع إلى /opt/islamic-unified-bot
# ============================================================================
set -euo pipefail

# ----------------------------------------------------------------------------
# ألوان وإخراج
# ----------------------------------------------------------------------------
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

info()  { echo -e "${BLUE}[ℹ]${NC} $*"; }
ok()    { echo -e "${GREEN}[✅]${NC} $*"; }
warn()  { echo -e "${YELLOW}[⚠]${NC} $*"; }
fail()  { echo -e "${RED}[❌]${NC} $*" >&2; exit 1; }

# ----------------------------------------------------------------------------
# فحوصات أولية
# ----------------------------------------------------------------------------
[ "$(id -u)" -eq 0 ] || fail "يجب تشغيل هذا السكربت بـ sudo أو كـ root"

BOT_DIR="${BOT_DIR:-/opt/islamic-unified-bot}"
SERVICE_USER="${SERVICE_USER:-ubuntu}"
[ -d "$BOT_DIR" ] || fail "المجلد $BOT_DIR غير موجود — استنسخ المستودع أولًا"
[ -f "$BOT_DIR/main.py" ] || fail "main.py غير موجود في $BOT_DIR"

ARCH=$(uname -m)
info "نظام التشغيل: $(. /etc/os-release 2>/dev/null && echo "$PRETTY_NAME" || echo "غير معروف")"
info "المعمارية: $ARCH"
info "مجلد البوت: $BOT_DIR"
info "مستخدم الخدمة: $SERVICE_USER"

# ----------------------------------------------------------------------------
# 1) إنشاء مستخدم ubuntu إن لم يوجد (افتراضي Oracle Cloud)
# ----------------------------------------------------------------------------
if ! id "$SERVICE_USER" >/dev/null 2>&1; then
    info "إنشاء المستخدم $SERVICE_USER..."
    useradd -m -s /bin/bash "$SERVICE_USER"
    ok "تم إنشاء المستخدم $SERVICE_USER"
fi

# ----------------------------------------------------------------------------
# 2) إنشاء swap للخوادم منخفضة الذاكرة (إذا كانت RAM ≤ 2GB ولم يوجد swap)
# ----------------------------------------------------------------------------
create_swap() {
    local RAM_MB SWAP_MB SWAP_FILE
    RAM_MB=$(awk '/MemTotal/ {printf "%d", $2/1024}' /proc/meminfo)
    if swapon --show=SIZE --bytes --noheadings 2>/dev/null | awk '{s+=$1} END {exit !(s>0)}'; then
        info "يوجد swap بالفعل — تخطّي الإنشاء"
        return 0
    fi
    if [ "$RAM_MB" -gt 2048 ]; then
        info "الذاكرة $RAM_MB MB كافية — لا حاجة لـ swap إجباري"
        return 0
    fi
    SWAP_MB=$((RAM_MB * 2))
    [ "$SWAP_MB" -gt 4096 ] && SWAP_MB=4096
    SWAP_FILE="/swapfile"
    info "إنشاء swap بحجم ${SWAP_MB}MB في $SWAP_FILE..."
    fallocate -l "${SWAP_MB}M" "$SWAP_FILE" 2>/dev/null || dd if=/dev/zero of="$SWAP_FILE" bs=1M count="$SWAP_MB" status=progress
    chmod 600 "$SWAP_FILE"
    mkswap "$SWAP_FILE" >/dev/null
    swapon "$SWAP_FILE"
    # إضافة لـ fstab لتثبيتها عبر إعادة الإقلاع
    if ! grep -q "^$SWAP_FILE" /etc/fstab; then
        echo "$SWAP_FILE none swap sw 0 0" >> /etc/fstab
    fi
    # تقليل ميل swappiness لتفضيل RAM على الخادم الضعيف
    sysctl vm.swappiness=10 >/dev/null 2>&1 || true
    if ! grep -q "^vm.swappiness" /etc/sysctl.conf; then
        echo "vm.swappiness=10" >> /etc/sysctl.conf
    fi
    ok "تم إنشاء swap بحجم ${SWAP_MB}MB (swappiness=10)"
}

create_swap

# ----------------------------------------------------------------------------
# 3) تثبيت حزم النظام
# ----------------------------------------------------------------------------
info "تثبيت حزم النظام (python3, ffmpeg, git, ...)..."
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y --no-install-recommends \
    python3 python3-pip python3-venv python3-dev \
    ffmpeg git curl ca-certificates \
    build-essential 2>&1 | tail -5
ok "تم تثبيت حزم النظام"

# ----------------------------------------------------------------------------
# 4) إنشاء venv وتثبيت مكتبات بايثون
# ----------------------------------------------------------------------------
if [ ! -x "$BOT_DIR/venv/bin/python" ]; then
    info "إنشاء بيئة افتراضية (venv)..."
    python3 -m venv "$BOT_DIR/venv"
    ok "تم إنشاء venv"
fi

info "ترقية pip..."
"$BOT_DIR/venv/bin/pip" install --upgrade pip -q

info "تثبيت مكتبات المشروع..."
"$BOT_DIR/venv/bin/pip" install -r "$BOT_DIR/requirements.txt" 2>&1 | tail -3
ok "تم تثبيت المكتبات"

# ----------------------------------------------------------------------------
# 5) تكوين ملف .env إن لم يوجد
# ----------------------------------------------------------------------------
if [ ! -f "$BOT_DIR/.env" ]; then
    if [ -f "$BOT_DIR/.env.example" ]; then
        cp "$BOT_DIR/.env.example" "$BOT_DIR/.env"
        warn "تم إنشاء .env من القالب — عدّله الآن بقيمك الحقيقية:"
        warn "  nano $BOT_DIR/.env"
        warn "ثم شغّل: sudo systemctl start islamic-bot"
    fi
fi

# ----------------------------------------------------------------------------
# 6) إنشاء المجلدات اللازمة وضبط الملكية
# ----------------------------------------------------------------------------
mkdir -p "$BOT_DIR/logs" "$BOT_DIR/azan_data" "$BOT_DIR/data" "$BOT_DIR/music"
chown -R "$SERVICE_USER":"$SERVICE_USER" "$BOT_DIR"
ok "تم ضبط الملكية على $BOT_DIR"

# ----------------------------------------------------------------------------
# 7) تثبيت ملفات systemd service + timer
# ----------------------------------------------------------------------------
info "تثبيت ملفات systemd..."

cp "$BOT_DIR/scripts/islamic-bot.service" /etc/systemd/system/
cp "$BOT_DIR/scripts/islamic-bot-update.service" /etc/systemd/system/
cp "$BOT_DIR/scripts/islamic-bot-update.timer" /etc/systemd/system/
cp "$BOT_DIR/scripts/islamic-bot-cleanup.service" /etc/systemd/system/
cp "$BOT_DIR/scripts/islamic-bot-cleanup.timer" /etc/systemd/system/

# جعل سكربتات الـ shell قابلة للتنفيذ
chmod +x "$BOT_DIR/scripts/weekly-update.sh" "$BOT_DIR/scripts/cleanup.sh"

systemctl daemon-reload
systemctl enable islamic-bot.service
systemctl enable --now islamic-bot-update.timer
systemctl enable --now islamic-bot-cleanup.timer
ok "تم تثبيت systemd units"

# عرض حالة الـ timers
info "حالة الـ timers المجدولة:"
systemctl list-timers "islamic-bot-*" --no-pager 2>/dev/null || true

# ----------------------------------------------------------------------------
# 8) تسهيلات: ربط docker-compose اختياري وملف سجل التحديث
# ----------------------------------------------------------------------------
touch /var/log/islamic-bot-update.log /var/log/islamic-bot-cleanup.log
chmod 644 /var/log/islamic-bot-update.log /var/log/islamic-bot-cleanup.log

# ----------------------------------------------------------------------------
# 9) ملخّص الحالة
# ----------------------------------------------------------------------------
echo
echo -e "${GREEN}════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}  ✅ تم تثبيت Islamic Unified Bot بنجاح${NC}"
echo -e "${GREEN}════════════════════════════════════════════════════${NC}"
echo
echo -e "  📂 مجلد البوت:    ${BLUE}$BOT_DIR${NC}"
echo -e "  📝 ملف الإعدادات: ${BLUE}$BOT_DIR/.env${NC}"
echo -e "  🐍 بايثون:        ${BLUE}$BOT_DIR/venv/bin/python${NC}"
echo
echo -e "  ${YELLOW}الخطوات التالية:${NC}"
echo -e "    1) عدّل الإعدادات:   ${BLUE}sudo nano $BOT_DIR/.env${NC}"
echo -e "    2) شغّل البوت:       ${BLUE}sudo systemctl start islamic-bot${NC}"
echo -e "    3) تابع السجلّات:    ${BLUE}sudo journalctl -u islamic-bot -f${NC}"
echo
echo -e "  ${YELLOW}أوامر مفيدة:${NC}"
echo -e "    إعادة التشغيل:      ${BLUE}sudo systemctl restart islamic-bot${NC}"
echo -e "    حالة البوت:          ${BLUE}sudo systemctl status islamic-bot${NC}"
echo -e "    تحديث فوري:          ${BLUE}sudo systemctl start islamic-bot-update.service${NC}"
echo -e "    تنظيف فوري:          ${BLUE}sudo bash $BOT_DIR/scripts/cleanup.sh${NC}"
echo
echo -e "  ${GREEN}التحديث الأسبوعي التلقائي:${NC} كل سبت 03:00 + عشوائية ساعة"
echo -e "  ${GREEN}التنظيف الأسبوعي التلقائي:${NC} كل سبت 04:00"
echo
echo -e "  ${YELLOW}لعرض الـ timers:${NC} ${BLUE}systemctl list-timers 'islamic-bot-*'${NC}"
echo
