import json
import logging
import time
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

HADITH_BOOKS = {
    "bukhari": {
        "name": "صحيح البخاري",
        "name_en": "Sahih Bukhari",
        "api_id": 1,
        "total": 7563,
    },
    "muslim": {
        "name": "صحيح مسلم",
        "name_en": "Sahih Muslim",
        "api_id": 2,
        "total": 5362,
    },
    "abudawud": {
        "name": "سنن أبي داود",
        "name_en": "Sunan Abi Dawud",
        "api_id": 3,
        "total": 5274,
    },
    "tirmidhi": {
        "name": "جامع الترمذي",
        "name_en": "Jami At-Tirmidhi",
        "api_id": 4,
        "total": 3956,
    },
    "nasai": {
        "name": "سنن النسائي",
        "name_en": "Sunan An-Nasai",
        "api_id": 5,
        "total": 5762,
    },
    "ibnmajah": {
        "name": "سنن ابن ماجه",
        "name_en": "Sunan Ibn Majah",
        "api_id": 6,
        "total": 4341,
    },
}

CACHE_DIR = Path("./data/hadith_cache")


def _cache_path(key: str) -> Path:
    return CACHE_DIR / f"{key}.json"


def _get_cached(key: str, ttl_hours: int = 168) -> Optional[dict]:
    path = _cache_path(key)
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            age = time.time() - data.get("_cached_at", 0)
            if age < ttl_hours * 3600:
                return data
        except (json.JSONDecodeError, OSError):
            pass
    return None


def _set_cache(key: str, data: dict) -> None:
    data["_cached_at"] = time.time()
    try:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        _cache_path(key).write_text(
            json.dumps(data, ensure_ascii=False), encoding="utf-8"
        )
    except OSError as e:
        logger.warning("Cache write error: %s", e)


async def get_hadith(book_id: str, hadith_number: int) -> Optional[dict]:
    if book_id not in HADITH_BOOKS:
        return None
    api_id = HADITH_BOOKS[book_id]["api_id"]
    cache_key = f"{book_id}_{hadith_number}"
    cached = _get_cached(cache_key, ttl_hours=720)
    if cached:
        return cached

    url = f"https://api.hadith.sutanlab.id/books/{api_id}/{hadith_number}"
    try:
        import aiohttp

        async with aiohttp.ClientSession() as session:
            async with session.get(
                url, timeout=aiohttp.ClientTimeout(total=15)
            ) as resp:
                if resp.status != 200:
                    logger.error("Hadith API error %d: %s", resp.status, url)
                    return None
                data = await resp.json()
                if data.get("status") and data.get("data"):
                    hadith = data["data"].get("contents", {})
                    _set_cache(cache_key, hadith)
                    return hadith
    except Exception as e:
        logger.error("Hadith fetch error: %s - %s", url, e)

    return None


async def search_hadith(keyword: str, book_id: Optional[str] = None) -> list[dict]:
    api_id = HADITH_BOOKS[book_id]["api_id"] if book_id else 1
    encoded = keyword.replace(" ", "%20")
    url = f"https://api.hadith.sutanlab.id/books/{api_id}?search={encoded}&limit=10"

    cache_key = f"search_{book_id or 'all'}_{keyword[:30]}"
    cached = _get_cached(cache_key, ttl_hours=24)
    if cached:
        return cached.get("results", [])

    try:
        import aiohttp

        async with aiohttp.ClientSession() as session:
            async with session.get(
                url, timeout=aiohttp.ClientTimeout(total=15)
            ) as resp:
                if resp.status != 200:
                    return []
                data = await resp.json()
                if data.get("status") and data.get("data"):
                    hadiths = data["data"].get(
                        "hadiths", data["data"].get("contents", [])
                    )
                    if isinstance(hadiths, list):
                        _set_cache(cache_key, {"results": hadiths})
                        return hadiths
    except Exception as e:
        logger.error("Hadith search error: %s", e)

    return []


def format_hadith(hadith: dict) -> str:
    arabic = hadith.get("arab", "") or hadith.get("text", "")
    number = hadith.get("number", "")
    return f"📚 **الحديث الشريف**\n───\n{arabic}\n\n_(الحديث رقم {number})_"
