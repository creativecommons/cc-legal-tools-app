from django.test import TestCase
from django.utils.translation import override

from i18n import DEFAULT_LANGUAGE_CODE
from licenses import FREEDOM_LEVEL_MIN, FREEDOM_LEVEL_MID, FREEDOM_LEVEL_MAX
from licenses.models import (
    Language,
    LegalCode,
    License,
    LicenseLogo,
    LicenseClass,
    Jurisdiction,
    Creator,
    TranslatedLicenseName,
)


class CreatorModelTest(TestCase):
    def test_str(self):
        record = Creator.objects.first()
        self.assertEqual(str(record), f"Creator<{record.url}>")


class JurisdictionModelTest(TestCase):
    def test_str(self):
        record = Jurisdiction.objects.first()
        self.assertEqual(str(record), f"Jurisdiction<{record.code}>")

    def test_about(self):
        record = Jurisdiction.objects.create(code="silly")
        self.assertEqual(
            "http://creativecommons.org/international/silly/", record.about
        )


class LanguageModelTest(TestCase):
    def test_str(self):
        record = Language.objects.get(code="fr")
        self.assertEqual(str(record), f"Language<{record.code}>")

    def test_name(self):
        # Name of language (translated to current active language)
        record = Language.objects.get(code="fr")
        self.assertEqual("French", record.name())
        with override("fr"):
            self.assertEqual("français", record.name())


class LegalCodeModelTest(TestCase):
    def test_str(self):
        legal_code = LegalCode.objects.first()
        self.assertEqual(
            str(legal_code), f"LegalCode<{legal_code.language}, {legal_code.url}>"
        )


class LicenseClassModelTest(TestCase):
    def test_str(self):
        record = LicenseClass.objects.first()
        self.assertEqual(str(record), f"LicenseClass<{record.url}>")


class LicenseLogoModelTest(TestCase):
    def test_str(self):
        record = LicenseLogo.objects.first()
        self.assertEqual(str(record), f"LicenseLogo<{record.image.url}>")


class LicenseModelTest(TestCase):
    def test_str(self):
        license = License.objects.first()
        self.assertEqual(str(license), f"License<{license.about}>")

    def test_level_of_freedom(self):
        self.assertEqual(
            FREEDOM_LEVEL_MIN,
            License.objects.get(license_code="devnations").level_of_freedom,
        )
        self.assertEqual(
            FREEDOM_LEVEL_MIN,
            License.objects.filter(license_code="sampling").first().level_of_freedom,
        )
        self.assertEqual(
            FREEDOM_LEVEL_MID,
            License.objects.filter(license_code="sampling+").first().level_of_freedom,
        )
        self.assertEqual(
            FREEDOM_LEVEL_MID,
            License.objects.filter(license_code="by-nc").first().level_of_freedom,
        )
        self.assertEqual(
            FREEDOM_LEVEL_MID,
            License.objects.filter(license_code="by-nd").first().level_of_freedom,
        )
        self.assertEqual(
            FREEDOM_LEVEL_MAX,
            License.objects.filter(license_code="by-sa").first().level_of_freedom,
        )

    def test_translated_title(self):
        license = License.objects.get(
            license_code="by-nc-nd", jurisdiction=None, version="4.0"
        )
        with self.subTest("en"):
            self.assertEqual(
                "Attribution-NonCommercial-NoDerivatives 4.0 International",
                license.translated_title(),
            )
        with self.subTest("es explicit"):
            self.assertEqual(
                "Atribución-NoComercial-SinDerivadas 4.0 Internacional",
                license.translated_title("es"),
            )
        with self.subTest("fr set as current lang"):
            with override("fr"):
                self.assertEqual(
                    "Attribution - Pas d’Utilisation Commerciale - Pas de Modification 4.0 Ceci peut être "
                    "votre site web principal ou la page d’informations vous concernant sur une plate forme "
                    "d’hébergement, comme Flickr Commons.",
                    license.translated_title(),
                )
        with self.subTest("no translation for language"):
            self.assertEqual(
                "Attribution-NonCommercial-NoDerivatives 4.0 International",
                license.translated_title("xx"),
            )

    def test_get_deed_url_for_language(self):
        with self.subTest("no jurisdiction, default language"):
            license = License.objects.get(license_code="by-nc-nd", jurisdiction=None, version="4.0")
            self.assertEqual("/by-nc-nd/4.0", license.get_deed_url())
        with self.subTest("no jurisdiction, ask for spanish"):
            license = License.objects.get(license_code="by-nc-nd", jurisdiction=None, version="4.0")
            self.assertEqual("/by-nc-nd/4.0/deed.es", license.get_deed_url_for_language("es"))
        with self.subTest("spanish jurisdiction, default language"):
            license = License.objects.get(license_code="by-nc-nd", jurisdiction__code="es", version="3.0")
            self.assertEqual("/by-nc-nd/3.0/es/", license.get_deed_url())

    def test_default_language_code(self):
        with self.subTest("no jurisdiction"):
            license = License.objects.get(license_code="by-nc-nd", jurisdiction=None, version="4.0")
            self.assertEqual(DEFAULT_LANGUAGE_CODE, license.default_language_code())
        with self.subTest("jurisdiction without default language"):
            license = License.objects.get(license_code="by-nc-nd", jurisdiction__code="pr", version="3.0")
            self.assertEqual(DEFAULT_LANGUAGE_CODE, license.default_language_code())
        with self.subTest("jurisdiction with default language"):
            license = License.objects.get(license_code="by-nc-nd", jurisdiction__code="br", version="3.0")
            self.assertEqual(license.jurisdiction.default_language.code, license.default_language_code())


class TranslatedLicenseNameModelTest(TestCase):
    def test_str(self):
        record = TranslatedLicenseName.objects.first()
        self.assertEqual(
            str(record), f"TranslatedLicenseName<{record.language}, {record.license}>"
        )
