from unittest import mock

from django.test import TestCase, override_settings
from django.urls import reverse

# Conditions under which we expect to see these strings in a deed page.
# The lambda is called with a License object
from licenses.models import License, Jurisdiction, Creator, Language
from licenses.tests import UNUSED_LANGUAGE
from licenses.tests.factories import LicenseFactory
from licenses.views import (
    all_possible_license_versions,
    license_catcher,
    catch_license_versions_from_request, ALL_POSSIBLE_VERSIONS_CACHE,
)


strings_to_lambdas = {
    "INVALID_VARIABLE": lambda l: False,  # Should never appear
    "You are free to:": lambda l: True,
    "You do not have to comply with the license for elements of the material in the public domain": lambda l: True,
    "The licensor cannot revoke these freedoms as long as you follow the license terms.": lambda l: True,
    "appropriate credit": lambda l: True,
    "You may do so in any reasonable manner, but not in any way that "
    "suggests the licensor endorses you or your use.": lambda l: True,
    "We never expect to see this string in a license deed.": lambda l: False,
    "you must distribute your contributions under the": lambda l: l.requires_share_alike,
    "ShareAlike": lambda l: l.requires_share_alike,
    "same license": lambda l: l.requires_share_alike,
    "as the original.": lambda l: l.requires_share_alike,
    "Adapt": lambda l: l.permits_derivative_works,
    "remix, transform, and build upon the material": lambda l: l.permits_derivative_works,
    "you may not distribute the modified material.": lambda l: not l.permits_derivative_works,
    "NoDerivatives": lambda l: not l.permits_derivative_works,
    "This license is acceptable for Free Cultural Works.": lambda l: l.license_code
    in ["by", "by-sa"],
    "for any purpose, even commercially.": lambda l: not l.prohibits_commercial_use,
    "You may not use the material for": lambda l: l.prohibits_commercial_use,
    "commercial purposes": lambda l: l.prohibits_commercial_use,
    "When the Licensor is an intergovernmental organization": lambda l: l.jurisdiction
    and l.jurisdiction.code == "igo",
    "of this license is available. You should use it for new works,": lambda l: l.superseded,
    """href="/worldwide/""": lambda l: l.jurisdiction is not None
    and l.jurisdiction.code not in ["", "es", "igo"],
}


def expected_and_unexpected_strings_for_license(license):
    expected = [s for s in strings_to_lambdas.keys() if strings_to_lambdas[s](license)]
    unexpected = [
        s for s in strings_to_lambdas.keys() if not strings_to_lambdas[s](license)
    ]
    return expected, unexpected


# All the valid license codes. They all start with "by", and have various combinations
# of "nc", "nd", and "sa", in that order. But not all combinations are valid,
# e.g. "nd" and "sa" are not compatible.
license_codes = []
for bits in range(8):  # We'll enumerate the variations
    parts = ["by"]
    if bits & 1:
        parts.append("nc")
    if bits & 2:
        parts.append("nd")
    if bits & 4:
        parts.append("sa")
    if "nd" in parts and "sa" in parts:
        continue  # Not compatible
    license_codes.append("-".join(parts))


class HomeViewTest(TestCase):
    def test_home_view(self):
        url = reverse("home")
        rsp = self.client.get(url)
        self.assertEqual(200, rsp.status_code)
        self.assertTemplateUsed("home.html")


class AllPossibleLicenseVersionsTest(TestCase):
    # all_possible_license_versions is a search function
    # that returns a list of License objects
    def setUp(self):
        ALL_POSSIBLE_VERSIONS_CACHE.clear()

    def test_no_match(self):
        result = all_possible_license_versions({})
        self.assertEqual(0, len(result))

    def test_code(self):
        args = {
            "code": "by-sa",
        }
        result = all_possible_license_versions(args)
        expected = list(License.objects.filter(license_code="by-sa"))
        self.assertCountEqual(expected, result)

    def test_jurisdiction(self):
        args = {"code": "by-nc-nd", "jurisdiction": "uk"}
        result = all_possible_license_versions(args)
        expected = list(
            License.objects.filter(jurisdiction__code="uk", license_code="by-nc-nd")
        )
        self.assertCountEqual(expected, result)

    def test_lang(self):
        args = {
            "target_lang": "fr",
            "code": "by-nc-nd",
        }
        result = all_possible_license_versions(args)
        expected = list(
            License.objects.filter(
                legal_codes__language__code="fr", license_code="by-nc-nd"
            )
        )
        self.maxDiff = None
        self.assertCountEqual(expected, result)
        self.assertTrue(len(result))

    def test_code_and_jurisdiction(self):
        args = {"code": "by-sa", "jurisdiction": "uk"}
        result = all_possible_license_versions(args)
        expected = list(
            License.objects.filter(license_code="by-sa", jurisdiction__code="uk")
        )
        self.assertCountEqual(expected, result)


