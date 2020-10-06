from unittest import mock
from unittest.mock import call

import polib
from django.test import TestCase, override_settings
from django.utils.translation import override

import i18n.utils
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


class LegalCodeModelTest(TestCase):
    fixtures = ["licenses.json"]

    def test_str(self):
        legal_code = LegalCode.objects.first()
        self.assertEqual(
            str(legal_code),
            f"LegalCode<{legal_code.language_code}, {legal_code.license.about}>",
        )

    def test_translation_domain(self):
        data = [
            # ("expected", "license_code", "version", "jurisdiction", "language")
            ("by-sa_30", "by-sa", "3.0", "", "fr"),
            ("by-sa_30_xx", "by-sa", "3.0", "xx", "fr"),
        ]

        for expected, license_code, version, jurisdiction, language in data:
            with self.subTest(expected):
                legalcode = LegalCodeFactory(
                    license__license_code=license_code,
                    license__version=version,
                    license__jurisdiction_code=jurisdiction,
                    language_code=language,
                )
                self.assertEqual(expected, legalcode.translation_domain)

    @override_settings(TRANSLATION_REPOSITORY_DIRECTORY="/foo")
    def test_translation_filename(self):
        data = [
            # ("expected", license_code, version, jurisdiction, language),
            ("/foo/legalcode/de/LC_MESSAGES/by-sa_03.po", "by-sa", "0.3", "", "de"),
            (
                "/foo/legalcode/de/LC_MESSAGES/by-sa_03_xx.po",
                "by-sa",
                "0.3",
                "xx",
                "de",
            ),
        ]

        for expected, license_code, version, jurisdiction, language in data:
            with self.subTest(expected):
                license = LicenseFactory(
                    license_code=license_code,
                    version=version,
                    jurisdiction_code=jurisdiction,
                )
                self.assertEqual(
                    expected,
                    LegalCodeFactory(
                        license=license, language_code=language
                    ).translation_filename(),
                )

    def test_license_url(self):
        lc = LegalCodeFactory()
        with mock.patch("licenses.models.build_license_url") as mock_build:
            lc.license_url()
        self.assertEqual(
            [
                call(
                    lc.license.license_code,
                    lc.license.version,
                    lc.license.jurisdiction_code,
                    lc.language_code,
                )
            ],
            mock_build.call_args_list,
        )

    def test_deed_url(self):
        lc = LegalCodeFactory()
        with mock.patch("licenses.models.build_deed_url") as mock_build:
            lc.deed_url()
        self.assertEqual(
            [
                call(
                    lc.license.license_code,
                    lc.license.version,
                    lc.license.jurisdiction_code,
                    lc.language_code,
                )
            ],
            mock_build.call_args_list,
        )

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

    @override_settings(TRANSLATION_REPOSITORY_DIRECTORY="/some/dir")
    def test_get_english_pofile(self):
        legalcode = LegalCodeFactory(language_code="es")
        legalcode_en = LegalCodeFactory(
            license=legalcode.license, language_code=DEFAULT_LANGUAGE_CODE
        )
        test_pofile = polib.POFile()

        with mock.patch.object(License, "get_legalcode_for_language_code") as mock_glfl:
            mock_glfl.return_value = legalcode_en
            with mock.patch.object(legalcode_en, "get_pofile") as mock_gp:
                mock_gp.return_value = test_pofile
                self.assertEqual(test_pofile, legalcode.get_english_pofile())
                self.assertEqual(test_pofile, legalcode_en.get_english_pofile())
        mock_glfl.assert_called_with(DEFAULT_LANGUAGE_CODE)
        mock_gp.assert_called_with()

    @override_settings(TRANSLATION_REPOSITORY_DIRECTORY="/some/dir")
    def test_get_translation_object(self):
        # get_translation_object on the model calls the i18n.utils.get_translation_object.
        legalcode = LegalCodeFactory(
            license__version="4.0", license__license_code="by-sa", language_code="de"
        )

        i18n.utils.get_translation_object.cache_clear()
        with mock.patch("licenses.models.get_translation_object") as mock_djt:
            legalcode.get_translation_object()
        mock_djt.assert_called_with(domain="by-sa_40", language_code="de")

    def test_branch_name(self):
        legalcode = LegalCodeFactory(
            license__version="4.0", license__license_code="by-sa", language_code="de"
        )
        self.assertEqual("cc4-de", legalcode.branch_name())
        legalcode = LegalCodeFactory(
            license__version="3.5", license__license_code="other", language_code="de"
        )
        self.assertEqual("other-35-de", legalcode.branch_name())
        legalcode = LegalCodeFactory(
            license__version="3.5",
            license__license_code="other",
            language_code="de",
            license__jurisdiction_code="xyz",
        )
        self.assertEqual("other-35-de-xyz", legalcode.branch_name())


