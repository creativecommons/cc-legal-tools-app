from django.test import TestCase
from licenses.constants import (
    EXCLUDED_LANGUAGE_IDENTIFIERS,
    EXCLUDED_LICENSE_VERSIONS
)
from licenses.models import License
from licenses.utils import (
    get_code_from_jurisdiction_url,
    get_license_url_from_legalcode_url,
    get_licenses_code_and_version,
    get_licenses_code_version_jurisdiction,
    get_licenses_code_version_jurisdiction_lang,
    get_licenses_code_version_lang,
    parse_legalcode_filename,
)
from .factories import LicenseFactory


class GetJurisdictionCodeTest(TestCase):
    def test_get_code_from_jurisdiction_url(self):
        # Just returns the last portion of the path
        self.assertEqual(
            "foo", get_code_from_jurisdiction_url("http://example.com/bar/foo/")
        )
        self.assertEqual(
            "foo", get_code_from_jurisdiction_url("http://example.com/bar/foo")
        )
        self.assertEqual("", get_code_from_jurisdiction_url("http://example.com"))


class ParseLegalcodeFilenameTest(TestCase):
    # Test parse_legalcode_filename
    def test_parse_legalcode_filename(self):
        data = [
            (
                "by_1.0.html",
                {
                    "url": "http://creativecommons.org/licenses/by/1.0/",
                    "license_code": "by",
                    "version": "1.0",
                    "jurisdiction_code": "",
                    "language_code": "",
                },
            ),
            (
                "by_3.0_es_ast",
                {
                    "url": "http://creativecommons.org/licenses/by/3.0/es/legalcode.ast",
                    "license_code": "by",
                    "version": "3.0",
                    "jurisdiction_code": "es",
                    "language_code": "ast",
                },
            ),
            (
                "by_3.0_rs_sr-Cyrl.html",
                {
                    "url": "http://creativecommons.org/licenses/by/3.0/rs/legalcode.sr-Cyrl",
                    "license_code": "by",
                    "version": "3.0",
                    "jurisdiction_code": "rs",
                    "language_code": "sr-Cyrl",
                },
            ),
            (
                "devnations_2.0.html",
                {
                    "url": "http://creativecommons.org/licenses/devnations/2.0/",
                    "license_code": "devnations",
                    "version": "2.0",
                    "jurisdiction_code": "",
                    "language_code": "",
                },
            ),
            (
                "LGPL_2.1.html",
                {
                    "url": "http://creativecommons.org/licenses/LGPL/2.1/",
                    "license_code": "LGPL",
                    "version": "2.1",
                    "jurisdiction_code": "",
                    "language_code": "",
                },
            ),
            (
                "samplingplus_1.0",
                {
                    "url": "http://creativecommons.org/licenses/sampling+/1.0/",
                    "license_code": "sampling+",
                    "version": "1.0",
                    "jurisdiction_code": "",
                    "language_code": "",
                },
            ),
            (
                "zero_1.0_fi.html",
                {
                    "url": "http://creativecommons.org/publicdomain/zero/1.0/legalcode.fi",
                    "license_code": "CC0",
                    "version": "1.0",
                    "jurisdiction_code": "",
                    "language_code": "fi",
                },
            ),
            (
                "nc-samplingplus_1.0.html",
                {
                    "url": "http://creativecommons.org/licenses/nc-sampling+/1.0/",
                    "license_code": "nc-sampling+",
                    "version": "1.0",
                    "jurisdiction_code": "",
                    "language_code": "",
                },
            ),
        ]
        for filename, expected_result in data:
            with self.subTest(filename):
                result = parse_legalcode_filename(filename)
                if result != expected_result:
                    print(repr(result))
                self.assertEqual(expected_result, result)


class GetLicenseURLFromLegalCodeURLTest(TestCase):
    # get_license_url_from_legalcode_url
    def test_get_license_url_from_legalcode_url(self):
        data = [
            (
                "http://creativecommons.org/licenses/by/4.0/legalcode",
                "http://creativecommons.org/licenses/by/4.0/",
            ),
            (
                "http://creativecommons.org/licenses/by/4.0/legalcode.es",
                "http://creativecommons.org/licenses/by/4.0/",
            ),
            (
                "http://creativecommons.org/licenses/GPL/2.0/legalcode",
                "http://creativecommons.org/licenses/GPL/2.0/",
            ),
            (
                "http://creativecommons.org/licenses/nc-sampling+/1.0/tw/legalcode",
                "http://creativecommons.org/licenses/nc-sampling+/1.0/tw/",
            ),
            # Exceptions:
            (
                "http://opensource.org/licenses/bsd-license.php",
                "http://creativecommons.org/licenses/BSD/",
            ),
            (
                "http://opensource.org/licenses/mit-license.php",
                "http://creativecommons.org/licenses/MIT/",
            ),
        ]
        for legalcode_url, expected_license_url in data:
            with self.subTest(legalcode_url):
                self.assertEqual(
                    expected_license_url,
                    get_license_url_from_legalcode_url(legalcode_url),
                )
        with self.assertRaises(ValueError):
            get_license_url_from_legalcode_url(
                "http://opensource.org/licences/bsd-license.php"
            )


