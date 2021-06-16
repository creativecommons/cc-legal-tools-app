# Standard library
from unittest import mock

# Third-party
import polib
from django.test import TestCase, override_settings
from django.utils.translation import override

# First-party/Local
from i18n import DEFAULT_LANGUAGE_CODE
from licenses import FREEDOM_LEVEL_MAX, FREEDOM_LEVEL_MID, FREEDOM_LEVEL_MIN
from licenses.models import LegalCode, License
from licenses.tests.factories import (
    LegalCodeFactory,
    LicenseFactory,
    TranslationBranchFactory,
)
from licenses.tests.test_transifex import TEST_TRANSIFEX_SETTINGS
from licenses.transifex import TransifexHelper


class LegalCodeQuerySetTest(TestCase):
    def test_translated(self):
        bylicense30ported = LicenseFactory(
            unit="by-nc", version="3.0", jurisdiction_code="ar"
        )
        bylicense30unported = LicenseFactory(
            unit="by-nc", version="3.0", jurisdiction_code=""
        )

        bylicense40 = LicenseFactory(
            unit="by-nc", version="4.0", jurisdiction_code=""
        )

        cc0v1license = LicenseFactory(
            unit="CC0", version="1.0", jurisdiction_code=""
        )

        should_be_translated = [
            LegalCodeFactory(license=bylicense40),
            LegalCodeFactory(license=cc0v1license),
        ]
        should_not_be_translated = [
            LegalCodeFactory(license=bylicense30ported),
            LegalCodeFactory(license=bylicense30unported),
        ]
        self.assertCountEqual(
            should_be_translated, list(LegalCode.objects.translated())
        )
        self.assertCountEqual(
            should_not_be_translated,
            set(LegalCode.objects.all()) - set(LegalCode.objects.translated()),
        )

    def test_valid(self):
        bylicense30ported = LicenseFactory(
            unit="by-nc", version="3.0", jurisdiction_code="ar"
        )
        bylicense30unported = LicenseFactory(
            unit="by-nc", version="3.0", jurisdiction_code=""
        )
        nonbylicense30ported = LicenseFactory(
            unit="xyz", version="3.0", jurisdiction_code="ar"
        )
        nonbylicense30unported = LicenseFactory(
            unit="xyz", version="3.0", jurisdiction_code=""
        )

        bylicense40 = LicenseFactory(
            unit="by-nc", version="4.0", jurisdiction_code=""
        )
        nonbylicense40 = LicenseFactory(
            unit="xyz", version="4.0", jurisdiction_code=""
        )

        cc0v1license = LicenseFactory(
            unit="CC0", version="1.0", jurisdiction_code=""
        )
        noncc0v1license = LicenseFactory(
            unit="xyz", version="1.0", jurisdiction_code=""
        )

        # Test valid()
        should_be_valid = [
            LegalCodeFactory(license=bylicense30ported),
            LegalCodeFactory(license=bylicense30unported),
            LegalCodeFactory(license=bylicense40),
            LegalCodeFactory(license=cc0v1license),
        ]
        should_not_be_valid = [
            LegalCodeFactory(license=nonbylicense30ported),
            LegalCodeFactory(license=nonbylicense30unported),
            LegalCodeFactory(license=nonbylicense40),
            LegalCodeFactory(license=noncc0v1license),
        ]
        self.assertCountEqual(should_be_valid, list(LegalCode.objects.valid()))
        self.assertCountEqual(
            should_not_be_valid,
            set(LegalCode.objects.all()) - set(LegalCode.objects.valid()),
        )
        # Test validgroups()
        self.assertCountEqual(
            should_be_valid,
            list(LegalCode.objects.validgroups()["Licenses 4.0"])
            + list(LegalCode.objects.validgroups()["Licenses 3.0"])
            + list(LegalCode.objects.validgroups()["Public Domain all"]),
        )
        self.assertCountEqual(
            should_not_be_valid,
            set(LegalCode.objects.all())
            - set(
                list(LegalCode.objects.validgroups()["Licenses 4.0"])
                + list(LegalCode.objects.validgroups()["Licenses 3.0"])
                + list(LegalCode.objects.validgroups()["Public Domain all"])
            ),
        )


