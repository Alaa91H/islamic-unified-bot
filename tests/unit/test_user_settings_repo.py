import pytest


@pytest.fixture
async def repo(tmp_path):
    from bot.db.connection import Database
    from bot.db.repositories.user_settings import UserSettingsRepo

    db = Database(str(tmp_path / "t.db"))
    await db.connect()
    yield UserSettingsRepo(db)
    await db.close()


@pytest.mark.asyncio
async def test_get_missing_returns_none(repo):
    assert await repo.get(123) is None


@pytest.mark.asyncio
async def test_upsert_then_get(repo):
    from bot.db.repositories.user_settings import UserSettings

    s = UserSettings(
        user_id=1, city="مكة المكرمة", method="isna",
        asr_method="standard", timezone=3,
    )
    await repo.upsert(s)
    got = await repo.get(1)
    assert got is not None
    assert got.city == "مكة المكرمة"
    assert got.notifications_on is True
    assert got.enabled_prayers == ["fajr", "dhuhr", "asr", "maghrib", "isha"]


@pytest.mark.asyncio
async def test_list_with_notifications_filters(repo):
    from bot.db.repositories.user_settings import UserSettings

    await repo.upsert(UserSettings(user_id=1, city="مكة المكرمة", timezone=3,
                                   notifications_on=True))
    await repo.upsert(UserSettings(user_id=2, city="القاهرة", timezone=2,
                                   notifications_on=False))
    rows = await repo.list_with_notifications()
    assert {r.user_id for r in rows} == {1}


@pytest.mark.asyncio
async def test_upsert_is_an_update(repo):
    from bot.db.repositories.user_settings import UserSettings

    await repo.upsert(UserSettings(user_id=1, city="مكة المكرمة", timezone=3))
    await repo.upsert(UserSettings(user_id=1, city="جدة", timezone=3,
                                  notifications_on=False))
    got = await repo.get(1)
    assert got.city == "جدة"
    assert got.notifications_on is False


@pytest.mark.asyncio
async def test_update_partial_changes_one_field(repo):
    from bot.db.repositories.user_settings import UserSettings

    await repo.upsert(UserSettings(user_id=1, city="مكة المكرمة", timezone=3))
    await repo.update_partial(1, notifications_on=False, prelude_minutes=10)
    got = await repo.get(1)
    assert got.notifications_on is False
    assert got.prelude_minutes == 10
    assert got.city == "مكة المكرمة"  # unchanged


@pytest.mark.asyncio
async def test_update_partial_rejects_unknown_field(repo):
    from bot.db.repositories.user_settings import UserSettings

    await repo.upsert(UserSettings(user_id=1, city="مكة المكرمة", timezone=3))
    with pytest.raises(ValueError, match="حقول غير معروفة"):
        await repo.update_partial(1, nonexistent_field=123)


@pytest.mark.asyncio
async def test_update_partial_serializes_prayers_as_json(repo):
    from bot.db.repositories.user_settings import UserSettings

    await repo.upsert(UserSettings(user_id=1, city="مكة المكرمة", timezone=3))
    await repo.update_partial(1, enabled_prayers=["fajr", "isha"])
    got = await repo.get(1)
    assert got.enabled_prayers == ["fajr", "isha"]


@pytest.mark.asyncio
async def test_invalid_enabled_prayers_falls_back_to_default(repo):
    from bot.db.connection import Database

    # نُدخل JSON تالف مباشرة للتأكد من المرونة
    db = repo._db
    await db.execute(
        """INSERT INTO user_settings (user_id, city, enabled_prayers)
           VALUES (5, 'test', 'not-json')"""
    )
    got = await repo.get(5)
    assert got is not None
    assert got.enabled_prayers == ["fajr", "dhuhr", "asr", "maghrib", "isha"]