class GetLicenseUtilityTest(TestCase):
    """Test django-distill utility functions for
    generating an iterable of license dictionaries
    """

    def setUp(self):
        self.license1 = LicenseFactory(license_code="by", version="4.0")
        self.license2 = LicenseFactory(license_code="by-nc", version="4.0")
        self.license3 = LicenseFactory(license_code="by-nd", version="3.0", jurisdiction_code="hk")
        self.license4 = LicenseFactory(license_code="by-nc-sa", version="3.0", jurisdiction_code="us")
        self.license5 = LicenseFactory(license_code="by-na", version="3.0", jurisdiction_code="nl")
        self.license6 = LicenseFactory(license_code="by", version="")  # zero
        self.license7 = LicenseFactory(license_code="by", version="2.5")
        self.license8 = LicenseFactory(license_code="by", version="2.0")
        self.license9 = LicenseFactory(license_code="by", version="2.1")

    def test_get_licenses_code_and_version(self):
        """Should return an iterable of license dictionaries
        with the dictionary keys (license_code, version)

        Excluding all versions other than 4.0 licenses
        """
        licenses = list(License.objects.exclude(version__in=EXCLUDED_LICENSE_VERSIONS))
        list_of_licenses_dict = [
            {"license_code": l.license_code, "version": l.version} for l in licenses
        ]
        yielded_licenses = get_licenses_code_and_version()
        yielded_license_list = list(yielded_licenses)
        self.assertEqual(list_of_licenses_dict, yielded_license_list)

    def test_get_licenses_code_version_lang(self):
        """Should return an iterable of license dictionaries
        with the dictionary keys (license_code, version, target_lang)

        Excluding all versions other than 4.0 licenses
        """
        list_of_licenses_dict = []
        yielded_licenses = get_licenses_code_version_lang()
        yielded_license_list = list(yielded_licenses)
        for license in License.objects.exclude(version__in=EXCLUDED_LICENSE_VERSIONS):
            for translated_license in license.names.all():
                if (
                    translated_license.language_code
                    not in EXCLUDED_LANGUAGE_IDENTIFIERS
                ):
                    return list_of_licenses_dict.append(
                        {
                            "license_code": license.license_code,
                            "version": license.version,
                            "target_lang": translated_license.language_code,
                        }
                    )
                return
        self.assertEqual(list_of_licenses_dict, yielded_license_list)

    def test_get_licenses_code_version_jurisdiction(self):
        """Should return an iterable of license dictionaries
        with the dictionary keys (license_code, version, jurisdiction)

        4.0 licenses do not have jurisdiction, we should expect an empty result
        """
        list_of_licenses_dict = []
        yielded_licenses = get_licenses_code_version_jurisdiction()
        yielded_license_list = list(yielded_licenses)
        for license in License.objects.exclude(version__in=EXCLUDED_LICENSE_VERSIONS):
            if license.jurisdiction_code:
                return list_of_licenses_dict.append(
                    {
                        "license_code": license.license_code,
                        "version": license.version,
                        "jurisdiction": license.jurisdiction_code,
                    }
                )
            return
        self.assertEqual([], yielded_license_list)
        self.assertEqual(list_of_licenses_dict, yielded_license_list)

    def test_get_licenses_code_version_jurisdiction_lang(self):
        """Should return an iterable of license dictionaries
        with the dictionary keys (license_code, version, jurisdiction,
        target_lang)

        4.0 licenses do not have jurisdiction, we should expect an empty result
        """
        list_of_licenses_dict = []
        yielded_licenses = get_licenses_code_version_jurisdiction_lang()
        yielded_license_list = list(yielded_licenses)
        for license in License.objects.exclude(version__in=EXCLUDED_LICENSE_VERSIONS):
            for translated_license in license.names.all():
                if (
                    translated_license.language_code
                    not in EXCLUDED_LANGUAGE_IDENTIFIERS
                    and license.jurisdiction_code
                ):
                    return list_of_licenses_dict.append(
                        {
                            "license_code": license.license_code,
                            "version": license.version,
                            "jurisdiction": license.jurisdiction_code,
                            "target_lang": translated_license.language_code,
                        }
                    )
                return
        self.assertEqual([], yielded_license_list)
        self.assertEqual(list_of_licenses_dict, yielded_license_list)