# Many of these tests mostly are based on whether the metadata import worked right, and
# we're not importing metadata for the time being.
class LicenseModelTest(TestCase):
    # fixtures = ["licenses.json"]

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
            license_code="qwerty", version="2.7", jurisdiction_code="zys"
        )
        self.assertEqual("QWERTY 2.7 ZYS", license.resource_name)
        license = LicenseFactory(
            license_code="qwerty", version="2.7", jurisdiction_code=""
        )
        self.assertEqual("QWERTY 2.7", license.resource_name)

    def test_resource_slug(self):
        license = LicenseFactory(
            license_code="qwerty", version="2.7", jurisdiction_code="zys"
        )
        self.assertEqual("qwerty_27_zys", license.resource_slug)
        license = LicenseFactory(
            license_code="qwerty", version="2.7", jurisdiction_code=""
        )
        self.assertEqual("qwerty_27", license.resource_slug)

    def test_str(self):
        license = LicenseFactory(
            license_code="bx-oh", version="1.3", jurisdiction_code="any"
        )
        self.assertEqual(str(license), f"License<{license.about}>")

    def test_rdf(self):
        license = LicenseFactory(
            license_code="bx-oh", version="1.3", jurisdiction_code="any"
        )
        self.assertEqual("RDF Generation Not Implemented", license.rdf())

    # def test_default_language_code(self):
    #     license = LicenseFactory(license_code="bx-oh", version="1.3", jurisdiction_code="")
    #     self.assertEqual(DEFAULT_LANGUAGE_CODE, license.default_language_code())
    #     license = LicenseFactory(license_code="bx-oh", version="1.3", jurisdiction_code="fr")
    #     self.assertEqual("fr", license.default_language_code())

    # def test_get_deed_url(self):
    #     # https://creativecommons.org/licenses/by-sa/4.0/
    #     # https://creativecommons.org/licenses/by-sa/4.0/deed.es
    #     # https://creativecommons.org/licenses/by/3.0/es/
    #     # https://creativecommons.org/licenses/by/3.0/es/deed.fr
    #     license = LicenseFactory(license_code="bx-oh", version="1.3", jurisdiction_code="ae")
    #     self.assertEqual("/licenses/bx-oh/1.3/ae/", license.get_deed_url())
    #     license = LicenseFactory(license_code="bx-oh", version="1.3", jurisdiction_code="")
    #     self.assertEqual("/licenses/bx-oh/1.3/", license.get_deed_url())

    # def test_get_deed_url_for_language(self):
    #     license = LicenseFactory(license_code="bx-oh", version="1.3", jurisdiction_code="ae")
    #     self.assertEqual("/licenses/bx-oh/1.3/ae/deed.fr", license.get_deed_url_for_language("fr"))
    #     license = LicenseFactory(license_code="bx-oh", version="1.3", jurisdiction_code="")
    #     self.assertEqual("/licenses/bx-oh/1.3/deed.es", license.get_deed_url_for_language("es"))

    def test_sampling_plus(self):
        self.assertTrue(LicenseFactory(license_code="nc-sampling+").sampling_plus)
        self.assertTrue(LicenseFactory(license_code="sampling+").sampling_plus)
        self.assertFalse(LicenseFactory(license_code="sampling").sampling_plus)
        self.assertFalse(LicenseFactory(license_code="MIT").sampling_plus)
        self.assertFalse(LicenseFactory(license_code="by-nc-nd-sa").sampling_plus)

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
        for license_code, expected_freedom in data:
            with self.subTest(license_code):
                license = LicenseFactory(license_code=license_code)
                self.assertEqual(expected_freedom, license.level_of_freedom)

    @override_settings(
        TRANSIFEX=TEST_TRANSIFEX_SETTINGS,
        TRANSLATION_REPOSITORY_DIRECTORY="/trans/repo",
    )
    def test_tx_upload_messages(self):
        legalcode = LegalCodeFactory(language_code=DEFAULT_LANGUAGE_CODE)
        license = legalcode.license
        test_pofile = polib.POFile()
        with mock.patch.object(
            license, "get_legalcode_for_language_code"
        ) as mock_glflc:
            mock_glflc.return_value = legalcode
            with mock.patch.object(
                TransifexHelper, "upload_messages_to_transifex"
            ) as mock_umtt:
                with mock.patch.object(LegalCode, "get_pofile") as mock_get_pofile:
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
    def test_stats(self):
        language_code = "es"
        lc1 = LegalCodeFactory(language_code=language_code)
        tb = TranslationBranchFactory(language_code=language_code, legalcodes=[lc1])

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
