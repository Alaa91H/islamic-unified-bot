import pytest


@pytest.mark.asyncio
async def test_database_creates_schema_and_is_idempotent(tmp_path):
    from bot.db.connection import Database

    db = Database(str(tmp_path / "test.db"))
    await db.connect()

    # الجداول موجودة
    rows = await db.fetchall(
        "SELECT name FROM sqlite_master WHERE type='table'"
    )
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
    assert [r[0] for r in versions] == [1, 2]

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
    assert await db.fetchone("SELECT * FROM user_settings WHERE user_id = ?", (1,)) is None
    await db.close()
