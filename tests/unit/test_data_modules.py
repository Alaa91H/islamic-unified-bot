def test_adhkar_categories_have_items():
    from bot.data.adhkar import ADHKAR, ADHKAR_CATEGORIES

    assert len(ADHKAR_CATEGORIES) >= 8
    for key in ADHKAR_CATEGORIES:
        items = ADHKAR.get(key, [])
        assert len(items) > 0, f"{key} empty"
        for it in items:
            assert {"title", "text", "benefit"} <= set(it.keys())


def test_adhkar_keys_match_categories():
    from bot.data.adhkar import ADHKAR, ADHKAR_CATEGORIES

    assert set(ADHKAR_CATEGORIES.keys()) == set(ADHKAR.keys())


def test_surahs_complete():
    from bot.data.surahs import SURAHS

    assert set(SURAHS.keys()) == set(range(1, 115))
    assert all(isinstance(v, str) and v.strip() for v in SURAHS.values())


def test_surahs_known_values():
    from bot.data.surahs import SURAHS

    assert SURAHS[1] == "الفاتحة"
    assert SURAHS[2] == "البقرة"
    assert SURAHS[114] == "الناس"
    assert SURAHS[36] == "يس"


def test_sources_have_azan_for_all_prayers():
    from bot.data.sources import AZAN_SOURCES

    for key, src in AZAN_SOURCES.items():
        assert "name" in src, f"{key} missing name"
        for p in ("fajr", "dhuhr", "asr", "maghrib", "isha"):
            assert p in src, f"{key} missing {p}"


def test_sources_reciters_have_stream_url():
    from bot.data.sources import QURANIC_RECITERS

    assert len(QURANIC_RECITERS) >= 5
    for key, r in QURANIC_RECITERS.items():
        assert "name" in r and "stream_url" in r, key
        assert r["stream_url"].startswith("http"), key


def test_prelude_sources_have_duration():
    from bot.data.sources import PRELUDE_SOURCES

    for key, p in PRELUDE_SOURCES.items():
        assert "url" in p and "duration" in p, key
        assert isinstance(p["duration"], int) and p["duration"] > 0


# ============================================================
# Quran Data module-level tests
# ============================================================

def test_ayah_counts_has_all_surahs():
    from bot.data.quran_data import AYAH_COUNTS

    assert len(AYAH_COUNTS) == 114
    assert AYAH_COUNTS[1] == 7
    assert AYAH_COUNTS[114] == 6
    assert AYAH_COUNTS[2] == 286


def test_quran_cache_path():
    from bot.data.quran_data import _cache_path

    result = _cache_path("test_key")
    assert result.name == "test_key.json"
    assert "quran_cache" in str(result)


def test_quran_juz_mapping_has_entries():
    from bot.data.quran_data import JUZ_MAPPING

    assert len(JUZ_MAPPING) > 0
    assert "1:1" in JUZ_MAPPING
    assert "114:6" in JUZ_MAPPING


# ============================================================
# Hadith Data module-level tests
# ============================================================

def test_hadith_books_structure():
    from bot.data.hadith_data import HADITH_BOOKS

    assert len(HADITH_BOOKS) == 6
    for key, info in HADITH_BOOKS.items():
        assert "name" in info
        assert "api_id" in info
        assert "total" in info
        assert isinstance(info["api_id"], int)
        assert isinstance(info["total"], int)


def test_hadith_books_known_values():
    from bot.data.hadith_data import HADITH_BOOKS

    assert HADITH_BOOKS["bukhari"]["name"] == "صحيح البخاري"
    assert HADITH_BOOKS["bukhari"]["api_id"] == 1
    assert HADITH_BOOKS["muslim"]["name"] == "صحيح مسلم"
    assert HADITH_BOOKS["muslim"]["api_id"] == 2


def test_hadith_cache_path():
    from bot.data.hadith_data import _cache_path

    result = _cache_path("test_key")
    assert result.name == "test_key.json"
    assert "hadith_cache" in str(result)


def test_hadith_get_cached_no_file():
    from bot.data.hadith_data import _get_cached

    result = _get_cached("nonexistent_key_xyz", ttl_hours=1)
    assert result is None


def test_hadith_set_and_get_cache(tmp_path):
    from bot.data.hadith_data import _set_cache, _get_cached, CACHE_DIR

    import bot.data.hadith_data as hd
    original = hd.CACHE_DIR
    hd.CACHE_DIR = tmp_path / "hadith_test_cache"

    try:
        _set_cache("test_key", {"data": "value"})
        result = _get_cached("test_key", ttl_hours=720)
        assert result is not None
        assert result["data"] == "value"
    finally:
        hd.CACHE_DIR = original


def test_hadith_get_hadith_unknown_book():
    from bot.data.hadith_data import get_hadith

    import asyncio
    result = asyncio.run(get_hadith("nonexistent", 1))
    assert result is None


def test_format_hadith_returns_correct_format():
    from bot.data.hadith_data import format_hadith

    hadith = {"number": 1, "arab": "نص الحديث", "id": "Terjemahan"}
    result = format_hadith(hadith)
    assert "نص الحديث" in result
    assert "1" in result

    hadith_fallback = {"number": 5, "text": "Fallback text"}
    result2 = format_hadith(hadith_fallback)
    assert "Fallback text" in result2
    assert "5" in result2


# ============================================================
# Islamic Names module-level tests
# ============================================================

def test_names_of_allah_count():
    from bot.data.islamic_names import NAMES_OF_ALLAH

    assert len(NAMES_OF_ALLAH) == 99


def test_names_of_allah_structure():
    from bot.data.islamic_names import NAMES_OF_ALLAH

    for entry in NAMES_OF_ALLAH:
        idx, name_ar, name_en, desc_ar, desc_en = entry
        assert isinstance(idx, int)
        assert 1 <= idx <= 99
        assert isinstance(name_ar, str) and len(name_ar) > 0
        assert isinstance(name_en, str) and len(name_en) > 0


def test_names_of_allah_first():
    from bot.data.islamic_names import NAMES_OF_ALLAH

    assert NAMES_OF_ALLAH[0][0] == 1
    assert NAMES_OF_ALLAH[0][1] == "الرحمن"


def test_names_of_allah_last():
    from bot.data.islamic_names import NAMES_OF_ALLAH

    assert NAMES_OF_ALLAH[98][0] == 99
    assert NAMES_OF_ALLAH[98][1] == "الصبور"


def test_name_keys():
    from bot.data.islamic_names import NAME_KEYS

    assert len(NAME_KEYS) == 99
    assert 1 in NAME_KEYS
    assert 99 in NAME_KEYS
    assert NAME_KEYS[1][0] == "الرحمن"
