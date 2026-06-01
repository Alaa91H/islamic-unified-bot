#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import math
from datetime import datetime, timedelta
from typing import Dict, Tuple, Optional
import asyncio
import aiohttp

class PrayerTimeCalculator:
    """حاسبة أوقات الصلاة المتقدمة - Advanced Prayer Times Calculator"""
    
    # طرق الحساب المختلفة
    CALCULATION_METHODS = {
        'karachi': {
            'name': 'جامعة الملك عبدالعزيز - كراتشي (University of Islamic Sciences, Karachi)',
            'fajr_angle': 18,
            'isha_angle': 18
        },
        'makkah': {
            'name': 'أم القرى (Umm Al-Qura University)',
            'fajr_angle': 18.5,
            'isha_angle': 90  # 90 دقيقة بعد المغرب
        },
        'isna': {
            'name': 'جمعية الشمال الأمريكية (Islamic Society of North America)',
            'fajr_angle': 15,
            'isha_angle': 15
        },
        'egypt': {
            'name': 'الهيئة المصرية (Egyptian General Authority)',
            'fajr_angle': 19.5,
            'isha_angle': 19.5
        },
        'algiers': {
            'name': 'أوقات الجزائر (Algiers, Community of Algers)',
            'fajr_angle': 18,
            'isha_angle': 17
        },
        'dubai': {
            'name': 'إمارة دبي (General Authority of Islamic Affairs, Dubai)',
            'fajr_angle': 18.5,
            'isha_angle': 19.5
        }
    }
    
    # الصلوات المطلوبة
    PRAYERS = ['fajr', 'sunrise', 'dhuhr', 'asr', 'sunset', 'maghrib', 'isha']
    PRAYER_NAMES = {
        'fajr': '🌅 الفجر',
        'sunrise': '🌄 الشروق',
        'dhuhr': '☀️ الظهر',
        'asr': '⛅ العصر',
        'sunset': '🌅 الغروب',
        'maghrib': '🌆 المغرب',
        'isha': '🌙 العشاء'
    }
    
    def __init__(self, latitude: float, longitude: float, timezone: int = 0, 
                 method: str = 'isna', asr_method: str = 'standard'):
        """
        تهيئة حاسبة أوقات الصلاة
        
        Args:
            latitude: خط العرض
            longitude: خط الطول
            timezone: التوقيت الزمني (بالساعات)
            method: طريقة الحساب (karachi, makkah, isna, egypt, algiers, dubai)
            asr_method: طريقة حساب العصر ('standard' أو 'hanafi')
        """
        self.latitude = math.radians(latitude)
        self.longitude = math.radians(longitude)
        self.timezone = timezone
        self.method = method
        self.asr_method = asr_method
        self.method_config = self.CALCULATION_METHODS.get(method, self.CALCULATION_METHODS['isna'])
        
    def _jdate(self, date: datetime) -> float:
        """حساب الرقم اليوليوسي"""
        a = (14 - date.month) // 12
        y = date.year + 4800 - a
        m = date.month + 12 * a - 3
        return (date.day + (153 * m + 2) // 5 + 365 * y + y // 4 - y // 100 + y // 400 - 32045.5)
    
    def _equation_of_time(self, jdate: float) -> float:
        """حساب معادلة الزمن"""
        D = jdate - 2451545.0
        g = (357.52910 + 0.98564724 * D) % 360
        q = (280.46645 + 0.9856474 * D) % 360
        L = (q + 1.914602 * math.sin(math.radians(g)) - 0.020708 * math.sin(math.radians(2*g))) % 360
        e = 23.439291 - 0.0130042 * D
        lambd = L - 0.02967 * math.sin(math.radians(2 * L))
        
        E = (q - 0.0057183 - lambd + 0.02468 * math.sin(math.radians(2 * L)) - 
             0.00684 * math.sin(math.radians(g)) + (0.00093 * math.sin(math.radians(2 * L)) * 
             math.sin(math.radians(2 * L))))
        
        return E
    
    def _compute_asr(self, T: float, hour: int) -> float:
        """حساب وقت العصر"""
        z = self._hour_angle(hour, T)
        sin_h = (math.sin(self.latitude) * math.sin(z) + 
                math.cos(self.latitude) * math.cos(z) * math.cos(T))
        h = math.degrees(math.asin(sin_h))
        
        method_factor = 1.0 if self.asr_method == 'standard' else 2.0
        cot_h = (math.tan(self.latitude) * method_factor - 
                 math.tan(z) * method_factor / math.sqrt(method_factor * method_factor + 1))
        
        return math.degrees(math.atan(1 / cot_h))
    
    def _hour_angle(self, hour: int, declination: float) -> float:
        """حساب زاوية الساعة"""
        return math.radians(15 * (hour - 12))
    
    def _sun_declination(self, jdate: float) -> float:
        """حساب ميل الشمس"""
        D = jdate - 2451545.0
        g = (357.52910 + 0.98564724 * D) % 360
        q = (280.46645 + 0.9856474 * D) % 360
        L = (q + 1.914602 * math.sin(math.radians(g)) - 0.020708 * math.sin(math.radians(2*g))) % 360
        e = 23.439291 - 0.0130042 * D
        lambd = L - 0.02967 * math.sin(math.radians(2 * L))
        
        declination = math.degrees(math.asin(math.sin(math.radians(e)) * math.sin(math.radians(lambd))))
        return declination
    
    def _equation_of_time_detailed(self, jdate: float) -> float:
        """حساب معادلة الزمن بشكل مفصل"""
        D = jdate - 2451545.0
        g = math.radians((357.52910 + 0.98564724 * D) % 360)
        q = math.radians((280.46645 + 0.9856474 * D) % 360)
        L = math.radians(((math.degrees(q) + 1.914602 * math.sin(g) - 
                          0.020708 * math.sin(2*g)) % 360))
        e = math.radians(23.439291 - 0.0130042 * D)
        y = math.tan(e/2) * math.tan(e/2)
        
        E = (4 * math.degrees(y * math.sin(2*q) - 2 * 
                             (math.sin(g) * math.cos(q) - 
                              2 * math.sin(g) * math.sin(g) * 
                              math.sin(q)) * y * 
                             math.sin(q)))
        
        return E
    
    def calculate_times(self, date: datetime) -> Dict[str, str]:
        """حساب أوقات الصلاة لتاريخ معين"""
        
        jdate = self._jdate(date)
        declination = self._sun_declination(jdate)
        eqtime = self._equation_of_time_detailed(jdate)
        
        # حساب زاوية الساعة للشروق والغروب
        latitude_rad = self.latitude
        declination_rad = math.radians(declination)
        
        ha_sunrise = math.acos(-math.tan(latitude_rad) * math.tan(declination_rad))
        sunrise_hour = (12 - math.degrees(ha_sunrise) / 15 - 
                       (self.longitude[0] if isinstance(self.longitude, tuple) else 0) / 15 - eqtime / 60 + 
                       self.timezone)
        
        # حسابات الفجر والعشاء
        ha_fajr = self._calculate_hour_angle(declination, -self.method_config['fajr_angle'])
        ha_isha = self._calculate_hour_angle(declination, -self.method_config['isha_angle'])
        
        # بناء القاموس
        times = {}
        
        # الفجر
        fajr_hour = 12 - math.degrees(ha_fajr) / 15 - eqtime / 60 + self.timezone
        times['fajr'] = self._decimal_to_time(fajr_hour)
        
        # الشروق
        sunrise_hour = 12 - math.degrees(ha_sunrise) / 15 - eqtime / 60 + self.timezone
        times['sunrise'] = self._decimal_to_time(sunrise_hour)
        
        # الظهر (عندما تكون الشمس في أعلى نقطة)
        dhuhr_hour = 12 - eqtime / 60 + self.timezone
        times['dhuhr'] = self._decimal_to_time(dhuhr_hour)
        
        # العصر
        asr_angle = 45 if self.asr_method == 'standard' else 63.26  # لـ Hanafi
        ha_asr = math.acos(math.cos(math.radians(asr_angle)) / 
                          (math.cos(latitude_rad) * math.cos(declination_rad)) - 
                          math.tan(latitude_rad) * math.tan(declination_rad))
        asr_hour = 12 + math.degrees(ha_asr) / 15 - eqtime / 60 + self.timezone
        times['asr'] = self._decimal_to_time(asr_hour)
        
        # الغروب
        sunset_hour = 12 + math.degrees(ha_sunrise) / 15 - eqtime / 60 + self.timezone
        times['sunset'] = self._decimal_to_time(sunset_hour)
        
        # المغرب
        maghrib_hour = sunset_hour
        times['maghrib'] = self._decimal_to_time(maghrib_hour)
        
        # العشاء
        if self.method == 'makkah':
            isha_hour = sunset_hour + self.method_config['isha_angle'] / 60
        else:
            isha_hour = 12 + math.degrees(ha_isha) / 15 - eqtime / 60 + self.timezone
        times['isha'] = self._decimal_to_time(isha_hour)
        
        return times
    
    def _calculate_hour_angle(self, declination: float, angle: float) -> float:
        """حساب زاوية الساعة للفجر والعشاء"""
        latitude_rad = self.latitude
        declination_rad = math.radians(declination)
        angle_rad = math.radians(angle)
        
        cos_ha = -(math.sin(angle_rad) + math.sin(latitude_rad) * 
                  math.sin(declination_rad)) / (math.cos(latitude_rad) * 
                  math.cos(declination_rad))
        
        cos_ha = max(-1, min(1, cos_ha))
        return math.acos(cos_ha)
    
    def _decimal_to_time(self, decimal_hour: float) -> str:
        """تحويل الساعة العشرية إلى صيغة HH:MM:SS"""
        decimal_hour = decimal_hour % 24
        hours = int(decimal_hour)
        minutes = int((decimal_hour - hours) * 60)
        seconds = int(((decimal_hour - hours) * 60 - minutes) * 60)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    
    def get_method_name(self) -> str:
        """الحصول على اسم طريقة الحساب"""
        return self.method_config['name']


class PrayerTimeAPI:
    """API للحصول على أوقات الصلاة من مصادر خارجية"""
    
    @staticmethod
    async def fetch_from_aladhan(latitude: float, longitude: float, 
                                 date: datetime, method: int = 2) -> Optional[Dict]:
        """
        الحصول على أوقات الصلاة من API Aladhan
        
        Methods:
        2 = Islamic Society of North America (ISNA)
        5 = Islamic Affairs of Dubai (Dubai)
        3 = University of Islamic Sciences, Karachi (Karachi)
        4 = Umm Al-Qura University (Makkah)
        """
        url = f"http://api.aladhan.com/v1/timings/{date.strftime('%d-%m-%Y')}"
        params = {
            'latitude': latitude,
            'longitude': longitude,
            'method': method
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        if data.get('code') == 200:
                            return data['data']['timings']
                    return None
        except Exception as e:
            print(f"خطأ في جلب البيانات: {e}")
            return None
    
    @staticmethod
    async def fetch_from_muslimworldleague(latitude: float, longitude: float, 
                                          date: datetime) -> Optional[Dict]:
        """الحصول على أوقات الصلاة من Muslim World League"""
        return await PrayerTimeAPI.fetch_from_aladhan(latitude, longitude, date, method=3)
    
    @staticmethod
    async def fetch_from_makkah(latitude: float, longitude: float, 
                               date: datetime) -> Optional[Dict]:
        """الحصول على أوقات الصلاة من Umm Al-Qura"""
        return await PrayerTimeAPI.fetch_from_aladhan(latitude, longitude, date, method=4)


class CityCoordinates:
    """قاعدة بيانات إحداثيات المدن"""
    
    CITIES = {
        # الدول العربية
        'مكة المكرمة': {'lat': 21.4225, 'lon': 39.8264, 'tz': 3, 'country': 'السعودية'},
        'المدينة المنورة': {'lat': 24.5047, 'lon': 39.5692, 'tz': 3, 'country': 'السعودية'},
        'الرياض': {'lat': 24.7136, 'lon': 46.6753, 'tz': 3, 'country': 'السعودية'},
        'جدة': {'lat': 21.5433, 'lon': 39.1728, 'tz': 3, 'country': 'السعودية'},
        'الدمام': {'lat': 26.4124, 'lon': 50.1971, 'tz': 3, 'country': 'السعودية'},
        'القاهرة': {'lat': 30.0444, 'lon': 31.2357, 'tz': 2, 'country': 'مصر'},
        'الإسكندرية': {'lat': 31.2001, 'lon': 29.9187, 'tz': 2, 'country': 'مصر'},
        'الجيزة': {'lat': 30.0131, 'lon': 31.2089, 'tz': 2, 'country': 'مصر'},
        'بغداد': {'lat': 33.3128, 'lon': 44.3615, 'tz': 3, 'country': 'العراق'},
        'بيروت': {'lat': 33.8886, 'lon': 35.4955, 'tz': 2, 'country': 'لبنان'},
        'دمشق': {'lat': 33.5186, 'lon': 36.2765, 'tz': 2, 'country': 'سوريا'},
        'عمّان': {'lat': 31.9454, 'lon': 35.9284, 'tz': 2, 'country': 'الأردن'},
        'الدوحة': {'lat': 25.2854, 'lon': 51.5310, 'tz': 3, 'country': 'قطر'},
        'دبي': {'lat': 25.2048, 'lon': 55.2708, 'tz': 4, 'country': 'الإمارات'},
        'أبو ظبي': {'lat': 24.4539, 'lon': 54.3773, 'tz': 4, 'country': 'الإمارات'},
        'مسقط': {'lat': 23.6100, 'lon': 58.5400, 'tz': 4, 'country': 'عمان'},
        'الكويت': {'lat': 29.3759, 'lon': 47.9774, 'tz': 3, 'country': 'الكويت'},
        'الرباط': {'lat': 34.0209, 'lon': -6.8416, 'tz': 0, 'country': 'المغرب'},
        'الجزائر': {'lat': 36.7372, 'lon': 3.0869, 'tz': 1, 'country': 'الجزائر'},
        'تونس': {'lat': 36.8065, 'lon': 10.1686, 'tz': 1, 'country': 'تونس'},
        'الخرطوم': {'lat': 15.5007, 'lon': 32.5599, 'tz': 2, 'country': 'السودان'},
        'إسطنبول': {'lat': 41.0082, 'lon': 28.9784, 'tz': 3, 'country': 'تركيا'},
        'أنقرة': {'lat': 39.9334, 'lon': 32.8597, 'tz': 3, 'country': 'تركيا'},
        'باكستان/كراتشي': {'lat': 24.8607, 'lon': 67.0011, 'tz': 5, 'country': 'باكستان'},
        'لاهور': {'lat': 31.5497, 'lon': 74.3436, 'tz': 5, 'country': 'باكستان'},
        'إسلام آباد': {'lat': 33.6844, 'lon': 73.1566, 'tz': 5, 'country': 'باكستان'},
        'الدار البيضاء': {'lat': 33.5731, 'lon': -7.5898, 'tz': 0, 'country': 'المغرب'},
        'نيويورك': {'lat': 40.7128, 'lon': -74.0060, 'tz': -5, 'country': 'الولايات المتحدة'},
        'لندن': {'lat': 51.5074, 'lon': -0.1278, 'tz': 0, 'country': 'المملكة المتحدة'},
        'باريس': {'lat': 48.8566, 'lon': 2.3522, 'tz': 1, 'country': 'فرنسا'},
        'برلين': {'lat': 52.5200, 'lon': 13.4050, 'tz': 1, 'country': 'ألمانيا'},
        'دبي (الإمارات)': {'lat': 25.2048, 'lon': 55.2708, 'tz': 4, 'country': 'الإمارات'},
        'سنغافورة': {'lat': 1.3521, 'lon': 103.8198, 'tz': 8, 'country': 'سنغافورة'},
        'جاكرتا': {'lat': -6.2088, 'lon': 106.8456, 'tz': 7, 'country': 'إندونيسيا'},
        'كوالالمبور': {'lat': 3.1390, 'lon': 101.6869, 'tz': 8, 'country': 'ماليزيا'},
        'طوكيو': {'lat': 35.6762, 'lon': 139.6503, 'tz': 9, 'country': 'اليابان'},
        'دبي (UAE)': {'lat': 25.2048, 'lon': 55.2708, 'tz': 4, 'country': 'الإمارات'},
    }
    
    @classmethod
    def get_city_coords(cls, city_name: str) -> Optional[Dict]:
        """الحصول على إحداثيات مدينة"""
        return cls.CITIES.get(city_name)
    
    @classmethod
    def search_cities(cls, query: str) -> list:
        """البحث عن مدن"""
        query = query.lower()
        results = []
        for city, data in cls.CITIES.items():
            if query in city.lower():
                results.append(city)
        return results
    
    @classmethod
    def get_all_cities(cls) -> Dict:
        """الحصول على جميع المدن"""
        return cls.CITIES
