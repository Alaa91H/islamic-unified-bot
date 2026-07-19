#!/usr/bin/env bash
# ============================================================================
# deploy.sh — نشر مستقل كامل لـ Islamic Unified Bot على خادم جديد
#
# سكربت "ضغطة زر" يقوم بكل شيء من الصفر:
#   1. يثبّت git
#   2. يستنسخ المستودع إلى /opt/islamic-unified-bot
#   3. يشغّل install.sh الذي يثبّت كل شيء آخر
#
# الاستخدام (SSH على الخادم Oracle Cloud ثم):
#   curl -fsSL https://raw.githubusercontent.com/Alaa91H/islamic-unified-bot/main/scripts/deploy.sh | sudo bash
#
# أو بعد استنساخ يدوي:
#   sudo bash scripts/deploy.sh
#
# متغيرات بيئة اختيارية:
#   REPO_URL   — رابط المستودع (افتراضي: Alaa91H/islamic-unified-bot)
#   BRANCH     — الفرع (افتراضي: main)
#   BOT_DIR    — مجلد التثبيت (افتراضي: /opt/islamic-unified-bot)
# ============================================================================
set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

info()  { echo -e "${BLUE}[ℹ]${NC} $*"; }
ok()    { echo -e "${GREEN}[✅]${NC} $*"; }
warn()  { echo -e "${YELLOW}[⚠]${NC} $*"; }
fail()  { echo -e "${RED}[❌]${NC} $*" >&2; exit 1; }

[ "$(id -u)" -eq 0 ] || fail "يجب تشغيل هذا السكربت بـ sudo أو كـ root"

REPO_URL="${REPO_URL:-https://github.com/Alaa91H/islamic-unified-bot.git}"
BRANCH="${BRANCH:-main}"
BOT_DIR="${BOT_DIR:-/opt/islamic-unified-bot}"

ARCH=$(uname -m)
info "المعمارية: $ARCH"
info "الرابط: $REPO_URL (فرع: $BRANCH)"
info "مجلد الهدف: $BOT_DIR"

# ----------------------------------------------------------------------------
# 1) تثبيت git إن لم يوجد
# ----------------------------------------------------------------------------
if ! command -v git >/dev/null 2>&1; then
    info "تثبيت git..."
    export DEBIAN_FRONTEND=noninteractive
    apt-get update -qq
    apt-get install -y -qq git >/dev/null
    ok "تم تثبيت git"
fi

# ----------------------------------------------------------------------------
# 2) استنساخ المستودع إن لم يوجد، أو سحب التحديثات إن وُجد
# ----------------------------------------------------------------------------
if [ ! -d "$BOT_DIR/.git" ]; then
    info "استنساخ المستودع إلى $BOT_DIR..."
    mkdir -p "$(dirname "$BOT_DIR")"
    git clone --depth 1 -b "$BRANCH" "$REPO_URL" "$BOT_DIR"
    ok "تم الاستنساخ"
else
    info "المستودع موجود — سحب التحديثات..."
    cd "$BOT_DIR"
    git fetch --depth 1 origin "$BRANCH"
    git reset --hard "origin/$BRANCH"
    ok "تم تحديث الكود"
fi

# ----------------------------------------------------------------------------
# 3) تشغيل install.sh
# ----------------------------------------------------------------------------
info "تشغيل install.sh..."
bash "$BOT_DIR/scripts/install.sh"

echo
ok "اكتمل النشر! عدّل $BOT_DIR/.env ثم شغّل: sudo systemctl start islamic-bot"