class LegalCodeModelTest(TestCase):
    def test_str(self):
        LegalCodeFactory()
        legal_code = LegalCode.objects.first()
        self.assertEqual(
            str(legal_code),
            f"LegalCode<{legal_code.language_code},"
            f" {str(legal_code.license)}>",
        )

    def test_translation_domain(self):
        data = [
            # (expected, unit, version, jurisdiction, language)
            ("by-sa_30", "by-sa", "3.0", "", "fr"),
            ("by-sa_30_xx", "by-sa", "3.0", "xx", "fr"),
        ]

        for expected, unit, version, jurisdiction, language in data:
            with self.subTest(expected):
                legalcode = LegalCodeFactory(
                    license__unit=unit,
                    license__version=version,
                    license__jurisdiction_code=jurisdiction,
                    language_code=language,
                )
                self.assertEqual(expected, legalcode.translation_domain)

    @override_settings(DATA_REPOSITORY_DIR="/foo")
    def test_translation_filename(self):
        data = [
            # (expected, unit, version, jurisdiction, language)
            (
                "/foo/legalcode/de/LC_MESSAGES/by-sa_03.po",
                "by-sa",
                "0.3",
                "",
                "de",
            ),
            (
                "/foo/legalcode/de/LC_MESSAGES/by-sa_03_xx.po",
                "by-sa",
                "0.3",
                "xx",
                "de",
            ),
        ]

        for expected, unit, version, jurisdiction, language in data:
            with self.subTest(expected):
                license = LicenseFactory(
                    unit=unit,
                    version=version,
                    jurisdiction_code=jurisdiction,
                )
                self.assertEqual(
                    expected,
                    LegalCodeFactory(
                        license=license, language_code=language
                    ).translation_filename(),
                )

    def test_plain_text_url(self):
        lc0 = LegalCodeFactory(
            license__unit="by",
            license__version="4.0",
            license__jurisdiction_code="",
            language_code="en",
        )
        lc1 = LegalCodeFactory(
            license__unit="by",
            license__version="4.0",
            license__jurisdiction_code="",
            language_code="fr",
        )
        lc2 = LegalCodeFactory(
            license__unit="by",
            license__version="4.0",
            license__jurisdiction_code="",
            language_code="ar",
        )
        self.assertEqual(
            lc0.plain_text_url,
            f"{lc0.license_url.replace('legalcode.en', 'legalcode.txt')}",
        )
        self.assertEqual(lc1.plain_text_url, None)
        self.assertEqual(lc2.plain_text_url, None)

    def test_get_pofile(self):
        legalcode = LegalCodeFactory()
        test_pofile = polib.POFile()
        test_translation_filename = "/dev/null"
        with mock.patch.object(LegalCode, "translation_filename") as mock_tf:
            mock_tf.return_value = test_translation_filename
            with mock.patch.object(polib, "pofile") as mock_pofile:
                mock_pofile.return_value = test_pofile
                result = legalcode.get_pofile()
        mock_pofile.assert_called_with("", encoding="utf-8")
        self.assertEqual(test_pofile, result)

    @override_settings(DATA_REPOSITORY_DIR="/some/dir")
    def test_get_english_pofile(self):
        legalcode = LegalCodeFactory(language_code="es")
        legalcode_en = LegalCodeFactory(
            license=legalcode.license, language_code=DEFAULT_LANGUAGE_CODE
        )
        test_pofile = polib.POFile()

        with mock.patch.object(
            License, "get_legalcode_for_language_code"
        ) as mock_glfl:
            mock_glfl.return_value = legalcode_en
            with mock.patch.object(legalcode_en, "get_pofile") as mock_gp:
                mock_gp.return_value = test_pofile
                self.assertEqual(test_pofile, legalcode.get_english_pofile())
                self.assertEqual(
                    test_pofile, legalcode_en.get_english_pofile()
                )
        mock_glfl.assert_called_with(DEFAULT_LANGUAGE_CODE)
        mock_gp.assert_called_with()

    @override_settings(DATA_REPOSITORY_DIR="/some/dir")
    def test_get_translation_object(self):
        # get_translation_object on the model calls the
        # i18n.utils.get_translation_object.
        legalcode = LegalCodeFactory(
            license__version="4.0",
            license__unit="by-sa",
            language_code="de",
        )

        with mock.patch("licenses.models.get_translation_object") as mock_djt:
            legalcode.get_translation_object()
        mock_djt.assert_called_with(
            domain="by-sa_40", django_language_code="de"
        )

    def test_branch_name(self):
        legalcode = LegalCodeFactory(
            license__version="4.0",
            license__unit="by-sa",
            language_code="de",
        )
        self.assertEqual("cc4-de", legalcode.branch_name())
        legalcode = LegalCodeFactory(
            license__version="3.5",
            license__unit="other",
            language_code="de",
        )
        self.assertEqual("other-35-de", legalcode.branch_name())
        legalcode = LegalCodeFactory(
            license__version="3.5",
            license__unit="other",
            language_code="de",
            license__jurisdiction_code="xyz",
        )
        self.assertEqual("other-35-de-xyz", legalcode.branch_name())

    def test_has_english(self):
        license = LicenseFactory()
        lc_fr = LegalCodeFactory(license=license, language_code="fr")
        self.assertFalse(lc_fr.has_english())
        lc_en = LegalCodeFactory(license=license, language_code="en")
        self.assertTrue(lc_fr.has_english())
        self.assertTrue(lc_en.has_english())

    def _test_get_deed_or_license_path(self, data):
        for (
            category,
            version,
            unit,
            jurisdiction_code,
            language_code,
            expected_deed_path,
            expected_deed_symlinks,
            expected_license_path,
            expected_license_symlinks,
        ) in data:
            license = LicenseFactory(
                category=category,
                unit=unit,
                version=version,
                jurisdiction_code=jurisdiction_code,
            )
            legalcode = LegalCodeFactory(
                license=license, language_code=language_code
            )
            self.assertEqual(
                [expected_deed_path, expected_deed_symlinks],
                legalcode.get_file_and_links("deed"),
            )
            self.assertEqual(
                [expected_license_path, expected_license_symlinks],
                legalcode.get_file_and_links("legalcode"),
            )

    def test_get_deed_or_license_path_by4(self):
        """
        4.0 formula:
        /licenses/VERSION/LICENSE_deed_LANGAUGE.html
        /licenses/VERSION/LICENSE_legalcode_LANGAUGEhtml

        4.0 examples:
        /licenses/4.0/by-nc-nd_deed_en.html
        /licenses/4.0/by-nc-nd_legalcode_en.html
        /licenses/4.0/by_deed_en.html
        /licenses/4.0/by_legalcode_en.html
        /licenses/4.0/by_deed_zh-Hans.html
        /licenses/4.0/by_legalcode_zh-Hans.html
        """
        self._test_get_deed_or_license_path(
            [
                (
                    "licenses",
                    "4.0",
                    "by-nc-nd",
                    "",
                    "en",
                    "licenses/by-nc-nd/4.0/deed.en.html",
                    ["deed.html", "index.html"],
                    "licenses/by-nc-nd/4.0/legalcode.en.html",
                    ["legalcode.html"],
                ),
                (
                    "licenses",
                    "4.0",
                    "by",
                    "",
                    "en",
                    "licenses/by/4.0/deed.en.html",
                    ["deed.html", "index.html"],
                    "licenses/by/4.0/legalcode.en.html",
                    ["legalcode.html"],
                ),
            ]
        )
        self._test_get_deed_or_license_path(
            [
                (
                    "licenses",
                    "4.0",
                    "by",
                    "",
                    "zh-Hans",
                    "licenses/by/4.0/deed.zh-Hans.html",
                    [],
                    "licenses/by/4.0/legalcode.zh-Hans.html",
                    [],
                ),
            ]
        )

    def test_get_deed_or_license_path_by3(self):
        """
        3.0 unported
            Formula
                CATEGORY/UNIT/VERSION/JURISDICTION/DOCUMENT.LANG.html
            Examples
                licenses/by/3.0/deed.en.html
                licenses/by/3.0/legalcode.en.html

        3.0 ported
            Formula
                CATEGORY/UNIT/VERSION/JURISDICTION/DOCUMENT.LANG.html
            Examples
                licenses/by/3.0/ca/deed.en.html
                licenses/by/3.0/ca/legalcode.en.html
                licenses/by-sa/3.0/ca/deed.fr.html
                licenses/by-sa/3.0/ca/legalcode.fr.html
        """
        # Unported
        self._test_get_deed_or_license_path(
            [
                (
                    "licenses",
                    "3.0",
                    "by",
                    "",
                    "en",
                    "licenses/by/3.0/deed.en.html",
                    ["deed.html", "index.html"],
                    "licenses/by/3.0/legalcode.en.html",
                    ["legalcode.html"],
                ),
            ]
        )
        # Ported with multiple languages
        self._test_get_deed_or_license_path(
            [
                (
                    "licenses",
                    "3.0",
                    "by",
                    "ca",
                    "en",
                    "licenses/by/3.0/ca/deed.en.html",
                    ["deed.html", "index.html"],
                    "licenses/by/3.0/ca/legalcode.en.html",
                    ["legalcode.html"],
                ),
            ]
        )
        self._test_get_deed_or_license_path(
            [
                (
                    "licenses",
                    "3.0",
                    "by-sa",
                    "ca",
                    "fr",
                    "licenses/by-sa/3.0/ca/deed.fr.html",
                    [],
                    "licenses/by-sa/3.0/ca/legalcode.fr.html",
                    [],
                ),
            ]
        )
        # Ported with single language
        self._test_get_deed_or_license_path(
            [
                (
                    "licenses",
                    "3.0",
                    "by-nc-nd",
                    "am",
                    "hy",
                    "licenses/by-nc-nd/3.0/am/deed.hy.html",
                    ["deed.html", "index.html"],
                    "licenses/by-nc-nd/3.0/am/legalcode.hy.html",
                    ["legalcode.html"],
                ),
            ]
        )

    def test_get_deed_or_license_path_cc0(self):
        """
        cc0 formula:
        /publicdomain/VERSION/LICENSE_deed_LANGAUGE.html
        /publicdomain/VERSION/LICENSE_legalcode_LANGAUGE.html

        cc0 examples:
        /publicdomain/1.0/zero_deed_en.html
        /publicdomain/1.0/zero_legalcode_en.html
        /publicdomain/1.0/zero_deed_ja.html
        /publicdomain/1.0/zero_legalcode_ja.html
        """
        self._test_get_deed_or_license_path(
            [
                (
                    "publicdomain",
                    "1.0",
                    "CC0",
                    "",
                    "en",
                    "publicdomain/zero/1.0/deed.en.html",
                    ["deed.html", "index.html"],
                    "publicdomain/zero/1.0/legalcode.en.html",
                    ["legalcode.html"],
                ),
            ]
        )
        self._test_get_deed_or_license_path(
            [
                (
                    "publicdomain",
                    "1.0",
                    "CC0",
                    "",
                    "ja",
                    "publicdomain/zero/1.0/deed.ja.html",
                    [],
                    "publicdomain/zero/1.0/legalcode.ja.html",
                    [],
                ),
            ]
        )


