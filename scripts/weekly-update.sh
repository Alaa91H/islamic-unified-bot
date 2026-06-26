#!/usr/bin/env bash
set -euo pipefail

LOG="/var/log/islamic-bot-update.log"
BOT_DIR="/opt/islamic-unified-bot"
VENV_PIP="$BOT_DIR/venv/bin/pip"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] === بداية التحديث الأسبوعي ===" >> "$LOG"

# 1. تحديث حزم النظام
echo "[$(date '+%H:%M:%S')] تحديث حزم النظام..." >> "$LOG"
apt-get update -qq >> "$LOG" 2>&1
apt-get upgrade -y -qq >> "$LOG" 2>&1
apt-get autoremove -y -qq >> "$LOG" 2>&1
echo "[$(date '+%H:%M:%S')] ✅ تم تحديث حزم النظام" >> "$LOG"

# 2. تحديث مكتبات بايثون
echo "[$(date '+%H:%M:%S')] تحديث مكتبات بايثون..." >> "$LOG"
"$VENV_PIP" install --upgrade pip -q >> "$LOG" 2>&1
"$VENV_PIP" install --upgrade -r "$BOT_DIR/requirements.txt" -q >> "$LOG" 2>&1
echo "[$(date '+%H:%M:%S')] ✅ تم تحديث مكتبات بايثون" >> "$LOG"

# 3. إعادة تشغيل البوت
echo "[$(date '+%H:%M:%S')] إعادة تشغيل البوت..." >> "$LOG"
systemctl restart islamic-bot >> "$LOG" 2>&1
echo "[$(date '+%H:%M:%S')] ✅ تم إعادة تشغيل البوت" >> "$LOG"

echo "[$(date '+%H:%M:%S')] === انتهى التحديث الأسبوعي ===" >> "$LOG"
