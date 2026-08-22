import pytest


@pytest.mark.asyncio
async def test_adhkar_partial_update_accepts_only_valid_whitelisted_fields(tmp_path):
    from bot.db.connection import Database
    from bot.db.repositories.adhkar_settings import AdhkarSettings, AdhkarSettingsRepo

    db = Database(str(tmp_path / "adhkar.db"))
    await db.connect()
    repo = AdhkarSettingsRepo(db)
    await repo.upsert(AdhkarSettings(chat_id=11))

    await repo.update_partial(11, interval_minutes=30, morning_time="05:45")
    updated = await repo.get(11)
    assert updated is not None
    assert updated.interval_minutes == 30
    assert updated.morning_time == "05:45"

    with pytest.raises(ValueError, match="غير معروفة"):
        await repo.update_partial(11, injected_column="bad")
    with pytest.raises(ValueError, match="بين 1 و1440"):
        await repo.update_partial(11, interval_minutes=0)
    with pytest.raises(ValueError, match="HH:MM"):
        await repo.update_partial(11, evening_time="25:90")

    await db.close()
