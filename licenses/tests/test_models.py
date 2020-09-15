from unittest import mock
from unittest.mock import call

from django.test import TestCase
from django.utils import translation

from licenses import FREEDOM_LEVEL_MAX, FREEDOM_LEVEL_MID, FREEDOM_LEVEL_MIN
from licenses.models import LegalCode, TranslatedLicenseName
from licenses.tests.factories import (
    LegalCodeFactory,
    LicenseFactory,
    TranslatedLicenseNameFactory,
)


class LegalCodeModelTest(TestCase):
    fixtures = ["licenses.json"]

    def test_str(self):
        legal_code = LegalCode.objects.first()
        self.assertEqual(
            str(legal_code),
            f"LegalCode<{legal_code.language_code}, {legal_code.license.about}>",
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

    def help_test_downstreams(self, code):
        # mock the translation
        with mock.patch.object(
            LegalCode, "get_translation_object"
        ) as mock_get_translation_object:
            mock_get_translation_object.return_value.translate.return_value = "qwerty"
            return LegalCodeFactory(license__license_code=code).downstreams()

    def test_downstreams(self):
        with self.subTest("by"):
            result = self.help_test_downstreams("by")
            expected = [
                {
                    "id": "s2a5A_offer",
                    "msgid_name": "s2a5_license_grant_downstream_offer_name",
                    "msgid_text": "s2a5_license_grant_downstream_offer_text",
                    "name_translation": "qwerty",
                    "text_translation": "qwerty",
                },
                {
                    "id": "s2a5B_no_restrictions",
                    "msgid_name": "s2a5_license_grant_downstream_no_restrictions_name",
                    "msgid_text": "s2a5_license_grant_downstream_no_restrictions_text",
                    "name_translation": "qwerty",
                    "text_translation": "qwerty",
                },
            ]
            self.assertEqual(expected, result)
        with self.subTest("by-sa"):
            result = self.help_test_downstreams("by-sa")
            expected = [
                {
                    "id": "s2a5A_offer",
                    "msgid_name": "s2a5_license_grant_downstream_offer_name",
                    "msgid_text": "s2a5_license_grant_downstream_offer_text",
                    "name_translation": "qwerty",
                    "text_translation": "qwerty",
                },
                {
                    "id": "s2a5B_adapted_material",
                    "msgid_name": "s2a5_license_grant_downstream_adapted_material_name",
                    "msgid_text": "s2a5_license_grant_downstream_adapted_material_text",
                    "name_translation": "qwerty",
                    "text_translation": "qwerty",
                },
                {
                    "id": "s2a5C_no_restrictions",
                    "msgid_name": "s2a5_license_grant_downstream_no_restrictions_name",
                    "msgid_text": "s2a5_license_grant_downstream_no_restrictions_text",
                    "name_translation": "qwerty",
                    "text_translation": "qwerty",
                },
            ]

            self.assertEqual(expected, result)
        with self.subTest("by-nc-sa"):
            result = self.help_test_downstreams("by-nc-sa")
            expected = [
                {
                    "id": "s2a5A_offer",
                    "msgid_name": "s2a5_license_grant_downstream_offer_name",
                    "msgid_text": "s2a5_license_grant_downstream_offer_text",
                    "name_translation": "qwerty",
                    "text_translation": "qwerty",
                },
                {
                    "id": "s2a5B_adapted_material",
                    "msgid_name": "s2a5_license_grant_downstream_adapted_material_name",
                    "msgid_text": "s2a5_license_grant_downstream_adapted_material_text",
                    "name_translation": "qwerty",
                    "text_translation": "qwerty",
                },
                {
                    "id": "s2a5C_no_restrictions",
                    "msgid_name": "s2a5_license_grant_downstream_no_restrictions_name",
                    "msgid_text": "s2a5_license_grant_downstream_no_restrictions_text",
                    "name_translation": "qwerty",
                    "text_translation": "qwerty",
                },
            ]
            self.assertEqual(expected, result)

    def test_definitions(self):
        codes = ["by", "by-nc", "by-nc-nd", "by-nc-sa", "by-nd", "by-sa"]
        for code in codes:
            with self.subTest(code=code):
                lc = LegalCodeFactory(license__license_code=code)
                # mock the translation
                with mock.patch.object(
                    LegalCode, "get_translation_object"
                ) as mock_get_translation_object:
                    mock_get_translation_object.return_value.translate.return_value = (
                        "qwerty"
                    )
                    result = lc.definitions()
                self.assertEqual(
                    {
                        "id": "s1a",
                        "msgid": "s1_definitions_adapted_material",
                        "translation": "qwerty",
                    },
                    result[0],
                )
                self.assertEqual("s1_definitions_you", result[-1]["msgid"])


# Many of these tests mostly are based on whether the metadata import worked right, and
# we're not importing metadata for the time being.
class LicenseModelTest(TestCase):
    # fixtures = ["licenses.json"]

    def test_translation_domain(self):
        license = LicenseFactory(
            license_code="qwerty", version="2.7", jurisdiction_code="zys"
        )
        self.assertEqual("qwerty27zys", license.translation_domain)
        license = LicenseFactory(
            license_code="qwerty", version="2.7", jurisdiction_code=""
        )
        self.assertEqual("qwerty27", license.translation_domain)

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

    def test_translated_title(self):
        license = LicenseFactory(
            license_code="by-nc-nd", jurisdiction_code="", version="4.0"
        )
        LegalCodeFactory(license=license, language_code="en")
        LegalCodeFactory(license=license, language_code="fr")
        with translation.override(language="fr"):
            self.assertEqual(
                "Attribution - Utilisation non commerciale - Pas d’Œuvre dérivée 4.0 International",
                license.translated_title(),
            )
        self.assertEqual(
            "Attribution-NonCommercial-NoDerivatives 4.0 International",
            license.translated_title("en"),
        )
        self.assertEqual(
            "Attribution-NonCommercial-NoDerivatives 4.0 International",
            license.translated_title(),
        )
        # with self.subTest("en"):
        #     self.assertEqual(
        #         "Attribution-NonCommercial-NoDerivatives 4.0 International",
        #         license.translated_title(),
        #     )
        # with self.subTest("es explicit"):
        #     self.assertEqual(
        #         "Atribución-NoComercial-SinDerivadas 4.0 Internacional",
        #         license.translated_title("es"),
        #     )
        # with self.subTest("fr set as current lang"):
        #     with override("fr"):
        #         self.assertEqual(
        #             "Attribution - Pas d’Utilisation Commerciale - Pas de Modification 4.0 Ceci peut être "
        #             "votre site web principal ou la page d’informations vous concernant sur une plate forme "
        #             "d’hébergement, comme Flickr Commons.",
        #             license.translated_title(),
        #         )
        # with self.subTest("no translation for language"):
        #     self.assertEqual(
        #         "Attribution-NonCommercial-NoDerivatives 4.0 International",
        #         license.translated_title("xx"),
        #     )


class TranslatedLicenseNameModelTest(TestCase):
    def test_str(self):
        TranslatedLicenseNameFactory()
        record = TranslatedLicenseName.objects.first()
        self.assertEqual(
            str(record),
            f"TranslatedLicenseName<{record.language_code}, {record.license}>",
        )
