from django.test import TestCase

from i18n import DEFAULT_LANGUAGE_CODE
from licenses import FREEDOM_LEVEL_MAX, FREEDOM_LEVEL_MID, FREEDOM_LEVEL_MIN
from licenses.models import LegalCode, TranslatedLicenseName
from licenses.tests.factories import LicenseFactory, TranslatedLicenseNameFactory


class LegalCodeModelTest(TestCase):
    fixtures = ["licenses.json"]

    def test_str(self):
        legal_code = LegalCode.objects.first()
        self.assertEqual(
            str(legal_code),
            f"LegalCode<{legal_code.language_code}, {legal_code.license.about}>",
        )


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

    def test_default_language_code(self):
        license = LicenseFactory(
            license_code="bx-oh", version="1.3", jurisdiction_code=""
        )
        self.assertEqual(DEFAULT_LANGUAGE_CODE, license.default_language_code())
        license = LicenseFactory(
            license_code="bx-oh", version="1.3", jurisdiction_code="fr"
        )
        self.assertEqual("fr", license.default_language_code())

    def test_get_deed_url(self):
        license = LicenseFactory(
            license_code="bx-oh", version="1.3", jurisdiction_code="ae"
        )
        self.assertEqual("/licenses/bx-oh/1.3/ae/", license.get_deed_url())
        license = LicenseFactory(
            license_code="bx-oh", version="1.3", jurisdiction_code=""
        )
        self.assertEqual("/licenses/bx-oh/1.3/", license.get_deed_url())

    def test_get_deed_url_for_language(self):
        license = LicenseFactory(
            license_code="bx-oh", version="1.3", jurisdiction_code="ae"
        )
        self.assertEqual(
            "/licenses/bx-oh/1.3/ae/deed.fr", license.get_deed_url_for_language("fr")
        )
        license = LicenseFactory(
            license_code="bx-oh", version="1.3", jurisdiction_code=""
        )
        self.assertEqual(
            "/licenses/bx-oh/1.3/deed.es", license.get_deed_url_for_language("es")
        )

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
        self.assertEqual(
            "FIXME: Implement translated title", license.translated_title()
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
