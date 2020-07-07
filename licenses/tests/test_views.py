from unittest import mock

from django.test import TestCase, override_settings
from django.urls import reverse

# Conditions under which we expect to see these strings in a deed page.
# The lambda is called with a License object
from licenses.models import License, Jurisdiction, Creator
from licenses.tests.factories import LicenseFactory
from licenses.views import all_possible_license_versions


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
        args = {
            "jurisdiction": "uk"
        }
        result = all_possible_license_versions(args)
        expected = list(License.objects.filter(jurisdiction__url__endswith="/uk/"))
        self.assertCountEqual(expected, result)

    def test_lang(self):
        args = {
            "target_lang": "fr"
        }
        result = all_possible_license_versions(args)
        expected = list(License.objects.filter(legal_codes__language__code="fr"))
        self.assertCountEqual(expected, result)

    def test_code_and_jurisdiction(self):
        args = {
            "code": "by-sa",
            "jurisdiction": "uk"
        }
        result = all_possible_license_versions(args)
        expected = list(License.objects.filter(license_code="by-sa", jurisdiction__url__endswith="/uk/"))
        self.assertCountEqual(expected, result)


# There's no URL for this view, so set one up for testing.
@override_settings(ROOT_URLCONF="licenses.tests.urls")
class LicenseCatcherViewTest(TestCase):
    def test_404_if_no_matches(self):
        url = reverse(
            "license_catcher",
            kwargs={
                "license_code": "nonesuch",
                "jurisdiction": "xxx",
                "target_lang": "klg",
            },
        )
        rsp = self.client.get(url)
        self.assertEqual(404, rsp.status_code)

    def test_code(self):
        url = reverse(
            "license_catcher",
            kwargs={
                "license_code": "by-nc",
                "jurisdiction": "",
                "target_lang": ""
            },
        )
        print(url)
        # Pick an arbitrary license for our mock search to return
        licenses_to_use = list(License.objects.filter(license_code="by-nc")[:2])
        with mock.patch("licenses.views.catch_license_versions_from_request") as mock_catcher:
            mock_catcher.return_value = licenses_to_use
            rsp = self.client.get(url)
        self.assertEqual(200, rsp.status_code)
        self.assertTemplateUsed(rsp, "catalog_pages/license_catcher.html")
        context = rsp.context
        self.assertEqual(reversed(licenses_to_use), context["license_versions"])


class LicenseDeedViewTest(TestCase):
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
            jurisdiction = Jurisdiction.objects.get(
                url=f"http://creativecommons.org/international/{code}/"
            )
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
