from django.test import TestCase

from licenses.tests.factories import (
    CreatorFactory,
    LicenseFactory,
    LegalCodeFactory,
    JurisdictionFactory,
    LicenseClassFactory,
    TranslatedLicenseNameFactory,
    LicenseLogoFactory,
    LanguageFactory,
)


class CreatorModelTest(TestCase):
    def test_str(self):
        record = CreatorFactory()
        self.assertEqual(str(record), f"Creator<{record.url}>")


class JurisdictionModelTest(TestCase):
    def test_str(self):
        record = JurisdictionFactory()
        self.assertEqual(str(record), f"Jurisdiction<{record.url}>")


class LanguageModelTest(TestCase):
    def test_str(self):
        record = LanguageFactory()
        self.assertEqual(str(record), f"Language<{record.code}>")


class LegalCodeModelTest(TestCase):
    def test_str(self):
        legal_code = LegalCodeFactory()
        self.assertEqual(str(legal_code), f"LegalCode<{legal_code.language}, {legal_code.url}>")


class LicenseClassModelTest(TestCase):
    def test_str(self):
        record = LicenseClassFactory()
        self.assertEqual(str(record), f"LicenseClass<{record.url}>")


class LicenseLogoModelTest(TestCase):
    def test_str(self):
        record = LicenseLogoFactory()
        self.assertEqual(str(record), f"LicenseLogo<{record.image.url}>")


class LicenseModelTest(TestCase):
    def test_str(self):
        license = LicenseFactory()
        self.assertEqual(str(license), f"License<{license.about}>")


class TranslatedLicenseNameModelTest(TestCase):
    def test_str(self):
        record = TranslatedLicenseNameFactory()
        self.assertEqual(str(record), f"TranslatedLicenseName<{record.language}, {record.license}>")
