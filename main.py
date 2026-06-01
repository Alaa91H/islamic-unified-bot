#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
import logging
import sys
import os
import json
from datetime import datetime
from typing import Optional, Dict, Set
from pathlib import Path

from dotenv import load_dotenv
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from pytgcalls import PyTgCalls
from pytgcalls.types import MediaStream
from pytgcalls.exceptions import (
    NoActiveGroupCall,
    GroupCallAlreadyStarted,
    AlreadyJoinedError,
)

from azan_commands import register_azan_commands, azan_scheduler, azan_streamer
from advanced_adhkar_library import ADVANCED_ADHKAR

load_dotenv()

# ============================================================================
# السجلات
# ============================================================================

def setup_logging():
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    log_file = log_dir / f"islamic_unified_{datetime.now().strftime('%Y%m%d')}.log"
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)

logger = setup_logging()

# ============================================================================
# الإعدادات
# ============================================================================

def get_config():
    return {
        'BOT_TOKEN': os.getenv('BOT_TOKEN'),
        'API_ID': int(os.getenv('API_ID', '0')),
        'API_HASH': os.getenv('API_HASH'),
        'OWNER_ID': int(os.getenv('OWNER_ID', '0')),
        'MUSIC_DIR': os.getenv('MUSIC_DIR', './music'),
        'QURAN_STREAM_URL': os.getenv('QURAN_STREAM_URL', 'https://quran.kalamullah.com/mp3/afs/'),
        'MAX_RECONNECT_ATTEMPTS': int(os.getenv('MAX_RECONNECT_ATTEMPTS', '10')),
        'INITIAL_RECONNECT_DELAY': int(os.getenv('INITIAL_RECONNECT_DELAY', '5')),
    }

CONFIG = get_config()

def validate_config():
    errors = []
    if not CONFIG['BOT_TOKEN'] or CONFIG['BOT_TOKEN'] == 'YOUR_BOT_TOKEN_HERE':
        errors.append("❌ BOT_TOKEN لم يتم تعيينه")
    if CONFIG['API_ID'] == 0 or not CONFIG['API_HASH']:
        errors.append("❌ API_ID أو API_HASH لم يتم تعيينهما")
    if CONFIG['OWNER_ID'] == 0:
        errors.append("❌ OWNER_ID لم يتم تعيينه")
    if errors:
        for e in errors:
            logger.error(e)
        sys.exit(1)
    logger.info("✅ تم التحقق من الإعدادات بنجاح")

# ============================================================================
# البيانات الإسلامية
# ============================================================================