class LicenseModelTest(TestCase):
    def test_nc(self):
        self.assertFalse(LicenseFactory(unit="xyz").nc)
        self.assertTrue(LicenseFactory(unit="by-nc-xyz").nc)

    def test_nd(self):
        self.assertFalse(LicenseFactory(unit="xyz").nd)
        self.assertTrue(LicenseFactory(unit="by-nd-xyz").nd)

    def test_sa(self):
        self.assertFalse(LicenseFactory(unit="xyz").sa)
        self.assertTrue(LicenseFactory(unit="xyz-sa").sa)

    def test_get_metadata(self):
        # Ported
        license = LicenseFactory(
            **{
                "canonical_url": (
                    "https://creativecommons.org/licenses/by-nc/3.0/xyz/"
                ),
                "category": "licenses",
                "unit": "by-nc",
                "version": "3.0",
                "title_english": "The Title",
                "jurisdiction_code": "xyz",
                "permits_derivative_works": False,
                "permits_reproduction": False,
                "permits_distribution": True,
                "permits_sharing": True,
                "requires_share_alike": True,
                "requires_notice": True,
                "requires_attribution": True,
                "requires_source_code": True,
                "prohibits_commercial_use": True,
                "prohibits_high_income_nation_use": False,
            }
        )

        LegalCodeFactory(license=license, language_code="pt")
        LegalCodeFactory(license=license, language_code="en")

        data = license.get_metadata()
        expected_data = {
            "jurisdiction": "xyz",
            "unit": "by-nc",
            "permits_derivative_works": False,
            "permits_distribution": True,
            "permits_reproduction": False,
            "permits_sharing": True,
            "prohibits_commercial_use": True,
            "prohibits_high_income_nation_use": False,
            "requires_attribution": True,
            "requires_notice": True,
            "requires_share_alike": True,
            "requires_source_code": True,
            "title_english": "The Title",
            "translations": {
                "en": {
                    "deed": "/licenses/by-nc/3.0/xyz/deed.en",
                    "license": "/licenses/by-nc/3.0/xyz/legalcode.en",
                    "title": "The Title",
                },
                "pt": {
                    "deed": "/licenses/by-nc/3.0/xyz/deed.pt",
                    "license": "/licenses/by-nc/3.0/xyz/legalcode.pt",
                    "title": "The Title",
                },
            },
            "version": "3.0",
        }

        for key in expected_data.keys():
            self.assertEqual(expected_data[key], data[key])

        # Unported
        license = LicenseFactory(
            **{
                "canonical_url": (
                    "https://creativecommons.org/licenses/by-nc/3.0/"
                ),
                "category": "licenses",
                "unit": "by-nc",
                "version": "3.0",
                "title_english": "The Title",
                "jurisdiction_code": "",
                "permits_derivative_works": False,
                "permits_reproduction": False,
                "permits_distribution": True,
                "permits_sharing": True,
                "requires_share_alike": True,
                "requires_notice": True,
                "requires_attribution": True,
                "requires_source_code": True,
                "prohibits_commercial_use": True,
                "prohibits_high_income_nation_use": False,
            }
        )

        LegalCodeFactory(license=license, language_code="en")

        data = license.get_metadata()
        expected_data = {
            "unit": "by-nc",
            "version": "3.0",
            "title_english": "The Title",
            "permits_derivative_works": False,
            "permits_distribution": True,
            "permits_reproduction": False,
            "permits_sharing": True,
            "prohibits_commercial_use": True,
            "prohibits_high_income_nation_use": False,
            "requires_attribution": True,
            "requires_notice": True,
            "requires_share_alike": True,
            "requires_source_code": True,
            "translations": {
                "en": {
                    "deed": "/licenses/by-nc/3.0/deed.en",
                    "license": "/licenses/by-nc/3.0/legalcode.en",
                    "title": "The Title",
                },
            },
        }

        for key in expected_data.keys():
            self.assertEqual(expected_data[key], data[key])

    def test_logos(self):
        # Every license includes "cc-logo"
        self.assertIn("cc-logo", LicenseFactory().logos())
        self.assertEqual(
            ["cc-logo", "cc-zero"], LicenseFactory(unit="CC0").logos()
        )
        self.assertEqual(
            ["cc-logo", "cc-by"],
            LicenseFactory(
                unit="by",
                version="4.0",
                prohibits_commercial_use=False,
                requires_share_alike=False,
                permits_derivative_works=True,
            ).logos(),
        )
        self.assertEqual(
            ["cc-logo", "cc-by", "cc-nc"],
            LicenseFactory(
                unit="by-nc",
                version="3.0",
                prohibits_commercial_use=True,
                requires_share_alike=False,
                permits_derivative_works=True,
            ).logos(),
        )
        self.assertEqual(
            ["cc-logo", "cc-by", "cc-nd"],
            LicenseFactory(
                unit="by-nd",
                version="4.0",
                prohibits_commercial_use=False,
                requires_share_alike=False,
                permits_derivative_works=False,
            ).logos(),
        )
        self.assertEqual(
            ["cc-logo", "cc-by", "cc-sa"],
            LicenseFactory(
                unit="by-sa",
                version="4.0",
                prohibits_commercial_use=False,
                requires_share_alike=True,
                permits_derivative_works=True,
            ).logos(),
        )
        self.assertEqual(
            ["cc-logo", "cc-by", "cc-nc", "cc-sa"],
            LicenseFactory(
                unit="by-nc-sa",
                version="4.0",
                prohibits_commercial_use=True,
                requires_share_alike=True,
                permits_derivative_works=True,
            ).logos(),
        )
        self.assertEqual(
            ["cc-logo", "cc-by", "cc-nc", "cc-sa"],
            LicenseFactory(
                unit="by-nc-sa",
                version="3.0",
                prohibits_commercial_use=True,
                requires_share_alike=True,
                permits_derivative_works=True,
            ).logos(),
        )

    def test_get_legalcode_for_language_code(self):
        license = LicenseFactory()

        lc_pt = LegalCodeFactory(license=license, language_code="pt")
        lc_en = LegalCodeFactory(license=license, language_code="en")

        with override(language="pt"):
            result = license.get_legalcode_for_language_code(None)
            self.assertEqual(lc_pt.id, result.id)
        result = license.get_legalcode_for_language_code("pt")
        self.assertEqual(lc_pt.id, result.id)
        result = license.get_legalcode_for_language_code("en")
        self.assertEqual(lc_en.id, result.id)
        with self.assertRaises(LegalCode.DoesNotExist):
            license.get_legalcode_for_language_code("en_us")
        result = license.get_legalcode_for_language_code("en-us")
        self.assertEqual(lc_en.id, result.id)

    def test_resource_name(self):
        license = LicenseFactory(
            unit="qwerty", version="2.7", jurisdiction_code="zys"
        )
        self.assertEqual("QWERTY 2.7 ZYS", license.resource_name)
        license = LicenseFactory(
            unit="qwerty", version="2.7", jurisdiction_code=""
        )
        self.assertEqual("QWERTY 2.7", license.resource_name)

    def test_resource_slug(self):
        license = LicenseFactory(
            unit="qwerty", version="2.7", jurisdiction_code="zys"
        )
        self.assertEqual("qwerty_27_zys", license.resource_slug)
        license = LicenseFactory(
            unit="qwerty", version="2.7", jurisdiction_code=""
        )
        self.assertEqual("qwerty_27", license.resource_slug)

    def test_str(self):
        license = LicenseFactory(
            unit="bx-oh", version="1.3", jurisdiction_code="any"
        )
        self.assertEqual(
            str(license),
            f"License<{license.unit},{license.version},"
            f"{license.jurisdiction_code}>",
        )

    def test_rdf(self):
        license = LicenseFactory(
            unit="bx-oh", version="1.3", jurisdiction_code="any"
        )
        self.assertEqual("RDF Generation Not Implemented", license.rdf())

    # def test_default_language_code(self):
    #     license = LicenseFactory(
    #         unit="bx-oh", version="1.3", jurisdiction_code=""
    #     )
    #     self.assertEqual(
    #         DEFAULT_LANGUAGE_CODE, license.default_language_code()
    #     )
    #     license = LicenseFactory(
    #         unit="bx-oh", version="1.3", jurisdiction_code="fr"
    #     )
    #     self.assertEqual("fr", license.default_language_code())
    #
    # def test_get_deed_url(self):
    #     # https://creativecommons.org/licenses/by-sa/4.0/
    #     # https://creativecommons.org/licenses/by-sa/4.0/deed.es
    #     # https://creativecommons.org/licenses/by/3.0/es/
    #     # https://creativecommons.org/licenses/by/3.0/es/deed.fr
    #     license = LicenseFactory(
    #         unit="bx-oh", version="1.3", jurisdiction_code="ae"
    #     )
    #     self.assertEqual("/licenses/bx-oh/1.3/ae/", license.deed_url)
    #     license = LicenseFactory(
    #         unit="bx-oh", version="1.3", jurisdiction_code=""
    #     )
    #     self.assertEqual("/licenses/bx-oh/1.3/", license.deed_url)
    #
    # def test_get_deed_url_for_language(self):
    #     license = LicenseFactory(
    #         unit="bx-oh", version="1.3", jurisdiction_code="ae"
    #     )
    #     self.assertEqual(
    #         "/licenses/bx-oh/1.3/ae/deed.fr",
    #         license.get_deed_url_for_language("fr"),
    #     )
    #     license = LicenseFactory(
    #         unit="bx-oh", version="1.3", jurisdiction_code=""
    #     )
    #     self.assertEqual(
    #         "/licenses/bx-oh/1.3/deed.es",
    #         license.get_deed_url_for_language("es"),
    #     )

    def test_sampling_plus(self):
        self.assertTrue(LicenseFactory(unit="nc-sampling+").sampling_plus)
        self.assertTrue(LicenseFactory(unit="sampling+").sampling_plus)
        self.assertFalse(LicenseFactory(unit="sampling").sampling_plus)
        self.assertFalse(LicenseFactory(unit="MIT").sampling_plus)
        self.assertFalse(LicenseFactory(unit="by-nc-nd-sa").sampling_plus)

    def test_level_of_freedom(self):
        data = [
            ("by", FREEDOM_LEVEL_MAX),
            ("devnations", FREEDOM_LEVEL_MIN),
            ("sampling", FREEDOM_LEVEL_MIN),
            ("sampling+", FREEDOM_LEVEL_MID),
            ("by-nc", FREEDOM_LEVEL_MID),
            ("by-nd", FREEDOM_LEVEL_MID),
            ("by-sa", FREEDOM_LEVEL_MAX),
        ]
        for unit, expected_freedom in data:
            with self.subTest(unit):
                license = LicenseFactory(unit=unit)
                self.assertEqual(expected_freedom, license.level_of_freedom)

    @override_settings(
        TRANSIFEX=TEST_TRANSIFEX_SETTINGS,
        DATA_REPOSITORY_DIR="/trans/repo",
    )
    def test_tx_upload_messages(self):
        language_code = "es"
        legalcode = LegalCodeFactory(language_code=language_code)
        license = legalcode.license
        test_pofile = polib.POFile()
        with mock.patch.object(
            license, "get_legalcode_for_language_code"
        ) as mock_glflc:
            mock_glflc.return_value = legalcode
            with mock.patch.object(
                TransifexHelper, "upload_messages_to_transifex"
            ) as mock_umtt:
                with mock.patch.object(
                    LegalCode, "get_pofile"
                ) as mock_get_pofile:
                    mock_get_pofile.return_value = test_pofile
                    license.tx_upload_messages()
        mock_glflc.assert_called_with("en")
        mock_umtt.assert_called_with(legalcode=legalcode)

    def test_superseded(self):
        lic1 = LicenseFactory()
        lic2 = LicenseFactory(is_replaced_by=lic1)
        self.assertTrue(lic2.superseded)
        self.assertFalse(lic1.superseded)


class TranslationBranchModelTest(TestCase):
    def test_str(self):
        tc = TranslationBranchFactory(complete=False)
        expected = f"Translation branch {tc.branch_name}. In progress."
        self.assertEqual(expected, str(tc))

    def test_stats(self):
        language_code = "es"
        lc1 = LegalCodeFactory(language_code=language_code)
        tb = TranslationBranchFactory(
            language_code=language_code, legalcodes=[lc1]
        )

        class MockPofile(list):
            def untranslated_entries(self):
                return [1, 2, 3, 4, 5]

            def translated_entries(self):
                return [1, 2, 3]

        mock_pofile = MockPofile()
        with mock.patch.object(LegalCode, "get_pofile") as mock_get_pofile:
            mock_get_pofile.return_value = mock_pofile
            stats = tb.stats
        self.assertEqual(
            {
                "percent_messages_translated": 37,
                "number_of_total_messages": 8,
                "number_of_translated_messages": 3,
                "number_of_untranslated_messages": 5,
            },
            stats,
        )
