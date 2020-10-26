from django.test import TestCase
from django.urls import get_resolver

from licenses.templatetags.license_tags import (
    build_deed_url,
    build_license_url,
    home_box,
)
from licenses.tests.factories import LegalCodeFactory, LicenseFactory


class LicenseTagsTest(TestCase):
    def test_home_box_no_licenses(self):
        # We don't create any licenses for home_box to link to
        out = home_box("nope", "0.0", "klingon")
        self.assertEqual("", out)

    def test_home_box_two_legalcodes(self):
        license_code = "by"
        version = "4.0"
        language_code = "es"
        license = LicenseFactory(license_code=license_code, version=version)
        l1 = LegalCodeFactory(license=license, language_code=language_code)
        LegalCodeFactory(license=license, language_code=language_code)
        out = home_box(license_code, version, language_code)
        deed_link = l1.deed_url()
        license_link = l1.license_url()
        expected = (
            f"""<a href="{deed_link}">Deed</a> <a href="{license_link}">License</a>"""
        )
        expected = expected + "<br/>" + expected
        self.assertEqual(expected, out)

    def test_build_license_url(self):
        # https://creativecommons.org/licenses/by/3.0/es/legalcode.es
        data = [
            # (license code, version, jurisdiction, language, expected result)
            ("by", "3.0", "es", "es", "/licenses/by/3.0/es/legalcode.es"),
            ("by", "4.0", "", "", "/licenses/by/4.0/legalcode"),
            ("by", "4.0", "", "xx", "/licenses/by/4.0/legalcode.xx"),
            ("by-nc", "2.0", "zz", "", "/licenses/by-nc/2.0/zz/legalcode"),
            ("by-nc", "2.5", "", "xx", "/licenses/by-nc/2.5/legalcode.xx"),
            ("by-nc", "3.5", "yy", "xx", "/licenses/by-nc/3.5/yy/legalcode.xx"),
        ]
        resolver = get_resolver()
        for license_code, version, jurisdiction, language, expected_result in data:
            with self.subTest((license_code, version, jurisdiction, language),):
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
        for license_code, version, jurisdiction, language, expected_result in data:
            with self.subTest((license_code, version, jurisdiction, language),):
                result = build_deed_url(license_code, version, jurisdiction, language)
                self.assertEqual(expected_result, result)