class IslamicData:
    CATEGORIES = {
        'morning': '🌅 أذكار الصباح',
        'evening': '🌙 أذكار المساء',
        'sleep': '😴 أذكار النوم والاستيقاظ',
        'entry': '🚪 أذكار الدخول والخروج',
        'prayer': '🤲 أذكار الصلاة',
        'journey': '✈️ أذكار السفر',
        'supplication': '🙏 الأدعية المشروعة',
        'tasbeeh': '📿 التسبيحات والتحميدات',
        'protection': '🛡️ الأدعية الحصينة والرقية',
        'gratitude': '🎁 شكر الله والرضا',
        'family': '👨‍👩‍👧 أذكار العائلة والأطفال',
        'health': '⚕️ أذكار الصحة والعافية',
    }

    ADHKAR = {
        'morning': [
            {'title': '✨ الآية الكريمة الأولى', 'text': 'بِسْمِ اللَّهِ الرَّحْمَٰنِ الرَّحِيمِ\n\"أَصْبَحْنَا وَأَصْبَحَ الْمُلْكُ لِلَّهِ، وَالْحَمْدُ لِلَّهِ، لَا إِلَٰهَ إِلَّا اللَّهُ وَحْدَهُ لَا شَرِيكَ لَهُ، لَهُ الْمُلْكُ وَلَهُ الْحَمْدُ وَهُوَ عَلَىٰ كُلِّ شَيْءٍ قَدِيرٌ\"', 'benefit': 'يُكتب لقائله كل يوم مائة حسنة'},
            {'title': '⭐ سورة الإخلاص والمعوذتان', 'text': 'قُلْ هُوَ اللَّهُ أَحَدٌ * اللَّهُ الصَّمَدُ * لَمْ يَلِدْ وَلَمْ يُولَدْ * وَلَمْ يَكُنْ لَهُ كُفُوًا أَحَدٌ', 'benefit': 'حصن عظيم من الشياطين والأمراض الروحية'},
            {'title': '🌟 آية الكرسي', 'text': 'اللَّهُ لَا إِلَٰهَ إِلَّا هُوَ الْحَيُّ الْقَيُّومُ ۚ لَا تَأْخُذُهُ سِنَةٌ وَلَا نَوْمٌ...', 'benefit': 'أفضل آية في القرآن الكريم، حماية عظيمة طوال اليوم'},
            {'title': '💫 اللهم إني أسألك', 'text': 'اللَّهُمَّ إِنِّي أَسْأَلُكَ عِلْمًا نَافِعًا، وَرِزْقًا طَيِّبًا، وَعَمَلًا تَقَبَّلُهُ', 'benefit': 'دعاء يومي شامل يجمع أعظم الحاجات'},
            {'title': '🌈 اللهم بك أصبحنا', 'text': 'اللَّهُمَّ بِكَ أَصْبَحْنَا، وَبِكَ أَمْسَيْنَا، وَبِكَ نَحْيَا، وَبِكَ نَمُوتُ، وَإِلَيْكَ النُّشُورُ', 'benefit': 'استسلام كامل لله في كل أحوالنا'},
        ],
        'evening': [
            {'title': '🌅 أمسينا وأمسى الملك', 'text': 'أَمْسَيْنَا وَأَمْسَى الْمُلْكُ لِلَّهِ، وَالْحَمْدُ لِلَّهِ...', 'benefit': 'حماية ليلية وحسنات كثيرة'},
            {'title': '⭐ الرقية والحصن', 'text': 'بِسْمِ اللَّهِ الرَّحْمَٰنِ الرَّحِيمِ\nسورة الإخلاص والمعوذتان (ثلاث مرات)', 'benefit': 'أقوى حصن من الشياطين والعين'},
            {'title': '💫 شكر الله على نعمه', 'text': 'اللَّهُمَّ أَنْتَ السَّلَامُ، وَمِنْكَ السَّلَامُ، تَبَارَكْتَ ذَا الْجَلَالِ وَالْإِكْرَامِ', 'benefit': 'شكر الله على سلامتك وعافيتك'},
            {'title': '✨ الاستغفار المضاعف', 'text': 'أَسْتَغْفِرُ اللَّهَ الْعَظِيمَ الَّذِي لَا إِلَٰهَ إِلَّا هُوَ، الْحَيُّ الْقَيُّومُ، وَأَتُوبُ إِلَيْهِ (3 مرات)', 'benefit': 'توبة وغفران للذنوب'},
        ],
        'sleep': [
            {'title': '😴 دعاء النوم', 'text': 'اللَّهُمَّ بِاسْمِكَ أَمُوتُ وَأَحْيَا', 'benefit': 'حماية وحسن ختام'},
            {'title': '🛡️ آية الكرسي', 'text': 'اللَّهُ لَا إِلَٰهَ إِلَّا هُوَ الْحَيُّ الْقَيُّومُ...', 'benefit': 'حماية مطلقة'},
            {'title': '💫 الدعاء الشامل', 'text': 'أَعُوذُ بِكَلِمَاتِ اللَّهِ التَّامَّاتِ مِنْ شَرِّ مَا خَلَقَ', 'benefit': 'عصمة من كل سوء'},
        ],
        'entry': [
            {'title': '🚪 الدخول إلى البيت', 'text': 'بِسْمِ اللَّهِ، دَخَلْنَا بِسْمِ اللَّهِ، وَخَرَجْنَا بِسْمِ اللَّهِ، وَعَلَى اللَّهِ رَبِّنَا تَوَكَّلْنَا', 'benefit': 'حماية وبركة في البيت'},
            {'title': '✨ الخروج من البيت', 'text': 'بِسْمِ اللَّهِ، تَوَكَّلْتُ عَلَى اللَّهِ، لَا حَوْلَ وَلَا قُوَّةَ إِلَّا بِاللَّهِ', 'benefit': 'حماية في الطريق والمسير'},
            {'title': '🚗 دخول المسجد', 'text': 'بِسْمِ اللَّهِ، السَّلَامُ عَلَى رَسُولِ اللَّهِ، اللَّهُمَّ افْتَحْ لِي أَبْوَابَ رَحْمَتِكَ', 'benefit': 'استقبال مبارك للمسجد'},
        ],
        'prayer': [
            {'title': '🤲 قبل الصلاة', 'text': 'اللَّهُمَّ اجْعَلْ نِيَّتِي خَالِصَةً لِوَجْهِكَ الْكَرِيمِ', 'benefit': 'إخلاص النية في العبادة'},
            {'title': '💫 الصلاة الإبراهيمية', 'text': 'اللَّهُمَّ صَلِّ عَلَىٰ مُحَمَّدٍ وَعَلَىٰ آلِ مُحَمَّدٍ...', 'benefit': 'محبة النبي وتعظيمه'},
            {'title': '✨ بعد التسليم', 'text': 'أَسْتَغْفِرُ اللَّهَ (3 مرات)\nاللَّهُمَّ أَنْتَ السَّلَامُ، وَمِنْكَ السَّلَامُ', 'benefit': 'ختم الصلاة بالاستغفار'},
        ],
        'journey': [
            {'title': '✈️ دعاء السفر', 'text': 'سُبْحَانَ الَّذِي سَخَّرَ لَنَا هَٰذَا وَمَا كُنَّا لَهُ مُقْرِنِينَ، وَإِنَّا إِلَىٰ رَبِّنَا لَمُنقَلِبُونَ', 'benefit': 'حماية وتسخير الركوب'},
            {'title': '🏨 العودة من السفر', 'text': 'آيِبُونَ، تَائِبُونَ، عَابِدُونَ، لِرَبِّنَا حَامِدُونَ', 'benefit': 'تكبير العودة من السفر'},
        ],
        'supplication': [
            {'title': '🙏 دعاء الاستجابة', 'text': 'يَا عَلِيمُ يَا قَدِيرُ، يَا رَحِيمُ يَا كَرِيمُ، اللَّهُمَّ اسْتَجِبْ دُعَاءَنَا', 'benefit': 'دعاء مستجاب بإذن الله'},
            {'title': '🎯 دعاء تفريج الكرب', 'text': 'لَا إِلَٰهَ إِلَّا أَنْتَ سُبْحَانَكَ إِنِّي كُنتُ مِنَ الظَّالِمِينَ', 'benefit': 'فرج من كل ضيق وكرب'},
        ],
        'tasbeeh': [
            {'title': '📿 التسبيح (سبحان الله)', 'text': 'سُبْحَانَ اللَّهِ (100 مرة)', 'benefit': 'تنزيه الله عن كل نقص'},
            {'title': '🎉 التحميد (الحمد لله)', 'text': 'الْحَمْدُ لِلَّهِ (100 مرة)', 'benefit': 'شكر نعم الله'},
            {'title': '💫 التسبيح الرباعي', 'text': 'سُبْحَانَ اللَّهِ، وَالْحَمْدُ لِلَّهِ، وَلَا إِلَٰهَ إِلَّا اللَّهُ، وَاللَّهُ أَكْبَرُ', 'benefit': 'أشمل وأعظم الأذكار'},
        ],
        'protection': [
            {'title': '🛡️ الرقية الشرعية', 'text': 'بِسْمِ اللَّهِ الرَّحْمَٰنِ الرَّحِيمِ\nقُلْ هُوَ اللَّهُ أَحَدٌ... (3 مرات)', 'benefit': 'أقوى حماية من الأمراض والعين'},
            {'title': '💫 حصن من كل شر', 'text': 'بِسْمِ اللَّهِ الَّذِي لَا يَضُرُّ مَعَ اسْمِهِ شَيْءٌ فِي الْأَرْضِ وَلَا فِي السَّمَاءِ', 'benefit': 'حصن منيع من كل ضرر'},
        ],
        'gratitude': [
            {'title': '🎁 شكر الله', 'text': 'الْحَمْدُ لِلَّهِ عَلَىٰ كُلِّ نِعْمَةٍ، وَالشُّكْرُ لِلَّهِ عَلَىٰ كُلِّ فَضْلٍ', 'benefit': 'زيادة النعم'},
            {'title': '💫 الرضا بقضاء الله', 'text': 'رَضِيتُ بِاللَّهِ رَبًّا، وَبِالْإِسْلَامِ دِينًا، وَبِمُحَمَّدٍ نَبِيًّا (3 مرات)', 'benefit': 'رضا القلب والطمأنينة'},
        ],
        'family': [
            {'title': '👨‍👩‍👧 دعاء الوالدين', 'text': 'رَبِّ اغْفِرْ لِي وَلِوَالِدَيَّ وَرَحْمَهُمَا كَمَا رَبَّيَانِي صَغِيرًا', 'benefit': 'دعاء للوالدين والبر بهما'},
            {'title': '👪 سعادة العائلة', 'text': 'اللَّهُمَّ اجْعَلْ بَيْتَنَا أَمِنًا مُطْمَئِنًّا، وَاجْعَلْ أَهْلَنَا مِنَ الصَّالِحِينَ', 'benefit': 'أمن وسلام بيتي'},
        ],
        'health': [
            {'title': '⚕️ دعاء الشفاء', 'text': 'اللَّهُمَّ يَا مَنْ تُمْسِكُ السَّمَاءَ أَنْ تَقَعَ، أَدْعُوكَ أَنْ تَشْفِي مَرِيضَنَا', 'benefit': 'شفاء من الأمراض'},
            {'title': '💪 العافية والصحة', 'text': 'اللَّهُمَّ عَافِنِي فِي بَدَنِي، اللَّهُمَّ عَافِنِي فِي سَمْعِي، اللَّهُمَّ عَافِنِي فِي بَصَرِي', 'benefit': 'صحة وعافية كاملة'},
        ],
    }

    SURAHS = {
        1: "الفاتحة", 2: "البقرة", 3: "آل عمران", 4: "النساء",
        5: "المائدة", 6: "الأنعام", 7: "الأعراف", 8: "الأنفال",
        9: "التوبة", 10: "يونس", 11: "هود", 12: "يوسف",
        13: "الرعد", 14: "إبراهيم", 15: "الحجر", 16: "النحل",
        17: "الإسراء", 18: "الكهف", 19: "مريم", 20: "طه",
        21: "الأنبياء", 22: "الحج", 23: "المؤمنون", 24: "النور",
        25: "الفرقان", 26: "الشعراء", 27: "النمل", 28: "القصص",
        29: "العنكبوت", 30: "الروم", 31: "لقمان", 32: "السجدة",
        33: "الأحزاب", 34: "سبأ", 35: "فاطر", 36: "يس",
        37: "الصافات", 38: "ص", 39: "الزمر", 40: "غافر",
        41: "فصلت", 42: "الشورى", 43: "الزخرف", 44: "الدخان",
        45: "الجاثية", 46: "الأحقاف", 47: "محمد", 48: "الفتح",
        49: "الحجرات", 50: "ق", 51: "الذاريات", 52: "الطور",
        53: "النجم", 54: "القمر", 55: "الرحمن", 56: "الواقعة",
        57: "الحديد", 58: "المجادلة", 59: "الحشر", 60: "الممتحنة",
        61: "الصف", 62: "الجمعة", 63: "المنافقون", 64: "التغابن",
        65: "الطلاق", 66: "التحريم", 67: "الملك", 68: "القلم",
        69: "الحاقة", 70: "المعارج", 71: "نوح", 72: "الجن",
        73: "المزمل", 74: "المدثر", 75: "القيامة", 76: "الإنسان",
        77: "المرسلات", 78: "النبأ", 79: "النازعات", 80: "عبس",
        81: "التكوير", 82: "الإنفطار", 83: "المطففين", 84: "الانشقاق",
        85: "البروج", 86: "الطارق", 87: "الأعلى", 88: "الغاشية",
        89: "الفجر", 90: "البلد", 91: "الشمس", 92: "الليل",
        93: "الضحى", 94: "الشرح", 95: "التين", 96: "العلق",
        97: "القدر", 98: "البينة", 99: "الزلزلة", 100: "العاديات",
        101: "القارعة", 102: "التكاثر", 103: "العصر", 104: "الهمزة",
        105: "الفيل", 106: "قريش", 107: "الماعون", 108: "الكوثر",
        109: "الكافرون", 110: "النصر", 111: "المسد", 112: "الإخلاص",
        113: "الفلق", 114: "الناس"
    }

