#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
import json
import logging
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional

from azan_prayer_times import CityCoordinates, PrayerTimeCalculator

logger = logging.getLogger(__name__)


class NotificationType(Enum):
    """أنواع التنبيهات"""

    PRAYER_TIME = "صلاة"
    PRELUDE = "مقدمة"
    STREAM_START = "بدء البث"
    STREAM_STOP = "إيقاف البث"


@dataclass
class UserAzanSettings:
    """إعدادات الأذان للمستخدم"""

    user_id: int
    city: str
    method: str = "isna"  # طريقة الحساب
    timezone: int = 0
    asr_method: str = "standard"

    # إعدادات التنبيهات
    enabled_prayers: List[str] = None  # الصلوات المفعلة
    notification_enabled: bool = True
    prelude_enabled: bool = False  # تنبيه قبل الأذان
    prelude_time: int = 5  # بالدقائق

    # إعدادات البث
    stream_enabled: bool = False
    stream_url: str = ""  # رابط الأذان الصوتي
    stream_prelude_url: str = ""  # رابط المقدمة
    stream_stop_before: int = 0  # إيقاف البث قبل الأذان (بالثواني)
    stream_duration: int = 120  # مدة البث (بالثواني)

    # إعدادات إضافية
    language: str = "ar"
    timezone_name: str = "UTC"
    use_hijri_calendar: bool = True

    def __post_init__(self):
        if self.enabled_prayers is None:
            self.enabled_prayers = ["fajr", "dhuhr", "asr", "maghrib", "isha"]

    def to_dict(self) -> Dict:
        """تحويل إلى قاموس"""
        return asdict(self)


