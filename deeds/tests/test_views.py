from django.test import TestCase
from django.urls import reverse

from licenses.models import License

# Conditions under which we expect to see these strings in a deed page.
# The lambda is called with a License object
from licenses.tests.factories import LicenseFactory


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


class LicenseDeedViewTest(TestCase):
    def validate(self, rsp, license):
        expected, unexpected = expected_and_unexpected_strings_for_license(license)
        for s in expected:
            with self.subTest(license.license_code + license.version + s):
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
                url = reverse(
                    viewname="license_deed",
                    kwargs={"license_code": license_code, "version": version},
                )
                license = LicenseFactory(
                    license_code=license_code, version=version, jurisdiction=None,
                )
                rsp = self.client.get(url)
                self.assertEqual(200, rsp.status_code)
                self.validate(rsp, license)

    def test_deed_for_superseded_license(self):
        license_code = "by-nc-sa"
        version = "2.0"  # No 4.0 licenses have been superseded

        new_license = LicenseFactory(
            license_code=license_code,
            version="3.0",
        )
        license = LicenseFactory(
            license_code=license_code,
            version=version,
            is_replaced_by=new_license,
        )
        url = reverse(
            viewname="license_deed",
            kwargs={"license_code": license_code, "version": version},
        )
        rsp = self.client.get(url)
        self.assertEqual(200, rsp.status_code)
        self.validate(rsp, license)

    def test_jurisdictions(self):
        for code in ["es", "igo"]:
            with self.subTest(code):
                license = LicenseFactory(
                    license_code="by-nd-sa",
                    jurisdiction__url=f"http://creativecommons.org/international/{code}/",
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
                self.assertEqual(200, rsp.status_code)
                self.validate(rsp, license)