# ============================================================================
# مدير البث
# ============================================================================

class StreamManager:
    def __init__(self, client: Client):
        self.pytgcalls = PyTgCalls(client)
        self.streams: Dict = {}
        Path(CONFIG['MUSIC_DIR']).mkdir(exist_ok=True)

    async def start(self):
        try:
            await self.pytgcalls.start()
            logger.info("✅ تم بدء خدمة المكالمات")
        except Exception as e:
            logger.error(f"❌ خطأ في بدء خدمة المكالمات: {e}")

    async def stop(self):
        try:
            await self.pytgcalls.stop()
        except Exception as e:
            logger.error(f"❌ خطأ في إيقاف خدمة المكالمات: {e}")

    def get_local_files(self, folder_path: str = None) -> Dict:
        if folder_path is None:
            folder_path = CONFIG['MUSIC_DIR']
        files = {}
        try:
            path = Path(folder_path)
            extensions = ['.mp3', '.wav', '.flac', '.m4a', '.ogg']
            for i, file in enumerate(path.glob('*'), 1):
                if file.suffix.lower() in extensions:
                    files[i] = {
                        'name': file.name,
                        'path': str(file.absolute()),
                        'size': file.stat().st_size
                    }
        except Exception as e:
            logger.error(f"❌ خطأ في قراءة المجلد: {e}")
        return files

    async def start_stream(self, chat_id: int, media_url: str, title: str = "البث المباشر") -> bool:
        try:
            media = MediaStream(media_url)
            await self.pytgcalls.join_group_call(chat_id, media, stream_type="audio")
            self.streams[chat_id] = {
                'url': media_url,
                'title': title,
                'started_at': datetime.now(),
                'status': 'active'
            }
            logger.info(f"✅ بدء البث في {chat_id}: {title}")
            return True
        except AlreadyJoinedError:
            logger.warning(f"⚠️ البوت موجود بالفعل في {chat_id}")
            return False
        except Exception as e:
            logger.error(f"❌ خطأ في بدء البث: {e}")
            return False

    async def stop_stream(self, chat_id: int) -> bool:
        try:
            await self.pytgcalls.leave_group_call(chat_id)
            self.streams.pop(chat_id, None)
            logger.info(f"✅ إيقاف البث في {chat_id}")
            return True
        except Exception as e:
            logger.error(f"❌ خطأ في إيقاف البث: {e}")
            return False

    def get_active_streams(self) -> Dict:
        return self.streams

