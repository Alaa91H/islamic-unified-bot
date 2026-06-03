import pytest

from advanced_adhkar_library import ADVANCED_ADHKAR
from azan_config import AZAN_SOURCES, PRELUDE_SOURCES


class TestAzanConfig:

    REQUIRED_PRAYERS = ["fajr", "dhuhr", "asr", "maghrib", "isha"]

    def test_azan_sources_not_empty(self):
        assert len(AZAN_SOURCES) > 0

    def test_azan_sources_have_name(self):
        for key, source in AZAN_SOURCES.items():
            assert "name" in source, f"Missing 'name' in source '{key}'"
            assert isinstance(source["name"], str)
            assert len(source["name"]) > 0

    def test_azan_sources_have_all_prayers(self):
        for key, source in AZAN_SOURCES.items():
            for prayer in self.REQUIRED_PRAYERS:
                assert prayer in source, f"Missing '{prayer}' in source '{key}'"

    def test_azan_sources_urls_are_strings(self):
        for key, source in AZAN_SOURCES.items():
            for prayer in self.REQUIRED_PRAYERS:
                url = source[prayer]
                assert isinstance(
                    url, str
                ), f"URL for {prayer} in '{key}' must be string, got {type(url)}"
                assert len(url) > 0, f"Empty URL for {prayer} in '{key}'"

    def test_prelude_sources_not_empty(self):
        assert len(PRELUDE_SOURCES) > 0

    def test_prelude_sources_structure(self):
        for key, source in PRELUDE_SOURCES.items():
            assert "name" in source, f"Missing 'name' in prelude '{key}'"
            assert "url" in source, f"Missing 'url' in prelude '{key}'"
            assert "duration" in source, f"Missing 'duration' in prelude '{key}'"

    def test_prelude_duration_positive(self):
        for key, source in PRELUDE_SOURCES.items():
            assert isinstance(
                source["duration"], (int, float)
            ), f"Duration must be numeric in '{key}'"
            assert source["duration"] > 0, f"Duration must be positive in '{key}'"

    def test_no_duplicate_source_keys(self):
        keys = list(AZAN_SOURCES.keys())
        assert len(keys) == len(set(keys)), "Duplicate keys found in AZAN_SOURCES"


class TestAdvancedAdhkarLibrary:

    def test_advanced_adhkar_not_empty(self):
        assert len(ADVANCED_ADHKAR) > 0

    def test_all_categories_have_list(self):
        for category, items in ADVANCED_ADHKAR.items():
            assert isinstance(
                items, list
            ), f"Category '{category}' must be a list, got {type(items)}"

    def test_all_categories_non_empty(self):
        for category, items in ADVANCED_ADHKAR.items():
            assert len(items) > 0, f"Category '{category}' is empty"

    def test_each_adhkar_has_title(self):
        for category, items in ADVANCED_ADHKAR.items():
            for i, item in enumerate(items):
                assert "title" in item, f"Missing 'title' in {category}[{i}]"
                assert isinstance(item["title"], str)
                assert len(item["title"]) > 0

    def test_each_adhkar_has_text(self):
        for category, items in ADVANCED_ADHKAR.items():
            for i, item in enumerate(items):
                assert "text" in item, f"Missing 'text' in {category}[{i}]"
                assert isinstance(item["text"], str)
                assert len(item["text"]) > 0

    def test_each_adhkar_has_benefit(self):
        for category, items in ADVANCED_ADHKAR.items():
            for i, item in enumerate(items):
                assert "benefit" in item, f"Missing 'benefit' in {category}[{i}]"

    def test_titles_are_unique_within_category(self):
        for category, items in ADVANCED_ADHKAR.items():
            titles = [item["title"] for item in items]
            assert len(titles) == len(
                set(titles)
            ), f"Duplicate titles in category '{category}'"

    def test_no_empty_text_fields(self):
        for category, items in ADVANCED_ADHKAR.items():
            for i, item in enumerate(items):
                text = item.get("text", "")
                assert (
                    text.strip() != ""
                ), f"Empty text in {category}[{i}]: {item.get('title')}"


class TestIslamicDataIntegrity:

    def test_main_module_imports_cleanly(self):
        try:
            # Just test that the file is parseable Python
            import ast

            with open("main.py", "r", encoding="utf-8") as f:
                source = f.read()
            tree = ast.parse(source)
            assert tree is not None
        except SyntaxError as e:
            pytest.fail(f"main.py has syntax error: {e}")

    def test_all_python_files_valid_syntax(self):
        import ast
        import glob

        py_files = glob.glob("*.py")
        errors = []
        for filepath in py_files:
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    ast.parse(f.read())
            except SyntaxError as e:
                errors.append(f"{filepath}: {e}")
        assert not errors, "Syntax errors found:\n" + "\n".join(errors)

    def test_requirements_txt_exists_and_non_empty(self):
        with open("requirements.txt", "r") as f:
            content = f.read().strip()
        assert len(content) > 0, "requirements.txt is empty"

    def test_requirements_has_core_packages(self):
        with open("requirements.txt", "r") as f:
            content = f.read().lower()
        for pkg in ("pyrogram", "py-tgcalls", "python-dotenv", "aiohttp"):
            assert pkg in content, f"Missing required package: {pkg}"

    def test_env_example_exists(self):
        import os

        assert os.path.exists(".env.example"), ".env.example file is missing"

    def test_env_example_has_required_keys(self):
        with open(".env.example", "r") as f:
            content = f.read()
        for key in ("BOT_TOKEN", "API_ID", "API_HASH", "OWNER_ID"):
            assert key in content, f"Missing key '{key}' in .env.example"

    def test_gitignore_protects_env(self):
        with open(".gitignore", "r") as f:
            content = f.read()
        assert ".env" in content, ".gitignore must include .env"
        assert "*.session" in content, ".gitignore must include *.session"

    def test_surahs_count_is_114(self):
        with open("main.py", "r", encoding="utf-8") as f:
            source = f.read()
        # Count SURAHS entries by parsing the dict literal
        import re

        matches = re.findall(r'^\s+\d+:\s+"[\u0600-\u06FF\s]+"', source, re.MULTILINE)
        assert len(matches) == 114, f"Expected 114 surahs, found {len(matches)}"
