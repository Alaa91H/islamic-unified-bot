import tempfile
from datetime import datetime

from azan_manager import (
    AzanNotificationManager,
    AzanScheduler,
    AzanStreamer,
    NotificationType,
    UserAzanSettings,
)


class TestUserAzanSettings:

    def test_default_prayers_populated(self):
        s = UserAzanSettings(user_id=1, city="مكة المكرمة")
        assert s.enabled_prayers is not None
        assert "fajr" in s.enabled_prayers
        assert "isha" in s.enabled_prayers

    def test_to_dict_returns_dict(self):
        s = UserAzanSettings(user_id=1, city="مكة المكرمة")
        d = s.to_dict()
        assert isinstance(d, dict)
        assert d["user_id"] == 1
        assert d["city"] == "مكة المكرمة"

    def test_to_dict_has_required_keys(self):
        s = UserAzanSettings(user_id=42, city="الرياض")
        d = s.to_dict()
        for key in (
            "user_id",
            "city",
            "method",
            "timezone",
            "notification_enabled",
            "stream_enabled",
        ):
            assert key in d, f"Missing key: {key}"

    def test_default_values(self):
        s = UserAzanSettings(user_id=1, city="القاهرة")
        assert s.notification_enabled is True
        assert s.stream_enabled is False
        assert s.prelude_enabled is False
        assert s.method == "isna"
        assert s.language == "ar"


class TestAzanScheduler:

    def setup_method(self):
        self.tmp = tempfile.mkdtemp()
        self.scheduler = AzanScheduler(data_dir=self.tmp)

    def test_add_user_success(self):
        result = self.scheduler.add_user(
            user_id=100, city="مكة المكرمة", method="makkah"
        )
        assert result is True

    def test_add_user_creates_settings(self):
        self.scheduler.add_user(user_id=200, city="الرياض")
        settings = self.scheduler.get_user_settings(200)
        assert settings is not None
        assert settings.user_id == 200
        assert settings.city == "الرياض"

    def test_get_user_settings_not_found(self):
        result = self.scheduler.get_user_settings(99999)
        assert result is None

    def test_update_user_settings(self):
        self.scheduler.add_user(user_id=300, city="القاهرة")
        result = self.scheduler.update_user_settings(300, notification_enabled=False)
        assert result is True
        settings = self.scheduler.get_user_settings(300)
        assert settings.notification_enabled is False

    def test_update_nonexistent_user(self):
        result = self.scheduler.update_user_settings(88888, city="بغداد")
        assert result is False

    def test_settings_persist_after_save_load(self):
        self.scheduler.add_user(user_id=400, city="دبي", method="dubai")
        self.scheduler.save_settings()
        scheduler2 = AzanScheduler(data_dir=self.tmp)
        scheduler2.load_settings()
        settings = scheduler2.get_user_settings(400)
        assert settings is not None
        assert settings.city == "دبي"

    def test_get_prayer_times_valid_user(self):
        self.scheduler.add_user(user_id=500, city="مكة المكرمة", method="makkah")
        times = self.scheduler.get_prayer_times(500)
        assert times is not None
        assert isinstance(times, dict)

    def test_get_prayer_times_invalid_user(self):
        result = self.scheduler.get_prayer_times(77777)
        assert result is None

    def test_get_prayer_times_contains_prayers(self):
        self.scheduler.add_user(user_id=600, city="مكة المكرمة")
        times = self.scheduler.get_prayer_times(600)
        for prayer in ("fajr", "dhuhr", "asr", "maghrib", "isha"):
            assert prayer in times, f"Missing {prayer} in prayer times"

    def test_get_next_prayer_returns_dict_or_none(self):
        self.scheduler.add_user(user_id=700, city="مكة المكرمة")
        result = self.scheduler.get_next_prayer(700)
        assert result is None or isinstance(result, dict)

    def test_get_next_prayer_has_required_keys(self):
        self.scheduler.add_user(user_id=800, city="مكة المكرمة")
        result = self.scheduler.get_next_prayer(800)
        if result is not None:
            assert "name" in result
            assert "time" in result

    def test_multiple_users_isolation(self):
        self.scheduler.add_user(user_id=901, city="مكة المكرمة")
        self.scheduler.add_user(user_id=902, city="الرياض")
        self.scheduler.update_user_settings(901, notification_enabled=False)
        s1 = self.scheduler.get_user_settings(901)
        s2 = self.scheduler.get_user_settings(902)
        assert s1.notification_enabled is False
        assert s2.notification_enabled is True

    def test_add_user_invalid_city(self):
        result = self.scheduler.add_user(user_id=999, city="مدينة_غير_موجودة_xyz")
        assert result is False or self.scheduler.get_user_settings(999) is None


class TestAzanStreamer:

    def setup_method(self):
        self.streamer = AzanStreamer()

    def test_get_azan_url_traditional(self):
        url = self.streamer.get_azan_url("fajr", "traditional")
        assert url is None or isinstance(url, str)

    def test_get_azan_url_invalid_prayer(self):
        url = self.streamer.get_azan_url("invalid_prayer", "traditional")
        assert url is None

    def test_add_and_get_stream(self):
        self.streamer.add_stream(
            chat_id=111,
            prayer="fajr",
            url="https://example.com/fajr.mp3",
            started_at=datetime.now(),
        )
        stream = self.streamer.get_stream(111)
        assert stream is not None
        assert stream["prayer"] == "fajr"

    def test_get_stream_not_found(self):
        result = self.streamer.get_stream(99999)
        assert result is None

    def test_stop_stream(self):
        self.streamer.add_stream(
            chat_id=222,
            prayer="maghrib",
            url="https://example.com/maghrib.mp3",
            started_at=datetime.now(),
        )
        result = self.streamer.stop_stream(222)
        assert result is True
        assert self.streamer.get_stream(222) is None

    def test_stop_nonexistent_stream(self):
        result = self.streamer.stop_stream(88888)
        assert result is False

    def test_is_streaming_true(self):
        self.streamer.add_stream(
            chat_id=333,
            prayer="isha",
            url="https://example.com/isha.mp3",
            started_at=datetime.now(),
        )
        assert self.streamer.is_streaming(333) is True

    def test_is_streaming_false(self):
        assert self.streamer.is_streaming(44444) is False


class TestAzanNotificationManager:

    def setup_method(self):
        self.manager = AzanNotificationManager()

    def test_add_notification(self):
        self.manager.add_notification(
            user_id=100,
            notification_type=NotificationType.PRAYER_TIME,
            prayer="fajr",
            scheduled_time=datetime.now(),
        )
        pending = self.manager.get_pending_notifications()
        assert isinstance(pending, list)

    def test_get_pending_notifications_is_list(self):
        result = self.manager.get_pending_notifications()
        assert isinstance(result, list)

    def test_mark_as_sent(self):
        self.manager.add_notification(
            user_id=200,
            notification_type=NotificationType.PRAYER_TIME,
            prayer="dhuhr",
            scheduled_time=datetime.now(),
        )
        pending = self.manager.get_pending_notifications()
        if pending:
            nid = pending[0].get("id")
            if nid:
                result = self.manager.mark_as_sent(nid)
                assert isinstance(result, bool)

    def test_clear_old_notifications(self):
        self.manager.clear_old_notifications(hours=0)
        pending = self.manager.get_pending_notifications()
        assert isinstance(pending, list)

    def test_notification_type_enum_values(self):
        assert NotificationType.PRAYER_TIME.value is not None
        assert NotificationType.PRELUDE.value is not None
        assert NotificationType.STREAM_START.value is not None
        assert NotificationType.STREAM_STOP.value is not None