# ============================================================================
# إنشاء البوت
# ============================================================================

app = Client(
    "islamic_unified_bot",
    api_id=CONFIG['API_ID'],
    api_hash=CONFIG['API_HASH'],
    bot_token=CONFIG['BOT_TOKEN']
)

stream_manager = StreamManager(app)

# ============================================================================
# القائمة الرئيسية
# ============================================================================

def main_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📿 الأذكار الإسلامية", callback_data="main_adhkar_menu")],
        [InlineKeyboardButton("📖 القرآن الكريم", callback_data="quran_menu")],
        [InlineKeyboardButton("🕌 أوقات الأذان والصلاة", callback_data="azan_home")],
        [InlineKeyboardButton("ℹ️ حول البوت", callback_data="about")],
    ])

@app.on_message(filters.command("start"))
async def start_command(client: Client, message: Message):
    await message.reply_text(
        "🕌 **مرحباً بك في البوت الإسلامي الموحد**\n\n"
        "🌟 **يضم هذا البوت:**\n"
        "✅ جميع الأذكار الإسلامية الشاملة\n"
        "✅ بث صوتي للقرآن الكريم (114 سورة)\n"
        "✅ أوقات الأذان والصلاة لمدن العالم\n"
        "✅ تنبيهات تلقائية عند أوقات الصلاة\n"
        "✅ واجهة تفاعلية سهلة الاستخدام\n\n"
        "اختر من القائمة أدناه:",
        reply_markup=main_keyboard(),
        parse_mode="markdown"
    )