# There's no URL for this view, so set one up for testing.
@override_settings(ROOT_URLCONF="licenses.tests.urls")
class LicenseCatcherViewTest(TestCase):
    def setUp(self):
        ALL_POSSIBLE_VERSIONS_CACHE.clear()

    def test_404_if_no_matches(self):
        License.objects.all().delete()
        url = reverse(
            "license_catcher",
            kwargs={
                "license_code": "nonesuch",
                "jurisdiction": "en",
                "target_lang": "es",
            },
        )
        rsp = self.client.get(url)
        self.assertEqual(404, rsp.status_code)

    def test_code_without_language(self):
        url = reverse(
            "license_catcher_without_language",
            kwargs={"license_code": "by-nc", "jurisdiction": "es",},
        )
        # Pick arbitrary licenses for our mock search to return.
        # (They don't match the kwargs we passed to the view, but we're not testing that here.)
        licenses_to_use = list(License.objects.filter(license_code="by-nc")[:2])
        with mock.patch(
            "licenses.views.catch_license_versions_from_request"
        ) as mock_catcher:
            mock_catcher.return_value = licenses_to_use
            rsp = self.client.get(url)
        self.assertTrue(mock_catcher.called)
        self.assertEqual(404, rsp.status_code)  # This view always returns a 404
        self.assertTemplateUsed(rsp, "catalog_pages/license_catcher.html")
        context = rsp.context
        self.assertEqual(list(reversed(licenses_to_use)), context["license_versions"])
        # Should not be translated.  "Skip to content" is in the base template and would
        # be translated...
        self.assertContains(rsp, "Skip to content", status_code=404)

    def test_code_with_language(self):
        url = reverse(
            "license_catcher",
            kwargs={"license_code": "by-nc", "jurisdiction": "es", "target_lang": "es"},
        )
        # Pick arbitrary licenses for our mock search to return.
        # (They don't match the kwargs we passed to the view, but we're not testing that here.)
        licenses_to_use = list(License.objects.filter(license_code="by-nc")[:2])
        with mock.patch(
            "licenses.views.catch_license_versions_from_request"
        ) as mock_catcher:
            mock_catcher.return_value = licenses_to_use
            rsp = self.client.get(url)
        self.assertTrue(mock_catcher.called)
        self.assertEqual(404, rsp.status_code)  # This view always returns a 404
        self.assertTemplateUsed(rsp, "catalog_pages/license_catcher.html")
        context = rsp.context
        self.assertEqual(list(reversed(licenses_to_use)), context["license_versions"])
        # Should be translated.  "Skip to content" is in the base template and should
        # be translated...
        self.assertContains(rsp, "Saltar al contenido", status_code=404)


