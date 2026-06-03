import os
import sys
import tempfile
from unittest.mock import AsyncMock, MagicMock

import pytest

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ============================================================
# Environment fixture — set safe test env vars
# ============================================================


@pytest.fixture(autouse=True)
def safe_env(monkeypatch):
    monkeypatch.setenv("BOT_TOKEN", "1234567890:ABCDefghijklmnopqrstuvwxyz_test_token")
    monkeypatch.setenv("API_ID", "12345678")
    monkeypatch.setenv("API_HASH", "test_api_hash_value_not_real")
    monkeypatch.setenv("OWNER_ID", "123456789")
    monkeypatch.setenv("MUSIC_DIR", tempfile.mkdtemp())
    monkeypatch.setenv("AZAN_DATA_DIR", tempfile.mkdtemp())
    monkeypatch.setenv("LOG_LEVEL", "ERROR")


# ============================================================
# Mock Pyrogram Client
# ============================================================


@pytest.fixture
def mock_client():
    client = MagicMock()
    client.send_message = AsyncMock()
    client.edit_message_text = AsyncMock()
    return client


# ============================================================
# Mock Message
# ============================================================


@pytest.fixture
def mock_message():
    msg = MagicMock()
    msg.from_user = MagicMock()
    msg.from_user.id = 123456789
    msg.from_user.first_name = "Test"
    msg.chat = MagicMock()
    msg.chat.id = -1001234567890
    msg.reply_text = AsyncMock()
    msg.command = ["start"]
    return msg


# ============================================================
# Mock CallbackQuery
# ============================================================


@pytest.fixture
def mock_callback():
    cq = MagicMock()
    cq.from_user = MagicMock()
    cq.from_user.id = 123456789
    cq.data = "test_data"
    cq.message = MagicMock()
    cq.message.edit_text = AsyncMock()
    cq.answer = AsyncMock()
    return cq


# ============================================================
# Temp data directory
# ============================================================


@pytest.fixture
def temp_dir():
    return tempfile.mkdtemp()


# ============================================================
# AzanScheduler with isolated temp dir
# ============================================================


@pytest.fixture
def scheduler(temp_dir):
    from azan_manager import AzanScheduler

    return AzanScheduler(data_dir=temp_dir)