@app.on_message(filters.command("help"))
async def help_command(client: Client, message: Message):
    await message.reply_text(
        "🕌 **البوت الإسلامي الموحد - دليل الاستخدام**\n\n"
        "**الأوامر الأساسية:**\n"
        "/start - القائمة الرئيسية\n"
        "/adhkar - الأذكار الإسلامية\n"
        "/quran - القرآن الكريم\n"
        "/azan_setup - إعداد أوقات الأذان\n"
        "/azan_times - عرض أوقات الصلاة اليوم\n"
        "/azan_next - الصلاة التالية\n"
        "/azan_settings - إعدادات الأذان\n\n"
        "**أوامر البث (للمالك فقط):**\n"
        "/stream [chat_id] quran [رقم] - تشغيل سورة\n"
        "/stream [chat_id] file [رقم] - تشغيل ملف محلي\n"
        "/stream [chat_id] url [رابط] - تشغيل رابط\n"
        "/stop [chat_id] - إيقاف البث\n"
        "/status - حالة البثات\n"
        "/files - الملفات المحلية المتاحة",
        parse_mode="markdown"
    )

@app.on_message(filters.command("adhkar"))
async def adhkar_command(client: Client, message: Message):
    keyboard_list = [[InlineKeyboardButton(v, callback_data=f"category_{k}")] for k, v in IslamicData.CATEGORIES.items()]
    await message.reply_text(
        "📿 **الأذكار الإسلامية الشاملة**\n\nاختر الفئة:",
        reply_markup=InlineKeyboardMarkup(keyboard_list),
        parse_mode="markdown"
    )

