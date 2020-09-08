from django.test import TestCase
from django.utils.translation import override

from i18n import DEFAULT_LANGUAGE_CODE
from licenses import FREEDOM_LEVEL_MAX
from licenses import FREEDOM_LEVEL_MID
from licenses import FREEDOM_LEVEL_MIN
from licenses import (
    FREEDOM_LEVEL_MAX,
    FREEDOM_LEVEL_MID,
    FREEDOM_LEVEL_MIN
)
from licenses.models import (
    LegalCode,
    License,
    LicenseLogo,
    TranslatedLicenseName,
)


class LegalCodeModelTest(TestCase):
    def test_str(self):
        legal_code = LegalCode.objects.first()
        self.assertEqual(
            str(legal_code), f"LegalCode<{legal_code.language_code}, {legal_code.url}>"
        )


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
            license_code="by-nc-nd", jurisdiction_code="", version="4.0"
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
            license = License.objects.get(
                license_code="by-nc-nd", jurisdiction_code="", version="4.0"
            )
            self.assertEqual("/licenses/by-nc-nd/4.0/", license.get_deed_url())
        with self.subTest("no jurisdiction, ask for spanish"):
            license = License.objects.get(
                license_code="by-nc-nd", jurisdiction_code="", version="4.0"
            )
            self.assertEqual(
                "/licenses/by-nc-nd/4.0/deed.es",
                license.get_deed_url_for_language("es"),
            )
        with self.subTest("spanish jurisdiction, default language"):
            license = License.objects.get(
                license_code="by-nc-nd", jurisdiction_code="es", version="3.0"
            )
            self.assertEqual("/licenses/by-nc-nd/3.0/es/", license.get_deed_url())

    def test_default_language_code(self):
        with self.subTest("no jurisdiction"):
            license = License.objects.get(
                license_code="by-nc-nd", jurisdiction_code="", version="4.0"
            )
            self.assertEqual(DEFAULT_LANGUAGE_CODE, license.default_language_code())
        with self.subTest("jurisdiction without default language"):
            license = License.objects.get(
                license_code="by-nc-nd", jurisdiction_code="pr", version="3.0"
            )
            self.assertEqual(DEFAULT_LANGUAGE_CODE, license.default_language_code())
        with self.subTest("jurisdiction with default language"):
            license = License.objects.get(
                license_code="by-nc-nd", jurisdiction_code="br", version="3.0"
            )
            self.assertEqual("br", license.default_language_code())


class TranslatedLicenseNameModelTest(TestCase):
    def test_str(self):
        record = TranslatedLicenseName.objects.first()
        self.assertEqual(
            str(record),
            f"TranslatedLicenseName<{record.language_code}, {record.license}>",
        )
