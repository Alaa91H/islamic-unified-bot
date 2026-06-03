#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
مصادر الأذان والقرآن الكريم والقراء
Azan & Quran Sources and Reciters
"""

# ============================================================================
# مصادر الأذان والمقدمات الصوتية
# ============================================================================

AZAN_SOURCES = {
    "traditional": {
        "name": "الأذان المكي (عالي الجودة)",
        "fajr": "https://server8.mp3quran.net/azan/makkah_fajr.mp3",
        "dhuhr": "https://server8.mp3quran.net/azan/makkah.mp3",
        "asr": "https://server8.mp3quran.net/azan/makkah.mp3",
        "maghrib": "https://server8.mp3quran.net/azan/makkah.mp3",
        "isha": "https://server8.mp3quran.net/azan/makkah.mp3",
    },
    "abdul_basit": {
        "name": "الأذان - عبد الباسط عبد الصمد (HQ)",
        "fajr": "https://server10.mp3quran.net/basit/001.mp3",  # مثال لروابط عالية الجودة
        "dhuhr": "https://server10.mp3quran.net/basit/001.mp3",
        "asr": "https://server10.mp3quran.net/basit/001.mp3",
        "maghrib": "https://server10.mp3quran.net/basit/001.mp3",
        "isha": "https://server10.mp3quran.net/basit/001.mp3",
    },
    "ahmed_al_ajmi": {
        "name": "الأذان - أحمد العجمي",
        "fajr": "https://example.com/azan/ahmed_al_ajmi_fajr.mp3",
        "dhuhr": "https://example.com/azan/ahmed_al_ajmi_dhuhr.mp3",
        "asr": "https://example.com/azan/ahmed_al_ajmi_asr.mp3",
        "maghrib": "https://example.com/azan/ahmed_al_ajmi_maghrib.mp3",
        "isha": "https://example.com/azan/ahmed_al_ajmi_isha.mp3",
    },
    "mishari_al_affasy": {
        "name": "الأذان - مشاري العفاسي",
        "fajr": "https://example.com/azan/mishari_fajr.mp3",
        "dhuhr": "https://example.com/azan/mishari_dhuhr.mp3",
        "asr": "https://example.com/azan/mishari_asr.mp3",
        "maghrib": "https://example.com/azan/mishari_maghrib.mp3",
        "isha": "https://example.com/azan/mishari_isha.mp3",
    },
}

PRELUDE_SOURCES = {
    "iqamah": {
        "name": "الإقامة (قصيرة)",
        "url": "https://example.com/prelude/iqamah_short.mp3",
        "duration": 15,
    },
    "traditional": {
        "name": "مقدمة تقليدية",
        "url": "https://example.com/prelude/traditional.mp3",
        "duration": 30,
    },
    "pleasant_sound": {
        "name": "صوت لطيف",
        "url": "https://example.com/prelude/pleasant_sound.mp3",
        "duration": 25,
    },
}

# ============================================================================
# القارئين القرآنيين
# ============================================================================

QURANIC_RECITERS = {
    "abdul_basit": {
        "name": "عبد الباسط عبد الصمد",
        "country": "مصر",
        "description": "أسطورة التجويد والقراءة",
        "stream_url": "https://server8.mp3quran.net/afs/",
        "available_surahs": list(range(1, 115)),
    },
    "mishari_al_affasy": {
        "name": "مشاري راشد العفاسي",
        "country": "الكويت",
        "description": "قراءة عصرية جميلة",
        "stream_url": "https://server8.mp3quran.net/afs/",
        "available_surahs": list(range(1, 115)),
    },
    "ahmed_al_ajmi": {
        "name": "أحمد بن علي العجمي",
        "country": "الكويت",
        "description": "قراءة عذبة وسهلة",
        "stream_url": "https://server12.mp3quran.net/ajm/",
        "available_surahs": list(range(1, 115)),
    },
    "saad_al_ghamdi": {
        "name": "سعد الغامدي",
        "country": "السعودية",
        "description": "قراءة جميلة بأسلوب تدبري",
        "stream_url": "https://server7.mp3quran.net/s_gmd/",
        "available_surahs": list(range(1, 115)),
    },
    "maher_al_meaqli": {
        "name": "ماهر المعيقلي",
        "country": "السعودية",
        "description": "قراءة متقنة وفريدة",
        "stream_url": "https://server12.mp3quran.net/maher/",
        "available_surahs": list(range(1, 115)),
    },
    "yasser_al_dosari": {
        "name": "ياسر الدوسري",
        "country": "السعودية",
        "description": "قراءة متزنة وجميلة",
        "stream_url": "https://server6.mp3quran.net/dosri/",
        "available_surahs": list(range(1, 115)),
    },
    "abdul_rahman_al_sudais": {
        "name": "عبد الرحمن السديس",
        "country": "السعودية",
        "description": "الإمام الشهير للمسجد الحرام",
        "stream_url": "https://server11.mp3quran.net/sds/",
        "available_surahs": list(range(1, 115)),
    },
    "nasser_al_qatami": {
        "name": "ناصر القطامي",
        "country": "السعودية",
        "description": "قراءة عذبة ولطيفة",
        "stream_url": "https://server6.mp3quran.net/qtm/",
        "available_surahs": list(range(1, 115)),
    },
    "muhammad_al_tablawi": {
        "name": "محمد الطبلاوي",
        "country": "مصر",
        "description": "قراءة تراثية جميلة",
        "stream_url": "https://server12.mp3quran.net/tblwi/",
        "available_surahs": list(range(1, 115)),
    },
    "abdul_muhsin_al_qasim": {
        "name": "عبد المحسن القاسم",
        "country": "السعودية",
        "description": "إمام المسجد النبوي الشريف",
        "stream_url": "https://server8.mp3quran.net/qasm/",
        "available_surahs": list(range(1, 115)),
    },
}

# ============================================================================
# أوقات الصلاة الخاصة بالمدن الكبرى
# ============================================================================

SPECIAL_PRAYERS = {
    "taraweeh": {
        "name": "🌙 صلاة التراويح",
        "description": "صلاة التراويح في رمضان",
        "season": "ramadan",
        "time": "21:30",
    },
    "qiyam_lail": {
        "name": "🌙 قيام الليل",
        "description": "صلاة القيام وتقام في أواخر الليل",
        "season": "any",
        "time": "03:00",
    },
}

# ============================================================================
# إعدادات الحساب المتقدمة
# ============================================================================

CALCULATION_CONFIGS = {
    "karachi": {
        "name": "جامعة الملك عبدالعزيز - كراتشي",
        "fajr_angle": 18,
        "isha_angle": 18,
        "best_for": "الخليج والشام",
    },
    "makkah": {
        "name": "أم القرى - مكة المكرمة",
        "fajr_angle": 18.5,
        "isha_angle": 90,  # 90 دقيقة بعد المغرب
        "best_for": "السعودية والخليج",
    },
    "isna": {
        "name": "جمعية الشمال الأمريكية",
        "fajr_angle": 15,
        "isha_angle": 15,
        "best_for": "أمريكا وكندا",
    },
    "egypt": {
        "name": "الهيئة المصرية الرسمية",
        "fajr_angle": 19.5,
        "isha_angle": 19.5,
        "best_for": "مصر والدول الإفريقية",
    },
    "algiers": {
        "name": "أوقات الجزائر الرسمية",
        "fajr_angle": 18,
        "isha_angle": 17,
        "best_for": "المغرب والجزائر",
    },
    "dubai": {
        "name": "إمارة دبي",
        "fajr_angle": 18.5,
        "isha_angle": 19.5,
        "best_for": "الإمارات",
    },
}

# ============================================================================
# رسائل التنبيهات المخصصة
# ============================================================================

NOTIFICATION_MESSAGES = {
    "fajr": {
        "main": "🌅 حان وقت صلاة الفجر\nاستيقظ وتوضأ",
        "prelude": "🌅 سيبدأ الأذان خلال دقائق",
        "reminder": "⏰ نبهتك لصلاة الفجر",
    },
    "dhuhr": {
        "main": "☀️ حان وقت صلاة الظهر\nتوضأ وتهيأ",
        "prelude": "☀️ سيبدأ الأذان خلال دقائق",
        "reminder": "⏰ نبهتك لصلاة الظهر",
    },
    "asr": {
        "main": "⛅ حان وقت صلاة العصر\nاستعد للصلاة",
        "prelude": "⛅ سيبدأ الأذان خلال دقائق",
        "reminder": "⏰ نبهتك لصلاة العصر",
    },
    "maghrib": {
        "main": "🌆 حان وقت صلاة المغرب\nبادر للصلاة",
        "prelude": "🌆 سيبدأ الأذان خلال دقائق",
        "reminder": "⏰ نبهتك لصلاة المغرب",
    },
    "isha": {
        "main": "🌙 حان وقت صلاة العشاء\nبادر للصلاة",
        "prelude": "🌙 سيبدأ الأذان خلال دقائق",
        "reminder": "⏰ نبهتك لصلاة العشاء",
    },
}

# ============================================================================
# دعم اللغات
# ============================================================================

LANGUAGE_MESSAGES = {
    "ar": {
        "prayer_times": "أوقات الصلاة",
        "prayer": "الصلاة",
        "time": "الوقت",
        "city": "المدينة",
        "country": "الدولة",
        "method": "الطريقة",
        "next_prayer": "الصلاة التالية",
        "settings": "الإعدادات",
        "notifications": "التنبيهات",
    },
    "en": {
        "prayer_times": "Prayer Times",
        "prayer": "Prayer",
        "time": "Time",
        "city": "City",
        "country": "Country",
        "method": "Method",
        "next_prayer": "Next Prayer",
        "settings": "Settings",
        "notifications": "Notifications",
    },
}

# ============================================================================
# API الخارجية الموثوقة
# ============================================================================

EXTERNAL_APIS = {
    "aladhan": {
        "name": "Aladhan API",
        "url": "http://api.aladhan.com/v1",
        "methods": {
            2: "Islamic Society of North America",
            3: "Muslim World League",
            4: "Umm Al-Qura University",
            5: "Dubai Authority",
        },
        "supported": True,
    },
    "prayer_timings": {
        "name": "Prayer Timings",
        "url": "https://api.prayer-timings.com",
        "description": "API متقدم لأوقات الصلاة",
        "supported": False,
    },
    "waktusolat": {
        "name": "Waktu Solat API",
        "url": "https://api.waktusolat.my",
        "description": "متخصص في ماليزيا",
        "supported": False,
    },
}