@app.on_message(filters.command("quran"))
async def quran_command(client: Client, message: Message):
    await message.reply_text(
        "📖 **القرآن الكريم**\n\nاختر طريقة:",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📚 قائمة السور", callback_data="surah_list")],
            [InlineKeyboardButton("🔙 الرئيسية", callback_data="back_to_start")],
        ]),
        parse_mode="markdown"
    )

# ============================================================================
# أوامر البث (للمالك)
# ============================================================================

@app.on_message(filters.command("stream"))
async def stream_command(client: Client, message: Message):
    if message.from_user.id != CONFIG['OWNER_ID']:
        await message.reply_text("❌ لا توجد صلاحيات")
        return
    try:
        args = message.command[1:]
        if len(args) < 2:
            await message.reply_text(
                "📌 **استخدام:**\n"
                "`/stream [chat_id] quran [رقم]`\n"
                "`/stream [chat_id] file [رقم]`\n"
                "`/stream [chat_id] url [رابط]`",
                parse_mode="markdown"
            )
            return
        chat_id = int(args[0])
        stream_type = args[1].lower()
        if stream_type == "quran":
            surah_num = int(args[2])
            if not (1 <= surah_num <= 114):
                await message.reply_text("❌ رقم السورة يجب أن يكون بين 1-114")
                return
            url = f"{CONFIG['QURAN_STREAM_URL']}{surah_num:03d}.mp3"
            name = IslamicData.SURAHS.get(surah_num, "سورة")
            success = await stream_manager.start_stream(chat_id, url, f"{surah_num} - {name}")
            if success:
                await message.reply_text(f"✅ بدأ البث: **{surah_num} - {name}**\n📍 `{chat_id}`", parse_mode="markdown")
            else:
                await message.reply_text("❌ فشل بدء البث")
        elif stream_type == "file":
            file_num = int(args[2])
            files = stream_manager.get_local_files()
            if file_num not in files:
                await message.reply_text(f"❌ الملف {file_num} غير موجود")
                return
            info = files[file_num]
            success = await stream_manager.start_stream(chat_id, info['path'], info['name'])
            if success:
                await message.reply_text(f"✅ بدأ البث: **{info['name']}**", parse_mode="markdown")
            else:
                await message.reply_text("❌ فشل بدء البث")
        elif stream_type == "url":
            url = args[2]
            success = await stream_manager.start_stream(chat_id, url, "بث مخصص")
            if success:
                await message.reply_text(f"✅ بدأ البث من الرابط في `{chat_id}`", parse_mode="markdown")
            else:
                await message.reply_text("❌ فشل بدء البث")
        else:
            await message.reply_text("❌ نوع غير معروف (quran/file/url)")
    except Exception as e:
        await message.reply_text(f"❌ خطأ: {e}")

@app.on_message(filters.command("stop"))
async def stop_command(client: Client, message: Message):
    if message.from_user.id != CONFIG['OWNER_ID']:
        await message.reply_text("❌ لا توجد صلاحيات")
        return
    args = message.command[1:]
    if not args:
        await message.reply_text("`/stop [chat_id]`")
        return
    chat_id = int(args[0])
    success = await stream_manager.stop_stream(chat_id)
    if success:
        await message.reply_text(f"✅ تم إيقاف البث في `{chat_id}`", parse_mode="markdown")
    else:
        await message.reply_text("❌ فشل إيقاف البث")

