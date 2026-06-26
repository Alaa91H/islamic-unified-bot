import logging


def test_setup_logging_creates_log_dir(tmp_path):
    from bot.logging_setup import setup_logging

    log_dir = tmp_path / "logs"
    logger = setup_logging(log_level="INFO", log_dir=str(log_dir), json_format=False)

    assert log_dir.exists()
    assert isinstance(logger, logging.Logger)
    assert logger.level == logging.INFO


def test_setup_logging_respects_level(tmp_path):
    from bot.logging_setup import setup_logging

    logger = setup_logging(log_level="DEBUG", log_dir=str(tmp_path), json_format=False)
    assert logger.level == logging.DEBUG


def test_setup_logging_json_format(tmp_path):
    from bot.logging_setup import setup_logging

    logger = setup_logging(log_level="INFO", log_dir=str(tmp_path), json_format=True)
    assert logger.level == logging.INFO


def test_setup_logging_is_idempotent(tmp_path):
    """تكرار الاستدعاء لا يضيف handlers مكررة."""
    from bot.logging_setup import setup_logging

    setup_logging(log_dir=str(tmp_path))
    setup_logging(log_dir=str(tmp_path))
    root = logging.getLogger()
    # file + console only (not duplicated)
    assert len(root.handlers) == 2
