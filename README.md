<div align="center">

<img src="https://raw.githubusercontent.com/Alaa91H/islamic-unified-bot/main/assets/banner.png" alt="Islamic Unified Bot" width="100%" />

# 🕌 Islamic Unified Bot

**A production-grade Telegram bot unifying Adhkar, Quran streaming, and automated prayer-time notifications in a single service.**

[![CI/CD Pipeline](https://github.com/Alaa91H/islamic-unified-bot/actions/workflows/ci-cd.yml/badge.svg)](https://github.com/Alaa91H/islamic-unified-bot/actions/workflows/ci-cd.yml)
[![Python](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12-blue?logo=python&logoColor=white)](https://www.python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Imports: isort](https://img.shields.io/badge/imports-isort-ef8336.svg)](https://pycqa.github.io/isort/)
[![Security: bandit](https://img.shields.io/badge/security-bandit-yellow.svg)](https://github.com/PyCQA/bandit)
[![Telegram](https://img.shields.io/badge/Telegram-Bot-2CA5E0?logo=telegram)](https://core.telegram.org/bots)

</div>

---

## 📋 Table of Contents

- [Overview](#-overview)
- [Features](#-features)
- [Architecture](#-architecture)
- [Requirements](#-requirements)
- [Quick Start](#-quick-start)
- [Configuration](#-configuration)
- [Deployment](#-deployment)
  - [Linux / Ubuntu (systemd)](#linux--ubuntu-systemd)
  - [Docker](#docker)
- [CI/CD Pipeline](#-cicd-pipeline)
- [Testing](#-testing)
- [Project Structure](#-project-structure)
- [Environment Variables](#-environment-variables)
- [Contributing](#-contributing)
- [Security](#-security)
- [License](#-license)

---

## 🌟 Overview

**Islamic Unified Bot** is a feature-rich Telegram bot designed for Muslim communities worldwide. It consolidates three independent services — Adhkar reminders, live Quran audio streaming, and accurate prayer-time scheduling — into a single, maintainable Python application.

The bot is built on [Pyrogram](https://docs.pyrogram.org/) and [PyTgCalls](https://pytgcalls.github.io/), follows clean architecture principles, and ships with a full CI/CD pipeline on GitHub Actions.

---

## ✨ Features

### 📿 Adhkar Module
- Curated Islamic remembrances (أذكار) organized by category
- Morning (*sabah*) and evening (*masa'*) Adhkar sequences
- After-prayer Adhkar with optional repetition counters
- Inline keyboard navigation — no slash-command memorization required

### 📖 Quran Module
- Live audio streaming of all **114 Surahs** directly into Telegram voice chats
- Multiple reciter sources configurable per group
- Graceful reconnect on network interruption

### 🕌 Azan & Prayer Times Module
- Accurate prayer-time calculation for **1 000+ cities worldwide**
- Multiple calculation methods: ISNA, Muslim World League, Egyptian, Umm al-Qura, and more
- Hanafi / Shafi'i Asr methods supported
- Automatic Azan audio broadcast at each prayer time
- Pre-Azan notification (configurable lead time)
- Per-group settings stored in SQLite via SQLAlchemy + aiosqlite
- Hijri date display alongside Gregorian

---

## 🏗️ Architecture

```
islamic-unified-bot/
├── main.py                     # Entry point — Pyrogram client, event loop
├── azan_commands.py            # All /azan command handlers & callbacks
├── azan_manager.py             # Scheduler, streamer, notification manager
├── azan_prayer_times.py        # Pure-Python prayer-time calculations
├── azan_config.py              # Azan / prelude audio source registry
├── advanced_adhkar_library.py  # Complete Adhkar data store
├── requirements.txt
├── Dockerfile
├── pytest.ini
├── .env.example
└── tests/
    ├── conftest.py
    ├── test_prayer_times.py
    ├── test_azan_manager.py
    ├── test_config_and_bot.py
    └── test_data_integrity.py
```

**Key design decisions:**
- **Async-first**: everything runs on a single `asyncio` event loop — no threads.
- **No ORM magic**: raw SQL via `aiosqlite` for the hot path; SQLAlchemy models for schema definition only.
- **Stateless config**: all runtime state lives in SQLite; the process can be restarted at any time safely.
- **Dependency injection via module-level singletons**: `azan_scheduler` and `azan_streamer` are created once and shared across command handlers.

---

## 📦 Requirements

| Requirement | Version |
|-------------|---------|
| Python | 3.10+ |
| FFmpeg | 4.x + |
| Telegram API account | — |

---

## 🚀 Quick Start

### 1. Clone the repository

```bash
git clone https://github.com/Alaa91H/islamic-unified-bot.git
cd islamic-unified-bot
```

### 2. Create and activate a virtual environment

```bash
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Configure environment variables

```bash
cp .env.example .env
nano .env                       # fill in the four required values
```

See [Environment Variables](#-environment-variables) for a full reference.

### 5. Run

```bash
python main.py
```

---

## ⚙️ Configuration

All configuration is driven by a single `.env` file. Copy `.env.example` and edit:

```env
BOT_TOKEN=123456:ABC-DEF...          # from @BotFather
API_ID=12345678                      # from https://my.telegram.org
API_HASH=abcdef1234...               # from https://my.telegram.org
OWNER_ID=987654321                   # your numeric Telegram user ID
```

The remaining values have sensible defaults for most deployments. See [Environment Variables](#-environment-variables) for the full table.

---

## 🖥️ Deployment

### Linux / Ubuntu (systemd)

#### Prerequisites

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3 python3-pip python3-venv ffmpeg git
```

#### Install

```bash
git clone https://github.com/Alaa91H/islamic-unified-bot.git /opt/islamic-unified-bot
cd /opt/islamic-unified-bot
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
cp .env.example .env && nano .env
```

#### Create systemd service

```bash
sudo tee /etc/systemd/system/islamic-bot.service > /dev/null << 'EOF'
[Unit]
Description=Islamic Unified Telegram Bot
After=network.target
Wants=network-online.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/opt/islamic-unified-bot
EnvironmentFile=/opt/islamic-unified-bot/.env
ExecStart=/opt/islamic-unified-bot/venv/bin/python main.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=islamic-bot

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable --now islamic-bot
sudo systemctl status islamic-bot
```

#### Useful commands

```bash
# View live logs
sudo journalctl -u islamic-bot -f

# Restart after a config change
sudo systemctl restart islamic-bot

# Stop the bot
sudo systemctl stop islamic-bot
```

---

### Docker

```bash
# Build
docker build -t islamic-unified-bot .

# Run (pass your .env file directly)
docker run -d \
  --name islamic-bot \
  --env-file .env \
  --restart unless-stopped \
  -v $(pwd)/logs:/app/logs \
  -v $(pwd)/azan_data:/app/azan_data \
  islamic-unified-bot
```

With Docker Compose:

```yaml
# docker-compose.yml
services:
  islamic-bot:
    build: .
    restart: unless-stopped
    env_file: .env
    volumes:
      - ./logs:/app/logs
      - ./azan_data:/app/azan_data
```

```bash
docker compose up -d
docker compose logs -f
```

---

## 🔄 CI/CD Pipeline

The pipeline runs on every push to `main` / `develop` and on every pull request targeting `main`.

```
push / PR
    │
    ├─ 🔍 Lint        black, isort, flake8, pylint
    ├─ 🔒 Security    bandit, safety, pip-audit, detect-secrets
    ├─ 🧪 Tests       pytest on Python 3.10 / 3.11 / 3.12 + Codecov
    │        ↓
    ├─ 💨 Smoke Test  import checks, prayer-time smoke, data integrity
    │        ↓
    ├─ 📦 Build       generate version.py, create release archive
    │        ↓
    └─ 🚀 Deploy      SSH → git pull → pip install → systemctl restart
                      (main branch only, requires production environment approval)
```

### Required secrets

| Secret | Description |
|--------|-------------|
| `BOT_TOKEN` | Telegram Bot token |
| `API_ID` | Telegram API ID |
| `API_HASH` | Telegram API Hash |
| `OWNER_ID` | Bot owner's Telegram user ID |
| `SSH_PRIVATE_KEY` | Private key for the production server |
| `SERVER_HOST` | Production server hostname / IP |
| `SSH_USER` | SSH username on the server |
| `SSH_PORT` | SSH port (default: `22`) |
| `DEPLOY_PATH` | Deployment directory on the server |

### Dependabot auto-merge

Dependabot opens weekly PRs for outdated dependencies. The **auto-merge workflow** handles them automatically:

- **patch** and **minor** updates → approved and set to auto-merge (fires once CI passes)
- **major** updates → labelled `needs-review` and a comment is posted requesting manual review

---

## 🧪 Testing

```bash
# Install test dependencies
pip install pytest pytest-asyncio pytest-cov pytest-timeout pytest-mock aioresponses freezegun

# Run all tests
pytest

# With coverage report
pytest --cov=. --cov-report=html
open htmlcov/index.html

# Run a specific test file
pytest tests/test_prayer_times.py -v

# Run only unit tests
pytest -m unit
```

Test coverage threshold is enforced at **75 %** in CI.

---

## 🗂️ Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `BOT_TOKEN` | — | **Required.** Telegram Bot token from @BotFather |
| `API_ID` | — | **Required.** Telegram API ID from my.telegram.org |
| `API_HASH` | — | **Required.** Telegram API Hash from my.telegram.org |
| `OWNER_ID` | — | **Required.** Your numeric Telegram user ID |
| `MUSIC_DIR` | `./music` | Directory for locally stored audio files |
| `AZAN_DATA_DIR` | `./azan_data` | Directory for Azan audio cache |
| `QURAN_STREAM_URL` | `https://quran.kalamullah.com/mp3/afs/` | Base URL for Quran audio files |
| `MAX_RECONNECT_ATTEMPTS` | `10` | How many times to retry on disconnect |
| `INITIAL_RECONNECT_DELAY` | `5` | Initial back-off delay (seconds) |
| `DEFAULT_CALCULATION_METHOD` | `isna` | Prayer-time calculation method |
| `DEFAULT_ASR_METHOD` | `standard` | Asr calculation method (`standard` / `hanafi`) |
| `DEFAULT_CITY` | `مكة المكرمة` | Fallback city for prayer times |
| `DEFAULT_TIMEZONE` | `3` | UTC offset for the default city |
| `NOTIFICATIONS_ENABLED` | `true` | Enable/disable push notifications |
| `PRELUDE_ENABLED` | `false` | Play a prelude before Azan |
| `PRELUDE_TIME` | `5` | Pre-Azan lead time in minutes |
| `STREAM_ENABLED` | `false` | Enable Quran streaming |
| `DEFAULT_AZAN_SOURCE` | `traditional` | Azan audio source key |
| `STREAM_STOP_BEFORE` | `0` | Stop stream N minutes before next prayer |
| `DEFAULT_STREAM_DURATION` | `120` | Maximum stream duration (minutes) |
| `DB_TYPE` | `sqlite` | Database backend (`sqlite`) |
| `SAFE_MODE` | `true` | Restrict bot to owner only during setup |
| `LOG_SENSITIVE_DATA` | `false` | Include sensitive data in logs |
| `REQUEST_TIMEOUT` | `10` | HTTP request timeout (seconds) |
| `MAX_RETRIES` | `3` | HTTP retry count |
| `DEBUG_MODE` | `false` | Enable verbose debug logging |
| `LOG_LEVEL` | `INFO` | Logging level (`DEBUG` / `INFO` / `WARNING` / `ERROR`) |

---

## 🤝 Contributing

Contributions are welcome and appreciated!

1. Fork the repository
2. Create a feature branch: `git checkout -b feat/my-new-feature`
3. Write your changes and add tests where applicable
4. Ensure the full test suite passes: `pytest`
5. Ensure code style is correct: `black . && isort .`
6. Commit with a conventional commit message: `git commit -m "feat: add xyz"`
7. Push and open a Pull Request against `main`

Please open an issue first for large changes so we can discuss the approach.

### Commit message convention

We follow [Conventional Commits](https://www.conventionalcommits.org/):

```
feat:      new feature
fix:       bug fix
chore:     maintenance / dependency update
docs:      documentation only
test:      adding or fixing tests
refactor:  code change with no behaviour change
ci:        changes to CI/CD configuration
```

---

## 🔒 Security

- **Never commit** `.env`, `*.session`, or any token/key files. They are in `.gitignore`.
- The CI pipeline runs `bandit`, `safety`, `pip-audit`, and `detect-secrets` on every push.
- Secrets are stored exclusively in GitHub Actions secrets — never in source code.
- If you discover a security vulnerability, please open a **private** security advisory via GitHub rather than a public issue.

---

## 📄 License

This project is released under the [MIT License](LICENSE).

---

<div align="center">

Made with ❤️ for the Muslim community worldwide.

**بارك الله فيكم**

</div>
