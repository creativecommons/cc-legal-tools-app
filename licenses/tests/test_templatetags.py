# Third-party
from django.test import TestCase
from django.urls import get_resolver

# First-party/Local
from licenses.models import build_path
from licenses.templatetags.license_tags import (
    current_letter,
    next_letter,
    reset_letters,
    units,
)
from licenses.utils import compute_canonical_url


class LicenseTagsTest(TestCase):
    def test_units(self):
        expected = ["by", "by-nc", "by-nc-nd", "by-nc-sa", "by-nd", "by-sa"]
        data = [
            {"unit": "by-nc-nd"},
            {"unit": "by-nc"},
            {"unit": "by-sa"},
            {"unit": "by"},
            {"unit": "by-nc-sa"},
            {"unit": "by"},
            {"unit": "by-nd"},
        ]
        self.assertEqual(expected, units(data))

    def test_reset_letters(self):
        reset_letters("lowercase")
        self.assertEqual("a", next_letter())
        reset_letters("uppercase")
        self.assertEqual("A", next_letter())
        with self.assertRaises(ValueError):
            reset_letters("InvalidValue")

    def test_next_letter(self):
        reset_letters("lowercase")
        self.assertEqual("a", next_letter())
        self.assertEqual("b", next_letter())

    def test_current_letter(self):
        reset_letters("lowercase")
        self.assertEqual("a", next_letter())
        self.assertEqual("a", current_letter())
        self.assertEqual("a", current_letter())
        self.assertEqual("b", next_letter())
        self.assertEqual("b", current_letter())

    def test_build_license_url(self):
        # https://creativecommons.org/licenses/by/3.0/es/legalcode.es
        data = [
            # (unit, version, jurisdiction, language, expected result)
            (
                "licenses",
                "by",
                "3.0",
                "es",
                "es",
                "/licenses/by/3.0/es/legalcode.es",
            ),
            (
                "licenses",
                "by",
                "4.0",
                "",
                "en",
                "/licenses/by/4.0/legalcode.en",
            ),
            (
                "licenses",
                "by",
                "4.0",
                "",
                "xx",
                "/licenses/by/4.0/legalcode.xx",
            ),
            (
                "licenses",
                "by-nc",
                "2.5",
                "",
                "xx",
                "/licenses/by-nc/2.5/legalcode.xx",
            ),
            (
                "licenses",
                "by-nc",
                "3.5",
                "yy",
                "xx",
                "/licenses/by-nc/3.5/yy/legalcode.xx",
            ),
            (
                "licenses",
                "by",
                "3.0",
                "am",
                "hy",
                "/licenses/by/3.0/am/legalcode.hy",
            ),  # hy is armenian
            (
                "licenses",
                "by",
                "3.0",
                "ge",
                "ka",
                "/licenses/by/3.0/ge/legalcode.ka",
            ),  # georgian
            (
                "licenses",
                "by",
                "3.0",
                "ca",
                "en",
                "/licenses/by/3.0/ca/legalcode.en",
            ),  # canadian
            (
                "licenses",
                "by",
                "3.0",
                "ca",
                "fr",
                "/licenses/by/3.0/ca/legalcode.fr",
            ),  # canadian
            (
                "licenses",
                "by",
                "3.0",
                "ch",
                "de",
                "/licenses/by/3.0/ch/legalcode.de",
            ),
            (
                "licenses",
                "by",
                "3.0",
                "ch",
                "de",
                "/licenses/by/3.0/ch/legalcode.de",
            ),
            (
                "licenses",
                "by",
                "3.0",
                "ch",
                "fr",
                "/licenses/by/3.0/ch/legalcode.fr",
            ),
        ]
        resolver = get_resolver()
        for (
            category,
            unit,
            version,
            jurisdiction,
            language,
            expected_result,
        ) in data:
            with self.subTest(
                (unit, version, jurisdiction, language),
            ):
                canonical_url = compute_canonical_url(
                    category, unit, version, jurisdiction
                )
                result = build_path(canonical_url, "legalcode", language)
                self.assertEqual(expected_result, result)
                self.assertTrue(resolver.resolve(result))

    def test_build_deed_url(self):
        # https://creativecommons.org/licenses/by-sa/4.0/
        # https://creativecommons.org/licenses/by-sa/4.0/deed.es
        # https://creativecommons.org/licenses/by/3.0/es/
        # https://creativecommons.org/licenses/by/3.0/es/deed.fr
        data = [
            # (unit, version, jurisdiction, language, expected result)
            ("licenses", "by-sa", "4.0", "", "", "/licenses/by-sa/4.0/deed"),
            (
                "licenses",
                "by-sa",
                "4.0",
                "",
                "es",
                "/licenses/by-sa/4.0/deed.es",
            ),
            ("licenses", "by", "3.0", "es", "", "/licenses/by/3.0/es/deed"),
            (
                "licenses",
                "by",
                "3.0",
                "es",
                "fr",
                "/licenses/by/3.0/es/deed.fr",
            ),
            ("licenses", "by", "4.0", "", "", "/licenses/by/4.0/deed"),
            ("licenses", "by", "4.0", "", "xx", "/licenses/by/4.0/deed.xx"),
            (
                "licenses",
                "by-nc",
                "2.0",
                "zz",
                "",
                "/licenses/by-nc/2.0/zz/deed",
            ),
            (
                "licenses",
                "by-nc",
                "2.5",
                "",
                "xx",
                "/licenses/by-nc/2.5/deed.xx",
            ),
            (
                "licenses",
                "by-nc",
                "3.5",
                "yy",
                "xx",
                "/licenses/by-nc/3.5/yy/deed.xx",
            ),
        ]
        for (
            category,
            unit,
            version,
            jurisdiction,
            language,
            expected_result,
        ) in data:
            with self.subTest(
                (unit, version, jurisdiction, language),
            ):
                canonical_url = compute_canonical_url(
                    category, unit, version, jurisdiction
                )
                result = build_path(canonical_url, "deed", language)
                self.assertEqual(expected_result, result)
