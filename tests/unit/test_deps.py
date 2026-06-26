import pytest
from unittest.mock import AsyncMock, MagicMock


@pytest.mark.asyncio
async def test_build_dependencies_wires_all_components(monkeypatch, tmp_path):
    from bot.config import Settings
    from bot.deps import build_dependencies, Dependencies

    monkeypatch.setenv("DB_PATH", str(tmp_path / "t.db"))
    s = Settings(
        bot_token="1:ABC", api_id=1, api_hash="h", owner_id=1,
        db_path=str(tmp_path / "t.db"),
    )

    app = MagicMock()
    # stream_factory وهمي لتفادي استيراد pytgcalls
    fake_stream = MagicMock()
    fake_stream.stop_all = AsyncMock()
    deps = await build_dependencies(
        s, app, stream_factory=lambda a: fake_stream
    )
    assert isinstance(deps, Dependencies)
    assert deps.stream_manager is fake_stream
    assert deps.notifier is not None
    assert deps.scheduler is not None
    assert deps.user_repo is not None
    await deps.db.close()


@pytest.mark.asyncio
async def test_shutdown_dependencies_is_safe_on_errors(tmp_path):
    from bot.config import Settings
    from bot.deps import build_dependencies, shutdown_dependencies

    s = Settings(
        bot_token="1:ABC", api_id=1, api_hash="h", owner_id=1,
        db_path=str(tmp_path / "t.db"),
    )
    app = MagicMock()
    fake_stream = MagicMock()
    fake_stream.stop_all = AsyncMock(side_effect=RuntimeError("boom"))
    deps = await build_dependencies(
        s, app, stream_factory=lambda a: fake_stream
    )
    # يجب ألا يرفع رغم فشل إيقاف البث
    await shutdown_dependencies(deps)