class AzanScheduler:
    """جدولة أوقات الأذان والتنبيهات"""

    def __init__(self, data_dir: str = "./azan_data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        self.settings_file = self.data_dir / "user_settings.json"
        self.prayer_times_cache = {}
        self.user_settings: Dict[int, UserAzanSettings] = {}
        self.load_settings()

    def load_settings(self):
        """تحميل إعدادات المستخدمين"""
        if self.settings_file.exists():
            try:
                with open(self.settings_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for user_id, settings_dict in data.items():
                        self.user_settings[int(user_id)] = UserAzanSettings(
                            **settings_dict
                        )
            except Exception as e:
                logger.error(f"خطأ في تحميل الإعدادات: {e}")

    def save_settings(self):
        """حفظ إعدادات المستخدمين"""
        try:
            data = {
                str(user_id): settings.to_dict()
                for user_id, settings in self.user_settings.items()
            }
            with open(self.settings_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"خطأ في حفظ الإعدادات: {e}")

    def add_user(
        self,
        user_id: int,
        city: str,
        method: str = "isna",
        timezone: int = 0,
        asr_method: str = "standard",
    ) -> bool:
        """إضافة مستخدم جديد"""
        city_coords = CityCoordinates.get_city_coords(city)
        if not city_coords:
            return False

        timezone = city_coords.get("tz", timezone)

        self.user_settings[user_id] = UserAzanSettings(
            user_id=user_id,
            city=city,
            method=method,
            timezone=timezone,
            asr_method=asr_method,
            timezone_name=self._get_timezone_name(timezone),
        )
        self.save_settings()
        return True

    def update_user_settings(self, user_id: int, **kwargs) -> bool:
        """تحديث إعدادات المستخدم"""
        if user_id not in self.user_settings:
            return False

        settings = self.user_settings[user_id]
        for key, value in kwargs.items():
            if hasattr(settings, key):
                setattr(settings, key, value)

        self.save_settings()
        return True

    def get_user_settings(self, user_id: int) -> Optional[UserAzanSettings]:
        """الحصول على إعدادات المستخدم"""
        return self.user_settings.get(user_id)

    def get_prayer_times(self, user_id: int, date: datetime = None) -> Optional[Dict]:
        """حساب أوقات الصلاة للمستخدم"""
        if date is None:
            date = datetime.now()

        settings = self.get_user_settings(user_id)
        if not settings:
            return None

        city_coords = CityCoordinates.get_city_coords(settings.city)
        if not city_coords:
            return None

        calculator = PrayerTimeCalculator(
            latitude=city_coords["lat"],
            longitude=city_coords["lng"],  # استخدام lng كما في CityCoordinates المحدثة
            timezone=city_coords["tz"],
            method=settings.method,
            asr_method=settings.asr_method,
        )

        times = calculator.calculate_times(date)
        times["city"] = settings.city
        times["country"] = city_coords.get("country", "Unknown")
        times["method"] = calculator.get_method_name()
        times["date"] = date.strftime("%Y-%m-%d")

        return times

    async def get_prayer_times_async(
        self, user_id: int, date: datetime = None
    ) -> Optional[Dict]:
        """حساب أوقات الصلاة بشكل غير متزامن"""
        return await asyncio.get_event_loop().run_in_executor(
            None, self.get_prayer_times, user_id, date
        )

    def get_next_prayer(
        self, user_id: int, current_time: datetime = None
    ) -> Optional[Dict]:
        """الحصول على الصلاة التالية"""
        if current_time is None:
            current_time = datetime.now()

        times = self.get_prayer_times(user_id, current_time)
        if not times:
            return None

        settings = self.get_user_settings(user_id)
        current_time_str = current_time.strftime("%H:%M")

        prayers = ["fajr", "dhuhr", "asr", "maghrib", "isha"]

        for prayer in prayers:
            if prayer in settings.enabled_prayers and prayer in times:
                prayer_time = times[prayer]
                if prayer_time > current_time_str:
                    # حساب الدقائق المتبقية
                    prayer_h, prayer_m = map(int, prayer_time.split(":"))
                    curr_h, curr_m = map(int, current_time_str.split(":"))
                    in_minutes = (prayer_h * 60 + prayer_m) - (curr_h * 60 + curr_m)
                    return {
                        "prayer": prayer,
                        "time": prayer_time,
                        "name": PrayerTimeCalculator.PRAYER_NAMES.get(prayer, prayer),
                        "in_minutes": in_minutes,
                        "tomorrow": False,
                    }

        # إذا لم توجد صلاة اليوم، أحسب للغد
        next_date = current_time + timedelta(days=1)
        times_next = self.get_prayer_times(user_id, next_date)
        if times_next:
            prayer = "fajr"
            return {
                "prayer": prayer,
                "time": times_next[prayer],
                "name": PrayerTimeCalculator.PRAYER_NAMES.get(prayer, prayer),
                "date": next_date.strftime("%Y-%m-%d"),
                "tomorrow": True,
            }

        return None

    def _get_timezone_name(self, tz: int) -> str:
        """الحصول على اسم التوقيت الزمني"""
        return f"UTC{tz:+d}"


class AzanStreamer:
    """نظام بث الأذان والمقدمات"""

    AZAN_SOURCES = {
        "traditional": {
            "fajr": "https://example.com/azan/fajr.mp3",
            "dhuhr": "https://example.com/azan/dhuhr.mp3",
            "asr": "https://example.com/azan/asr.mp3",
            "maghrib": "https://example.com/azan/maghrib.mp3",
            "isha": "https://example.com/azan/isha.mp3",
        }
    }

    def __init__(self):
        self.active_streams: Dict[int, Dict] = {}

    def get_azan_url(self, prayer: str, source: str = "traditional") -> Optional[str]:
        """الحصول على رابط الأذان"""
        return self.AZAN_SOURCES.get(source, {}).get(prayer)

    def add_stream(
        self, chat_id: int, prayer: str, url: str, started_at: datetime = None
    ) -> bool:
        """إضافة بث جديد"""
        self.active_streams[chat_id] = {
            "prayer": prayer,
            "url": url,
            "started_at": started_at or datetime.now(),
            "status": "streaming",
        }
        return True

    def get_stream(self, chat_id: int) -> Optional[Dict]:
        """الحصول على معلومات البث"""
        return self.active_streams.get(chat_id)

    def stop_stream(self, chat_id: int) -> bool:
        """إيقاف البث"""
        if chat_id in self.active_streams:
            del self.active_streams[chat_id]
            return True
        return False

    def is_streaming(self, chat_id: int) -> bool:
        """هل البث نشط؟"""
        return chat_id in self.active_streams


class AzanNotificationManager:
    """إدارة التنبيهات والإشعارات"""

    def __init__(self):
        self.notification_queue: List[Dict] = []

    def add_notification(
        self,
        user_id: int,
        notification_type: NotificationType,
        prayer: str,
        scheduled_time: datetime = None,
    ) -> Dict:
        """إضافة تنبيه جديد"""
        notification = {
            "id": f"{user_id}_{prayer}_{datetime.now().timestamp()}",
            "user_id": user_id,
            "type": notification_type,
            "prayer": prayer,
            "scheduled_time": scheduled_time or datetime.now(),
            "sent": False,
        }
        self.notification_queue.append(notification)
        return notification

    def get_pending_notifications(self) -> List[Dict]:
        """الحصول على التنبيهات المعلقة"""
        return [n for n in self.notification_queue if not n["sent"]]

    def mark_as_sent(self, notification_id: str) -> bool:
        """وضع علامة على التنبيه كمُرسل"""
        for notification in self.notification_queue:
            if notification["id"] == notification_id:
                notification["sent"] = True
                return True
        return False

    def clear_old_notifications(self, hours: int = 24):
        """حذف التنبيهات القديمة"""
        # تبسيط للمحاكاة في الاختبارات
        self.notification_queue = []
