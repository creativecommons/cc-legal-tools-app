from django.test import TestCase
from django.urls import reverse

from licenses.models import License
from licenses.tests.factories import LicenseFactory, LegalCodeFactory
from licenses.views import DEED_TEMPLATE_MAPPING


def never(l):
    return False


def always(l):
    return True


strings_to_lambdas = {
    # Conditions under which we expect to see these strings in a deed page.
    # The lambda is called with a License object
    "INVALID_VARIABLE": never,  # Should never appear
    "You are free to:": lambda l: l.license_code not in DEED_TEMPLATE_MAPPING,
    "You do not have to comply with the license for elements of "
    "the material in the public domain": lambda l: l.license_code
    not in DEED_TEMPLATE_MAPPING,  # Shows up in standard_deed.html, not others
    "The licensor cannot revoke these freedoms as long as you follow the license terms.": lambda l: l.license_code
    not in DEED_TEMPLATE_MAPPING,  # Shows up in standard_deed.html, not others
    "appropriate credit": lambda l: l.requires_attribution
    and l.license_code not in DEED_TEMPLATE_MAPPING,
    "You may do so in any reasonable manner, but not in any way that "
    "suggests the licensor endorses you or your use.": lambda l: l.requires_attribution
    and l.license_code not in DEED_TEMPLATE_MAPPING,
    "We never expect to see this string in a license deed.": never,
    "you must distribute your contributions under the": lambda l: l.requires_share_alike,
    "ShareAlike": lambda l: l.requires_share_alike,
    "same license": lambda l: l.requires_share_alike,
    "as the original.": lambda l: l.requires_share_alike,
    "Adapt": lambda l: l.permits_derivative_works
    and l.license_code not in DEED_TEMPLATE_MAPPING,
    "remix, transform, and build upon the material": lambda l: l.permits_derivative_works
    and l.license_code not in DEED_TEMPLATE_MAPPING,
    "you may not distribute the modified material.": lambda l: not l.permits_derivative_works,
    "NoDerivatives": lambda l: not l.permits_derivative_works,
    "This license is acceptable for Free Cultural Works.": lambda l: l.license_code
    in ["by", "by-sa", "publicdomain", "CC0"],
    "for any purpose, even commercially.": lambda l: l.license_code
    not in DEED_TEMPLATE_MAPPING
    and not l.prohibits_commercial_use,
    "You may not use the material for": lambda l: l.prohibits_commercial_use
    and l.license_code not in DEED_TEMPLATE_MAPPING,
    ">commercial purposes<": lambda l: l.prohibits_commercial_use
    and l.license_code not in DEED_TEMPLATE_MAPPING,
    "When the Licensor is an intergovernmental organization": lambda l: l.jurisdiction_code
    == "igo",
    "of this license is available. You should use it for new works,": lambda l: l.superseded,
    """href="/worldwide/""": lambda l: l.jurisdiction_code != ""
    and l.jurisdiction_code not in ["", "es", "igo"]
    and l.license_code not in DEED_TEMPLATE_MAPPING,
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
        LicenseFactory()  # Have a license for it to display
        url = reverse("home")
        rsp = self.client.get(url)
        self.assertEqual(200, rsp.status_code)
        self.assertTemplateUsed("home.html")


class LicenseDeedViewTest(TestCase):
    def validate_deed_text(self, rsp, license):
        self.assertEqual(200, rsp.status_code)
        self.assertEqual("en", rsp.context["target_lang"])
        text = rsp.content.decode("utf-8")
        if "INVALID_VARIABLE" in text:  # Some unresolved variable in the template
            msgs = ["INVALID_VARIABLE in output"]
            for line in text.splitlines():
                if "INVALID_VARIABLE" in line:
                    msgs.append(line)
            self.fail("\n".join(msgs))

        expected, unexpected = expected_and_unexpected_strings_for_license(license)
        for s in expected:
            with self.subTest("|".join([license.license_code, license.version, s])):
                if s not in text:
                    print(text)
                self.assertContains(rsp, s)
        for s in unexpected:
            with self.subTest("|".join([license.license_code, license.version, s])):
                self.assertNotContains(rsp, s)

    def test_text_in_deeds(self):
        LicenseFactory()
        for license in License.objects.all():
            with self.subTest(license.about):
                # Test in English since that's how we've set up the strings to test for
                url = license.get_deed_url_for_language("en")
                rsp = self.client.get(url)
                self.assertEqual(rsp.status_code, 200)
                self.validate_deed_text(rsp, license)

    def test_license_deed_view_code_version_jurisdiction_language(self):
        license = LicenseFactory(license_code="by-nc", jurisdiction_code="es", version="4.0")
        LegalCodeFactory(license=license, language_code="fr")
        # "<code:license_code>/<version:version>/<jurisdiction:jurisdiction>/deed.<lang:target_lang>"
        url = reverse(
            "license_deed_view_code_version_jurisdiction_language",
            kwargs=dict(
                license_code=license.license_code,
                jurisdiction=license.jurisdiction_code,
                target_lang="fr",
                version="4.0",
            )
        )
        rsp = self.client.get(url)
        self.assertEqual(200, rsp.status_code)

    def test_license_deed_view_code_version_jurisdiction(self):
        license = LicenseFactory(license_code="by-nc", jurisdiction_code="es", version="4.0")
        LegalCodeFactory(license=license, language_code="fr")
        # "<code:license_code>/<version:version>/<jurisdiction:jurisdiction>/"
        url = reverse(
            "license_deed_view_code_version_jurisdiction",
            kwargs=dict(
                license_code=license.license_code,
                version=license.version,
                jurisdiction=license.jurisdiction_code
            )
        )
        rsp = self.client.get(url)
        self.assertEqual(200, rsp.status_code)

    # def test_deed_for_superseded_license(self):
    #     license_code = "by-nc-sa"
    #     version = "2.0"  # No 4.0 licenses have been superseded
    #
    #     new_license = License.objects.get(
    #         license_code=license_code, version="3.0", jurisdiction_code=""
    #     )
    #     license = License.objects.get(
    #         license_code=license_code, version=version, jurisdiction_code=""
    #     )
    #     license.is_replaced_by = new_license
    #     license.save()
    #     rsp = self.client.get(license.get_deed_url())
    #     self.validate_deed_text(rsp, license)

    # def test_jurisdictions(self):
    #     for code in ["es", "igo"]:
    #         with self.subTest(code):
    #             license = LicenseFactory(
    #                 license_code="by-nd-sa",
    #                 jurisdiction_code="es",
    #                 version="3.7",
    #                 requires_share_alike=True,
    #                 permits_distribution=False,
    #                 requires_attribution=True,
    #                 prohibits_commercial_use=False,
    #                 permits_derivative_works=False,
    #             )
    #             rsp = self.client.get(license.get_deed_url())
    #             self.validate_deed_text(rsp, license)
    #
    # def test_language(self):
    #     license = (
    #         License.objects.filter(
    #             license_code="by-nd", version="4.0", legal_codes__language_code="es",
    #         )
    #         .first()
    #     )
    #     rsp = self.client.get(license.get_deed_url())
    #     self.validate_deed_text(rsp, license)
    #
    # def test_use_jurisdiction_default_language(self):
    #     """
    #     If no language specified, but jurisdiction default language is not english,
    #     use that language instead of english.
    #     """
    #     license = License.objects.filter(version="3.0", jurisdiction_code="fr").first()
    #     url = reverse(
    #         "license_deed_view_code_version_jurisdiction",
    #         kwargs=dict(
    #             license_code=license.license_code,
    #             version=license.version,
    #             jurisdiction=license.jurisdiction_code,
    #         ),
    #     )
    #     rsp = self.client.get(url)
    #     context = rsp.context
    #     self.assertEqual("fr", context["target_lang"])