class LicenseDeedViewTest(TestCase):
    def setUp(self):
        ALL_POSSIBLE_VERSIONS_CACHE.clear()

    def validate(self, rsp, license):
        self.assertEqual(200, rsp.status_code)
        expected, unexpected = expected_and_unexpected_strings_for_license(license)
        for s in expected:
            with self.subTest(license.license_code + license.version + s):
                if s not in rsp.content.decode("utf-8"):
                    print(rsp.content.decode("utf-8"))
                self.assertContains(rsp, s)
        for s in unexpected:
            with self.subTest(license.license_code + license.version + s):
                self.assertNotContains(rsp, s)

    def test_text_in_deeds(self):
        # Test that each deed view includes the expected strings and not the unexpected strings
        # for its license.
        for license_code in license_codes:
            with self.subTest(license_code):
                version = "3.0"
                license = (
                    License.objects.filter(license_code=license_code, version=version)
                    .exclude(jurisdiction=None)
                    .first()
                )
                url = reverse(
                    viewname="license_deed_jurisdiction_explicit",
                    kwargs={
                        "license_code": license_code,
                        "version": version,
                        "jurisdiction": license.jurisdiction.code,
                    },
                )
                rsp = self.client.get(url)
                self.validate(rsp, license)

    def test_deed_for_superseded_license(self):
        license_code = "by-nc-sa"
        version = "2.0"  # No 4.0 licenses have been superseded

        new_license = License.objects.filter(
            license_code=license_code, version="3.0",
        ).first()
        license = License.objects.filter(
            license_code=license_code, version=version,
        ).first()
        license.is_replaced_by = new_license
        license.save()

        url = reverse(
            viewname="license_deed",
            kwargs={"license_code": license_code, "version": version},
        )
        rsp = self.client.get(url)
        self.validate(rsp, license)

    def test_jurisdictions(self):
        for code in ["es", "igo"]:
            creator = Creator.objects.first()
            jurisdiction = Jurisdiction.objects.get(code=code)
            with self.subTest(code):
                license = LicenseFactory(
                    creator=creator,
                    license_code="by-nd-sa",
                    jurisdiction=jurisdiction,
                    version="3.7",
                    requires_share_alike=True,
                    permits_distribution=False,
                    requires_attribution=True,
                    prohibits_commercial_use=False,
                    permits_derivative_works=False,
                )
                url = reverse(
                    viewname="license_deed_jurisdiction_explicit",
                    kwargs={
                        "license_code": license.license_code,
                        "jurisdiction": code,
                        "version": license.version,
                    },
                )
                rsp = self.client.get(url)
                self.validate(rsp, license)

    def test_language(self):
        license = License.objects.filter(license_code="by-nd", version="3.0",
                                          legal_codes__language__code="es",
                                          ).exclude(jurisdiction=None).first()
        target_lang = license.legal_codes.first().language.code
        url = reverse(
            viewname="license_deed_lang_jurisdiction",
            kwargs={
                "license_code": license.license_code,
                "jurisdiction": license.jurisdiction.code,
                "version": license.version,
                "target_lang": target_lang,
            }
        )
        rsp = self.client.get(url)
        self.validate(rsp, license)

    def test_license_not_found_but_look_for_close_matches(self):
        url = reverse(
            viewname="license_deed_lang",
            kwargs={
                "license_code": "by-nc",
                "version": "4.0",
                "target_lang": UNUSED_LANGUAGE,
            }
        )
        rsp = self.client.get(url)
        self.assertEqual(404, rsp.status_code)
        self.assertTemplateUsed(rsp, "catalog_pages/license_catcher.html")

    def test_negotiated_locale_not_valid(self):
        license = License.objects.filter(license_code="by-sa", version="4.0").first()
        url = reverse(
            viewname="license_deed",
            kwargs=dict(
                license_code=license.license_code,
                version=license.version,
            )
        )
        redirect_to = reverse(
            viewname="license_deed_lang",
            kwargs=dict(
                license_code=license.license_code,
                version=license.version,
                target_lang="fr"
            )
        )

        with mock.patch("licenses.views.applicable_langs") as mock_applicable_langs:
            mock_applicable_langs.return_value = ["fr"]
            rsp = self.client.get(url)
            self.assertRedirects(rsp, redirect_to, fetch_redirect_response=False)

    def test_multiple_languages(self):
        # license available in multiple languages
        license = License.objects.filter(license_code="by-sa", version="4.0").first()
        url = reverse(
            viewname="license_deed",
            kwargs=dict(
                license_code=license.license_code,
                version=license.version,
            )
        )
        rsp = self.client.get(url)
        self.assertTrue(rsp.context["multi_language"])

    def test_use_jurisdiction_default_language(self):


class CatchLicenseVersionsFromRequestTest(TestCase):
    def setUp(self):
        ALL_POSSIBLE_VERSIONS_CACHE.clear()

    def test_no_search_args(self):
        result = catch_license_versions_from_request(
            license_code="", jurisdiction="", target_lang=""
        )
        self.assertEqual([], result)

    def test_by_nc_nd(self):
        # Searching for by-nc-nd can find by-nd-nc
        result = catch_license_versions_from_request(
            license_code="by-nc-nd", jurisdiction="fi", target_lang=""
        )
        codes_seen = {license.license_code for license in result}
        self.assertEqual({"by-nd-nc"}, codes_seen)

    def test_jurisdiction(self):
        result = catch_license_versions_from_request(
            license_code="by-sa", jurisdiction="fi", target_lang=""
        )
        jurisdictions = {lic.jurisdiction.code for lic in result}
        self.assertEqual({"fi"}, jurisdictions)

    def test_target_lang(self):
        # If lang specified, only returns licenses with translations for that language
        code = "by-sa"
        lcode = "ca"
        # Ensure there are "by-sa" licenses without "ca" translations
        self.assertTrue(
            License.objects.filter(license_code=code)
            .exclude(legal_codes__language__code=lcode)
            .exists()
        )
        # Now use catch_license_versions_from_request to query for ones that do have "ca"
        result = catch_license_versions_from_request(
            license_code=code, jurisdiction="", target_lang=lcode
        )
        # and make sure all the results do have an 'lcode' translation.
        for license in result:
            self.assertTrue(license.legal_codes.filter(language__code=lcode).exists(),
                            msg=f"License {license} has no {lcode} translation")

    def test_all_args(self):
        code = "by-nc"
        lcode = "ca"
        jurisdiction = "fi"
        result = catch_license_versions_from_request(
            license_code=code, jurisdiction=jurisdiction, target_lang=lcode
        )
        # It looks FIRST for code/translated language, and if found, will not
        # get around to looking at the jurisdiction
        expected = list(
            License.objects.filter(
                license_code=code, legal_codes__language__code=lcode,
            )
        )
        self.assertCountEqual(expected, result)
