import sqlite3

import pytest


@pytest.mark.asyncio
async def test_database_creates_schema_and_is_idempotent(tmp_path):
    from bot.db.connection import Database

    db = Database(str(tmp_path / "test.db"))
    await db.connect()

    # الجداول موجودة
    rows = await db.fetchall("SELECT name FROM sqlite_master WHERE type='table'")
    tables = {row[0] for row in rows}
    assert {
        "user_settings",
        "group_settings",
        "sent_notifications",
        "schema_version",
    } <= tables

    # idempotent: التشغيل ثانيةً لا يُخطئ ولا يكرّر
    await db.apply_migrations()
    versions = await db.fetchall("SELECT version FROM schema_version")
    assert [r[0] for r in versions] == [1, 2, 3, 4]

    columns = await db.fetchall("PRAGMA table_info(sent_notifications)")
    column_names = {column[1] for column in columns}
    assert {"status", "claimed_at", "attempts", "last_error"} <= column_names

    today = "2026-07-02"
    await db.execute(
        """INSERT INTO sent_notifications
        (target_id, target_type, prayer, prayer_date)
        VALUES (?, ?, ?, ?)""",
        (1, "user", "fajr", today),
    )
    await db.execute(
        """INSERT INTO sent_notifications
        (target_id, target_type, prayer, prayer_date)
        VALUES (?, ?, ?, ?)""",
        (1, "group", "fajr", today),
    )
    with pytest.raises(sqlite3.IntegrityError):
        await db.execute(
            """INSERT INTO sent_notifications
            (target_id, target_type, prayer, prayer_date)
            VALUES (?, ?, ?, ?)""",
            (1, "user", "fajr", today),
        )

    await db.close()


@pytest.mark.asyncio
async def test_database_pragmas_set(tmp_path):
    from bot.db.connection import Database

    db = Database(str(tmp_path / "t.db"))
    await db.connect()
    row = await db.fetchone("PRAGMA journal_mode")
    assert row[0].lower() == "wal"
    await db.close()


@pytest.mark.asyncio
async def test_database_creates_parent_dir(tmp_path):
    from bot.db.connection import Database

    nested = tmp_path / "nested" / "deep" / "bot.db"
    db = Database(str(nested))
    await db.connect()
    assert nested.exists()
    await db.close()


@pytest.mark.asyncio
async def test_fetchone_returns_none_when_empty(tmp_path):
    from bot.db.connection import Database

    db = Database(str(tmp_path / "t.db"))
    await db.connect()
    assert (
        await db.fetchone("SELECT * FROM user_settings WHERE user_id = ?", (1,)) is None
    )
    await db.close()
