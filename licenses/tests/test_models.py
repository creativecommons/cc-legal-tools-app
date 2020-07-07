from django.test import TestCase

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
        self.assertEqual(str(record), f"Jurisdiction<{record.url}>")

    def test_code(self):
        record = Jurisdiction.objects.create(url="http://creativecommons.org/international/silly/")
        self.assertEqual("silly", record.code)
        record = Jurisdiction.objects.create(url="http://example.com/foo")
        self.assertEqual("", record.code)


class LanguageModelTest(TestCase):
    def test_str(self):
        record = Language.objects.get(code="fr")
        self.assertEqual(str(record), f"Language<{record.code}>")


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
        self.assertEqual(FREEDOM_LEVEL_MIN, License.objects.get(license_code="devnations").level_of_freedom)
        self.assertEqual(FREEDOM_LEVEL_MIN, License.objects.filter(license_code="sampling").first().level_of_freedom)
        self.assertEqual(FREEDOM_LEVEL_MID, License.objects.filter(license_code="sampling+").first().level_of_freedom)
        self.assertEqual(FREEDOM_LEVEL_MID, License.objects.filter(license_code="by-nc").first().level_of_freedom)
        self.assertEqual(FREEDOM_LEVEL_MID, License.objects.filter(license_code="by-nd").first().level_of_freedom)
        self.assertEqual(FREEDOM_LEVEL_MAX, License.objects.filter(license_code="by-sa").first().level_of_freedom)


class TranslatedLicenseNameModelTest(TestCase):
    def test_str(self):
        record = TranslatedLicenseName.objects.first()
        self.assertEqual(
            str(record), f"TranslatedLicenseName<{record.language}, {record.license}>"
        )
