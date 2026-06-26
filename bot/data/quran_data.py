import json
import logging
import time
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

AYAH_COUNTS = {
    1: 7,
    2: 286,
    3: 200,
    4: 176,
    5: 120,
    6: 165,
    7: 206,
    8: 75,
    9: 129,
    10: 109,
    11: 123,
    12: 111,
    13: 43,
    14: 52,
    15: 99,
    16: 128,
    17: 111,
    18: 110,
    19: 98,
    20: 135,
    21: 112,
    22: 78,
    23: 118,
    24: 64,
    25: 77,
    26: 227,
    27: 93,
    28: 88,
    29: 69,
    30: 60,
    31: 34,
    32: 30,
    33: 73,
    34: 54,
    35: 45,
    36: 83,
    37: 182,
    38: 88,
    39: 75,
    40: 85,
    41: 54,
    42: 53,
    43: 89,
    44: 59,
    45: 37,
    46: 35,
    47: 38,
    48: 29,
    49: 18,
    50: 45,
    51: 60,
    52: 49,
    53: 62,
    54: 55,
    55: 78,
    56: 96,
    57: 29,
    58: 22,
    59: 24,
    60: 13,
    61: 14,
    62: 11,
    63: 11,
    64: 18,
    65: 12,
    66: 12,
    67: 30,
    68: 52,
    69: 52,
    70: 44,
    71: 28,
    72: 28,
    73: 20,
    74: 56,
    75: 40,
    76: 31,
    77: 50,
    78: 40,
    79: 46,
    80: 42,
    81: 29,
    82: 19,
    83: 36,
    84: 25,
    85: 22,
    86: 17,
    87: 19,
    88: 26,
    89: 30,
    90: 20,
    91: 15,
    92: 21,
    93: 11,
    94: 8,
    95: 8,
    96: 19,
    97: 5,
    98: 8,
    99: 8,
    100: 11,
    101: 11,
    102: 8,
    103: 3,
    104: 9,
    105: 5,
    106: 4,
    107: 7,
    108: 3,
    109: 6,
    110: 3,
    111: 5,
    112: 4,
    113: 5,
    114: 6,
}

JUZ_MAPPING = {}
_current_ayah = 0
_current_juz = 1
for s in range(1, 115):
    for a in range(1, AYAH_COUNTS[s] + 1):
        _current_ayah += 1
        if _current_ayah in (
            1,
            22,
            42,
            63,
            83,
            103,
            123,
            143,
            163,
            183,
            203,
            223,
            243,
            263,
            283,
            303,
            323,
            343,
            363,
            383,
            403,
            423,
            443,
            463,
            483,
            503,
            523,
            543,
            543,
        ):
            pass
        JUZ_MAPPING[f"{s}:{a}"] = _current_juz
        if _current_ayah in (
            21,
            41,
            61,
            81,
            101,
            121,
            141,
            161,
            181,
            201,
            221,
            241,
            261,
            281,
            301,
            321,
            341,
            361,
            381,
            401,
            421,
            441,
            461,
            481,
            501,
            521,
            541,
            561,
            581,
        ):
            _current_juz += 1


CACHE_DIR = Path("./data/quran_cache")


def _cache_path(key: str) -> Path:
    return CACHE_DIR / f"{key}.json"


async def _fetch_json(url: str, cache_key: str, ttl_hours: int = 24) -> Optional[dict]:
    path = _cache_path(cache_key)
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            age = time.time() - data.get("_cached_at", 0)
            if age < ttl_hours * 3600:
                return data
        except (json.JSONDecodeError, OSError):
            pass

    try:
        import aiohttp

        async with aiohttp.ClientSession() as session:
            async with session.get(
                url, timeout=aiohttp.ClientTimeout(total=15)
            ) as resp:
                if resp.status != 200:
                    logger.error("API error %d: %s", resp.status, url)
                    return None
                data = await resp.json()
    except Exception as e:
        logger.error("Fetch error: %s - %s", url, e)
        return None

    data["_cached_at"] = time.time()
    try:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    except OSError as e:
        logger.warning("Cache write error: %s", e)

    return data


async def get_ayah_text(surah: int, ayah: int) -> Optional[str]:
    url = f"https://api.alquran.cloud/v1/ayah/{surah}:{ayah}/ar"
    data = await _fetch_json(url, f"ayah_{surah}_{ayah}", ttl_hours=720)
    if data and "data" in data:
        return data["data"].get("text")
    return None


async def get_ayah_translation(
    surah: int, ayah: int, lang: str = "en.asad"
) -> Optional[str]:
    url = f"https://api.alquran.cloud/v1/ayah/{surah}:{ayah}/{lang}"
    data = await _fetch_json(url, f"ayah_{surah}_{ayah}_{lang}", ttl_hours=720)
    if data and "data" in data:
        return data["data"].get("text")
    return None


async def get_surah_short(surah: int) -> Optional[dict]:
    url = f"https://api.alquran.cloud/v1/surah/{surah}/ar"
    data = await _fetch_json(url, f"surah_{surah}", ttl_hours=720)
    if data and "data" in data:
        return data["data"]
    return None


async def get_tafsir(
    surah: int, ayah: int, tafsir_id: str = "ar-muyassar"
) -> Optional[str]:
    url = f"https://api.alquran.cloud/v1/tafsir/{tafsir_id}/{surah}:{ayah}"
    data = await _fetch_json(url, f"tafsir_{tafsir_id}_{surah}_{ayah}", ttl_hours=720)
    if data and "data" in data:
        return data["data"].get("text")
    return None


async def search_quran(keyword: str, lang: str = "ar") -> list[dict]:
    encoded = keyword.replace(" ", "%20")
    url = f"https://api.alquran.cloud/v1/search/{encoded}/all/{lang}"
    data = await _fetch_json(url, f"search_{lang}_{keyword[:50]}", ttl_hours=24)
    if data and "data" in data:
        return data["data"].get("matches", [])
    return []


async def get_juz(juz_number: int) -> Optional[list[dict]]:
    url = f"https://api.alquran.cloud/v1/juz/{juz_number}/ar"
    data = await _fetch_json(url, f"juz_{juz_number}", ttl_hours=720)
    if data and "data" in data:
        return data["data"].get("ayahs", [])
    return None
