"""
Since the metadata is already imported during migrations before
this test runs, we just check out a sampling of data that we
expect to exist.
"""
import datetime

from django.test import TestCase

from licenses.models import License, TranslatedLicenseName, LicenseLogo, LegalCode


class MetadataTest(TestCase):
    def test_mit_license(self):
        license = License.objects.get(identifier="MIT")
        self.assertIsNone(license.creator)
        self.assertEqual("http://creativecommons.org/license/software", license.license_class.url)

        self.assertTrue(license.permits_derivative_works)
        self.assertTrue(license.permits_distribution)
        self.assertTrue(license.permits_reproduction)
        self.assertTrue(license.requires_notice)

        self.assertFalse(license.requires_attribution)
        self.assertFalse(license.requires_source_code)
        self.assertFalse(license.requires_share_alike)
        self.assertFalse(license.prohibits_commercial_use)
        self.assertFalse(license.prohibits_high_income_nation_use)

    def test_bsd(self):
        license = License.objects.get(identifier="BSD")
        self.assertIsNone(license.creator)
        self.assertEqual("http://creativecommons.org/license/software", license.license_class.url)

        self.assertTrue(license.permits_derivative_works)
        self.assertTrue(license.permits_distribution)
        self.assertTrue(license.permits_reproduction)
        self.assertTrue(license.requires_notice)

        self.assertFalse(license.requires_attribution)
        self.assertFalse(license.requires_share_alike)
        self.assertFalse(license.requires_source_code)
        self.assertFalse(license.prohibits_commercial_use)
        self.assertFalse(license.prohibits_high_income_nation_use)

    def test_40_by_nc_nd(self):
        license = License.objects.get(version="4.0", identifier="by-nc-nd")
        self.assertEqual("http://creativecommons.org", license.creator.url)
        self.assertEqual("http://creativecommons.org/license/", license.license_class.url)

        self.assertTrue(license.requires_attribution)
        self.assertTrue(license.requires_notice)
        self.assertTrue(license.permits_reproduction)
        self.assertTrue(license.permits_distribution)
        self.assertTrue(license.prohibits_commercial_use)

        self.assertFalse(license.requires_share_alike)
        self.assertFalse(license.requires_source_code)
        self.assertFalse(license.permits_derivative_works)
        self.assertFalse(license.prohibits_high_income_nation_use)

        legalcodes = list(license.legal_codes.all())
        self.assertEqual(1, len(legalcodes))
        legalcode = legalcodes[0]
        self.assertEqual(legalcode.url, "http://creativecommons.org/licenses/by-nc-nd/4.0/legalcode")
        self.assertEqual(legalcode.language.code, "en-us")

        tname = TranslatedLicenseName.objects.get(
            license=license,
            language__code="it",
        )
        self.assertEqual("Attribuzione - Non commerciale - Non opere derivate 4.0 Internazionale", tname.name)

    def test_40_by_sa(self):
        license = License.objects.get(version="4.0", identifier="by-sa")
        self.assertEqual("http://creativecommons.org", license.creator.url)
        self.assertEqual("http://creativecommons.org/license/", license.license_class.url)

        self.assertTrue(license.requires_attribution)
        self.assertTrue(license.requires_notice)
        self.assertTrue(license.requires_share_alike)
        self.assertTrue(license.permits_derivative_works)
        self.assertTrue(license.permits_reproduction)
        self.assertTrue(license.permits_distribution)

        self.assertFalse(license.requires_source_code)
        self.assertFalse(license.permits_sharing)
        self.assertFalse(license.prohibits_commercial_use)
        self.assertFalse(license.prohibits_high_income_nation_use)
        tname = TranslatedLicenseName.objects.get(
            license=license,
            language__code="af",
        )
        self.assertEqual("Erkenning-InsgelyksDeel 4.0 International", tname.name)

    def test_30_by_nc_nd_es(self):
        license = License.objects.get(about="http://creativecommons.org/licenses/by-nc-nd/3.0/es/")
        # This one has a source
        self.assertEqual(
            "http://creativecommons.org/licenses/by-nc-nd/3.0/",
            license.source.about
        )
        self.assertEqual("http://creativecommons.org", license.creator.url)
        self.assertEqual("http://creativecommons.org/license/", license.license_class.url)
        self.assertTrue(license.jurisdiction.url.endswith("/es/"))
        self.assertTrue(license.requires_attribution)
        self.assertTrue(license.requires_notice)
        self.assertTrue(license.permits_reproduction)
        self.assertTrue(license.permits_distribution)
        self.assertTrue(license.prohibits_commercial_use)

        self.assertFalse(license.requires_share_alike)
        self.assertFalse(license.requires_source_code)
        self.assertFalse(license.permits_derivative_works)
        self.assertFalse(license.prohibits_high_income_nation_use)

        # one of six legalcodes for this one
        legalcode = license.legal_codes.get(language__code="es")
        self.assertEqual(legalcode.url, "http://creativecommons.org/licenses/by-nc-nd/3.0/es/legalcode.es")
        self.assertEqual(legalcode.language.code, "es")

        tname = TranslatedLicenseName.objects.get(
            license=license,
            language__code="id",
        )
        self.assertEqual("Atribusi-NonKomersial-TanpaTurunan 3.0 Spanyol", tname.name)

        # Two logos
        logos = LicenseLogo.objects.filter(license=license)
        self.assertCountEqual(
            [
                "https://i.creativecommons.org/l/by-nc-nd/3.0/es/80x15.png",
                "https://i.creativecommons.org/l/by-nc-nd/3.0/es/88x31.png"
            ],
            list(logos.values_list("image", flat=True))
        )

    def test_is_replaced_by(self):
        license = License.objects.get(about="http://creativecommons.org/licenses/by/2.0/hr/")
        self.assertEqual("http://creativecommons.org/licenses/by/2.5/hr/", license.is_replaced_by.about)

    def test_is_based_on(self):
        license = License.objects.get(about="http://creativecommons.org/licenses/by-nc-nd/2.0/jp/")
        self.assertEqual("http://creativecommons.org/licenses/by-nc-nd/2.0/", license.is_based_on.about)

    def test_deprecated_on(self):
        license = License.objects.get(
            about="http://creativecommons.org/licenses/sa/1.0/fi/"
        )
        # 2004-05-25
        self.assertEqual(datetime.date(2004, 5, 25), license.deprecated_on)

    def test_english_is_default(self):
        with self.subTest("legal code"):
            # Here's a Legalcode that did not have a language in the RDF
            legal_code = LegalCode.objects.get(url="http://creativecommons.org/publicdomain/zero/1.0/legalcode")
            # It should be using English
            self.assertEqual("en-us", legal_code.language.code)
        with self.subTest("title"):
            title = TranslatedLicenseName.objects.get(name="BSD License")
            self.assertEqual("en-us", title.language.code)
