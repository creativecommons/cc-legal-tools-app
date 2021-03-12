# Third-party
from django.test import TestCase
from django.urls import get_resolver

# First-party/Local
from licenses.models import build_deed_url, build_license_url
from licenses.templatetags.license_tags import (
    current_letter,
    next_letter,
    reset_letters,
)


class LicenseTagsTest(TestCase):
    def test_reset_letters(self):
        reset_letters("lowercase")
        self.assertEqual("a", next_letter())
        reset_letters("uppercase")
        self.assertEqual("A", next_letter())

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
            # (license code, version, jurisdiction, language, expected result)
            ("by", "3.0", "es", "es", "/licenses/by/3.0/es/legalcode.es"),
            ("by", "4.0", "", "en", "/licenses/by/4.0/legalcode"),
            ("by", "4.0", "", "xx", "/licenses/by/4.0/legalcode.xx"),
            ("by-nc", "2.5", "", "xx", "/licenses/by-nc/2.5/legalcode.xx"),
            (
                "by-nc",
                "3.5",
                "yy",
                "xx",
                "/licenses/by-nc/3.5/yy/legalcode.xx",
            ),
            (
                "by",
                "3.0",
                "am",
                "hy",
                "/licenses/by/3.0/am/legalcode",
            ),  # hy is armenian
            (
                "by",
                "3.0",
                "ge",
                "ka",
                "/licenses/by/3.0/ge/legalcode",
            ),  # georgian
            (
                "by",
                "3.0",
                "ca",
                "en",
                "/licenses/by/3.0/ca/legalcode.en",
            ),  # canadian
            (
                "by",
                "3.0",
                "ca",
                "fr",
                "/licenses/by/3.0/ca/legalcode.fr",
            ),  # canadian
            ("by", "3.0", "ch", "de", "/licenses/by/3.0/ch/legalcode.de"),
            ("by", "3.0", "ch", "de", "/licenses/by/3.0/ch/legalcode.de"),
            ("by", "3.0", "ch", "fr", "/licenses/by/3.0/ch/legalcode.fr"),
        ]
        resolver = get_resolver()
        for (
            license_code,
            version,
            jurisdiction,
            language,
            expected_result,
        ) in data:
            with self.subTest(
                (license_code, version, jurisdiction, language),
            ):
                result = build_license_url(
                    license_code, version, jurisdiction, language
                )
                self.assertEqual(expected_result, result)
                self.assertTrue(resolver.resolve(result))

    def test_build_deed_url(self):
        # https://creativecommons.org/licenses/by-sa/4.0/
        # https://creativecommons.org/licenses/by-sa/4.0/deed.es
        # https://creativecommons.org/licenses/by/3.0/es/
        # https://creativecommons.org/licenses/by/3.0/es/deed.fr
        data = [
            # (license code, version, jurisdiction, language, expected result)
            ("by-sa", "4.0", "", "", "/licenses/by-sa/4.0/"),
            ("by-sa", "4.0", "", "es", "/licenses/by-sa/4.0/deed.es"),
            ("by", "3.0", "es", "", "/licenses/by/3.0/es/"),
            ("by", "3.0", "es", "fr", "/licenses/by/3.0/es/deed.fr"),
            ("by", "4.0", "", "", "/licenses/by/4.0/"),
            ("by", "4.0", "", "xx", "/licenses/by/4.0/deed.xx"),
            ("by-nc", "2.0", "zz", "", "/licenses/by-nc/2.0/zz/"),
            ("by-nc", "2.5", "", "xx", "/licenses/by-nc/2.5/deed.xx"),
            ("by-nc", "3.5", "yy", "xx", "/licenses/by-nc/3.5/yy/deed.xx"),
        ]
        for (
            license_code,
            version,
            jurisdiction,
            language,
            expected_result,
        ) in data:
            with self.subTest(
                (license_code, version, jurisdiction, language),
            ):
                result = build_deed_url(
                    license_code, version, jurisdiction, language
                )
                self.assertEqual(expected_result, result)