@app.on_message(filters.command("status"))
async def status_command(client: Client, message: Message):
    if message.from_user.id != CONFIG['OWNER_ID']:
        await message.reply_text("❌ لا توجد صلاحيات")
        return
    streams = stream_manager.get_active_streams()
    if not streams:
        await message.reply_text("✅ لا توجد بثات نشطة حالياً")
        return
    text = "📊 **البثات النشطة:**\n\n"
    for chat_id, info in streams.items():
        mins = (datetime.now() - info['started_at']).seconds // 60
        text += f"📍 `{chat_id}`\n🎵 {info['title']}\n⏱️ {mins} دقيقة\n\n"
    await message.reply_text(text, parse_mode="markdown")

@app.on_message(filters.command("files"))
async def files_command(client: Client, message: Message):
    if message.from_user.id != CONFIG['OWNER_ID']:
        await message.reply_text("❌ لا توجد صلاحيات")
        return
    files = stream_manager.get_local_files()
    if not files:
        await message.reply_text(f"❌ لا توجد ملفات في `{CONFIG['MUSIC_DIR']}`")
        return
    text = f"📁 **الملفات ({len(files)}):**\n\n"
    for num, info in files.items():
        size_mb = info['size'] / (1024 * 1024)
        text += f"{num}. {info['name']} ({size_mb:.2f} MB)\n"
    await message.reply_text(text, parse_mode="markdown")

# ============================================================================
# معالجات الأزرار
# ============================================================================

