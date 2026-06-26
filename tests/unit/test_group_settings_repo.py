import pytest


@pytest.fixture
async def repo(tmp_path):
    from bot.db.connection import Database
    from bot.db.repositories.group_settings import GroupSettingsRepo

    db = Database(str(tmp_path / "t.db"))
    await db.connect()
    yield GroupSettingsRepo(db)
    await db.close()


@pytest.mark.asyncio
async def test_get_missing_returns_none(repo):
    assert await repo.get(-100999) is None


@pytest.mark.asyncio
async def test_upsert_and_get(repo):
    from bot.db.repositories.group_settings import GroupSettings

    g = GroupSettings(chat_id=-100123, city="مكة المكرمة")
    await repo.upsert(g)
    got = await repo.get(-100123)
    assert got is not None
    assert got.city == "مكة المكرمة"
    assert got.azan_source == "traditional"
    assert got.stream_quran_on is False


@pytest.mark.asyncio
async def test_list_all(repo):
    from bot.db.repositories.group_settings import GroupSettings

    await repo.upsert(GroupSettings(chat_id=-1, city="جدة"))
    await repo.upsert(GroupSettings(chat_id=-2, city="الرياض"))
    rows = await repo.list_all()
    assert {r.chat_id for r in rows} == {-1, -2}


@pytest.mark.asyncio
async def test_upsert_is_update(repo):
    from bot.db.repositories.group_settings import GroupSettings

    await repo.upsert(GroupSettings(chat_id=-1, city="جدة"))
    await repo.upsert(GroupSettings(chat_id=-1, city="مكة المكرمة",
                                   azan_source="abdul_basit"))
    got = await repo.get(-1)
    assert got.city == "مكة المكرمة"
    assert got.azan_source == "abdul_basit"


@pytest.mark.asyncio
async def test_delete(repo):
    from bot.db.repositories.group_settings import GroupSettings

    await repo.upsert(GroupSettings(chat_id=-5, city="جدة"))
    await repo.delete(-5)
    assert await repo.get(-5) is None


@pytest.mark.asyncio
async def test_linked_user_persists(repo):
    from bot.db.repositories.group_settings import GroupSettings

    await repo.upsert(GroupSettings(chat_id=-7, city="جدة", linked_user_id=42))
    got = await repo.get(-7)
    assert got.linked_user_id == 42
