import json
import pytest


@pytest.mark.asyncio
async def test_migrate_imports_existing_users(tmp_path):
    from bot.db.connection import Database
    from bot.db.migrate_from_json import migrate_from_json
    from bot.db.repositories.user_settings import UserSettingsRepo

    json_path = tmp_path / "user_settings.json"
    json_path.write_text(
        json.dumps(
            {
                "111": {
                    "user_id": 111, "city": "مكة المكرمة", "method": "makkah",
                    "timezone": 3, "asr_method": "standard",
                },
                "222": {
                    "user_id": 222, "city": "القاهرة", "method": "egypt",
                    "timezone": 2, "asr_method": "standard",
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    db = Database(str(tmp_path / "t.db"))
    await db.connect()
    repo = UserSettingsRepo(db)

    imported = await migrate_from_json(json_path, repo)

    assert imported == 2
    g1 = await repo.get(111)
    assert g1 is not None
    assert g1.city == "مكة المكرمة"
    assert g1.method == "makkah"
    await db.close()
    # نسخة احتياطية أُنشئت
    assert (tmp_path / "user_settings.json.bak").exists()


@pytest.mark.asyncio
async def test_migrate_no_file_returns_zero(tmp_path):
    from bot.db.connection import Database
    from bot.db.migrate_from_json import migrate_from_json
    from bot.db.repositories.user_settings import UserSettingsRepo

    db = Database(str(tmp_path / "t.db"))
    await db.connect()
    imported = await migrate_from_json(
        tmp_path / "missing.json", UserSettingsRepo(db)
    )
    assert imported == 0
    await db.close()


@pytest.mark.asyncio
async def test_migrate_corrupt_json_returns_zero(tmp_path):
    from bot.db.connection import Database
    from bot.db.migrate_from_json import migrate_from_json
    from bot.db.repositories.user_settings import UserSettingsRepo

    bad = tmp_path / "user_settings.json"
    bad.write_text("{ this is not valid json", encoding="utf-8")

    db = Database(str(tmp_path / "t.db"))
    await db.connect()
    imported = await migrate_from_json(bad, UserSettingsRepo(db))
    assert imported == 0
    await db.close()


@pytest.mark.asyncio
async def test_migrate_skips_invalid_records_continues(tmp_path):
    from bot.db.connection import Database
    from bot.db.migrate_from_json import migrate_from_json
    from bot.db.repositories.user_settings import UserSettingsRepo

    json_path = tmp_path / "user_settings.json"
    json_path.write_text(
        json.dumps(
            {
                "5": {
                    "user_id": 5, "city": "جدة", "method": "isna", "timezone": 3,
                },
                "bad": {"city": "x"},
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    db = Database(str(tmp_path / "t.db"))
    await db.connect()
    repo = UserSettingsRepo(db)
    imported = await migrate_from_json(json_path, repo)
    assert imported == 1
    assert await repo.get(5) is not None
    await db.close()


@pytest.mark.asyncio
async def test_migrate_preserves_notification_flags(tmp_path):
    from bot.db.connection import Database
    from bot.db.migrate_from_json import migrate_from_json
    from bot.db.repositories.user_settings import UserSettingsRepo

    json_path = tmp_path / "user_settings.json"
    json_path.write_text(
        json.dumps(
            {
                "1": {
                    "user_id": 1, "city": "مكة المكرمة", "timezone": 3,
                    "notification_enabled": False, "prelude_enabled": True,
                    "prelude_time": 15,
                }
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    db = Database(str(tmp_path / "t.db"))
    await db.connect()
    repo = UserSettingsRepo(db)
    await migrate_from_json(json_path, repo)
    s = await repo.get(1)
    assert s is not None
    assert s.notifications_on is False
    assert s.prelude_on is True
    assert s.prelude_minutes == 15
    await db.close()