@app.on_callback_query()
async def handle_callback(client: Client, cq: CallbackQuery):
    try:
        data = cq.data

        # ---- القائمة الرئيسية ----
        if data == "back_to_start":
            await cq.message.edit_text(
                "🕌 **القائمة الرئيسية**\n\nاختر من القائمة:",
                reply_markup=main_keyboard(),
                parse_mode="markdown"
            )

        # ---- الأذكار ----
        elif data == "main_adhkar_menu":
            keyboard_list = [[InlineKeyboardButton(v, callback_data=f"category_{k}")] for k, v in IslamicData.CATEGORIES.items()]
            keyboard_list.append([InlineKeyboardButton("🔙 العودة", callback_data="back_to_start")])
            await cq.message.edit_text(
                "📿 **اختر فئة الأذكار:**",
                reply_markup=InlineKeyboardMarkup(keyboard_list),
                parse_mode="markdown"
            )

        elif data.startswith("category_"):
            category = data.replace("category_", "")
            adhkar_list = IslamicData.ADHKAR.get(category, [])
            keyboard_list = []
            for i, adhkar in enumerate(adhkar_list):
                keyboard_list.append([InlineKeyboardButton(f"{i+1}. {adhkar['title'][:35]}", callback_data=f"adhkar_{category}_{i}")])
            keyboard_list.append([InlineKeyboardButton("🔙 الرجوع", callback_data="main_adhkar_menu")])
            await cq.message.edit_text(
                f"📿 **{IslamicData.CATEGORIES.get(category)}:**",
                reply_markup=InlineKeyboardMarkup(keyboard_list),
                parse_mode="markdown"
            )

        elif data.startswith("adhkar_"):
            parts = data.replace("adhkar_", "").split("_")
            category = parts[0]
            idx = int(parts[1])
            adhkar = IslamicData.ADHKAR[category][idx]
            text = f"🕌 **{adhkar['title']}**\n\n📝 **النص:**\n{adhkar['text']}\n\n✨ **الفضل:**\n{adhkar['benefit']}"
            await cq.message.edit_text(
                text,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 الرجوع", callback_data=f"category_{category}")],
                    [InlineKeyboardButton("🏠 الرئيسية", callback_data="back_to_start")],
                ]),
                parse_mode="markdown"
            )

        # ---- القرآن ----
        elif data == "quran_menu":
            await cq.message.edit_text(
                "📖 **القرآن الكريم**\n\nاختر طريقة:",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("📚 قائمة السور", callback_data="surah_list")],
                    [InlineKeyboardButton("🔙 العودة", callback_data="back_to_start")],
                ]),
                parse_mode="markdown"
            )

        elif data == "surah_list":
            keyboard_list = []
            for i in range(1, 115, 2):
                s1 = IslamicData.SURAHS.get(i, "")
                s2 = IslamicData.SURAHS.get(i + 1, "")
                row = [InlineKeyboardButton(f"{i}-{s1}", callback_data=f"surah_{i}")]
                if s2:
                    row.append(InlineKeyboardButton(f"{i+1}-{s2}", callback_data=f"surah_{i+1}"))
                keyboard_list.append(row)
            keyboard_list.append([InlineKeyboardButton("🔙 الرجوع", callback_data="quran_menu")])
            await cq.message.edit_text(
                "📚 **اختر السورة:**",
                reply_markup=InlineKeyboardMarkup(keyboard_list),
                parse_mode="markdown"
            )

        elif data.startswith("surah_"):
            num = int(data.replace("surah_", ""))
            name = IslamicData.SURAHS.get(num, "")
            await cq.message.edit_text(
                f"📖 **{num} - {name}**\n\n🎵 للاستماع استخدم الأمر:\n`/stream [chat_id] quran {num}`",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 السور", callback_data="surah_list")],
                    [InlineKeyboardButton("🏠 الرئيسية", callback_data="back_to_start")],
                ]),
                parse_mode="markdown"
            )

        # ---- الأذان (توجيه للأوامر) ----
        elif data == "azan_home":
            await cq.message.edit_text(
                "🕌 **نظام الأذان وأوقات الصلاة**\n\n"
                "استخدم الأوامر التالية:\n"
                "/azan_setup - إعداد مدينتك\n"
                "/azan_times - أوقات الصلاة اليوم\n"
                "/azan_next - الصلاة التالية\n"
                "/azan_settings - الإعدادات\n"
                "/azan_search [مدينة] - البحث عن مدينة",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 العودة", callback_data="back_to_start")],
                ]),
                parse_mode="markdown"
            )

        # ---- حول البوت ----
        elif data == "about":
            await cq.message.edit_text(
                "🕌 **البوت الإسلامي الموحد**\n\n"
                "**يضم ثلاثة أنظمة متكاملة:**\n\n"
                "📿 **بوت الأذكار** - أذكار إسلامية شاملة مصنفة\n"
                "📖 **بوت القرآن** - بث صوتي لكامل القرآن الكريم\n"
                "🕌 **بوت الأذان** - أوقات الصلاة مع تنبيهات تلقائية\n\n"
                "**الأوامر:** /help",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 العودة", callback_data="back_to_start")],
                ]),
                parse_mode="markdown"
            )

        await cq.answer()

    except Exception as e:
        logger.error(f"خطأ في الزر: {e}")
        try:
            await cq.answer(f"❌ خطأ: {str(e)[:100]}", show_alert=True)
        except Exception:
            pass

# ============================================================================
# بدء وإيقاف البوت
# ============================================================================

@app.on_startup
async def on_startup():
    logger.info("=" * 70)
    logger.info("🕌 البوت الإسلامي الموحد - يبدأ التشغيل...")
    logger.info("=" * 70)
    await stream_manager.start()
    await register_azan_commands(app)
    logger.info("✅ جميع الأنظمة جاهزة!")

@app.on_shutdown
async def on_shutdown():
    logger.info("🛑 إيقاف البوت...")
    await stream_manager.stop()
    logger.info("✅ تم الإيقاف بنجاح")

# ============================================================================
# نقطة البداية
# ============================================================================

if __name__ == "__main__":
    logger.info("=" * 70)
    logger.info("🕌 البوت الإسلامي الموحد")
    logger.info("   ✅ بوت الأذكار + بوت القرآن + بوت الأذان")
    logger.info("=" * 70)

    validate_config()

    try:
        logger.info(f"👤 معرف المالك: {CONFIG['OWNER_ID']}")
        logger.info(f"📁 مجلد الملفات: {CONFIG['MUSIC_DIR']}")
        logger.info("=" * 70)
        app.run()
    except KeyboardInterrupt:
        logger.info("🛑 تم الإيقاف بواسطة المستخدم")
    except Exception as e:
        logger.error(f"❌ خطأ حرج: {e}", exc_info=True)
        sys.exit(1)
