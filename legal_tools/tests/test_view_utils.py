# Third-party
from django.core.cache import cache
from django.test import TestCase, override_settings

# First-party/Local
from i18n.utils import get_default_language_for_jurisdiction_deed
from legal_tools.models import Tool
from legal_tools.tests.test_views import ToolsTestsMixin
from legal_tools.view_utils import (
    get_category_and_category_title,
    get_deed_rel_path,
    get_legal_code_replaced_rel_path,
    normalize_path_and_lang,
)


class ViewHelperFunctionsTest(ToolsTestsMixin, TestCase):
    def test_get_category_and_category_title_category_tool(self):
        category, category_title = get_category_and_category_title(
            category=None,
            tool=None,
        )
        self.assertEqual(category, "licenses")
        self.assertEqual(category_title, "Licenses")

        tool = Tool.objects.get(unit="by", version="4.0")
        category, category_title = get_category_and_category_title(
            category=None,
            tool=tool,
        )
        self.assertEqual(category, "licenses")
        self.assertEqual(category_title, "Licenses")

    def test_get_category_and_category_title_category_publicdomain(self):
        category, category_title = get_category_and_category_title(
            category="publicdomain",
            tool=None,
        )
        self.assertEqual(category, "publicdomain")
        self.assertEqual(category_title, "Public Domain")

    @override_settings(LANGUAGES_MOSTLY_TRANSLATED=["x1", "x2"])
    def test_get_deed_rel_path_mostly_translated_language_code(self):
        expected_deed_rel_path = "deed.x1"
        deed_rel_path = get_deed_rel_path(
            deed_url="/deed.x1",
            path_start="/",
            language_code="x1",
            language_default="x2",
        )
        self.assertEqual(expected_deed_rel_path, deed_rel_path)

    @override_settings(LANGUAGES_MOSTLY_TRANSLATED=["x1", "x2"])
    def test_get_deed_rel_path_less_translated_language_code(self):
        expected_deed_rel_path = "deed.x2"
        deed_rel_path = get_deed_rel_path(
            deed_url="/deed.x3",
            path_start="/",
            language_code="x3",
            language_default="x2",
        )
        self.assertEqual(expected_deed_rel_path, deed_rel_path)

    @override_settings(
        LANGUAGE_CODE="x1",
        LANGUAGES_MOSTLY_TRANSLATED=[],
    )
    def test_get_deed_rel_path_less_translated_language_default(self):
        expected_deed_rel_path = "deed.x1"
        deed_rel_path = get_deed_rel_path(
            deed_url="/deed.x3",
            path_start="/",
            language_code="x3",
            language_default="x2",
        )
        self.assertEqual(expected_deed_rel_path, deed_rel_path)

    def test_get_legal_code_replaced_rel_path_cache_miss(self):
        tool = Tool.objects.get(
            unit="by",
            version="3.0",
            jurisdiction_code="",
        )
        path_start = "/licenses/by/3.0"
        language_code = "en"
        language_default = get_default_language_for_jurisdiction_deed(None)

        cache.clear()
        self.assertFalse(cache.has_key("by-4.0--en-replaced_deed_str"))
        self.assertFalse(cache.has_key("by-4.0--en-replaced_legal_code_title"))
        _, _, _, _ = get_legal_code_replaced_rel_path(
            tool.is_replaced_by, path_start, language_code, language_default
        )
        self.assertEqual(
            cache.get("by-4.0--en-replaced_deed_title"),
            "Deed - Attribution 4.0 International",
        )
        self.assertEqual(
            cache.get("by-4.0--en-replaced_legal_code_title"),
            "Legal Code - Attribution 4.0 International",
        )

    def test_normalize_path_and_lang(self):
        request_path = "/licenses/by/3.0/de/legalcode"
        jurisdiction = "de"
        norm_request_path, norm_language_code = normalize_path_and_lang(
            request_path,
            jurisdiction,
            language_code=None,
        )
        self.assertEqual(norm_request_path, f"{request_path}.de")
        self.assertEqual(norm_language_code, "de")
