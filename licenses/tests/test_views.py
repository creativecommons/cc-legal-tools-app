# Standard library
from unittest import mock

# Third-party
from django.conf import settings
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from django.utils.translation.trans_real import DjangoTranslation

# First-party/Local
from i18n import DEFAULT_LANGUAGE_CODE
from licenses.models import LegalCode, License, build_deed_url
from licenses.tests.factories import (
    LegalCodeFactory,
    LicenseFactory,
    TranslationBranchFactory,
)
from licenses.views import (
    DEED_TEMPLATE_MAPPING,
    NUM_COMMITS,
    branch_status_helper,
)


def never(lic_obj):
    return False


def always(lic_obj):
    return True


strings_to_lambdas = {
    # Conditions under which we expect to see these strings in a deed page.
    # The lambda is called with a License object
    "INVALID_VARIABLE": never,  # Should never appear
    "You are free to:": lambda lic_ob: lic_ob.license_code
    not in DEED_TEMPLATE_MAPPING,
    "You do not have to comply with the license for elements of "
    "the material in the public domain": lambda lic_ob: lic_ob.license_code
    not in DEED_TEMPLATE_MAPPING,  # Shows up in standard_deed.html, not others
    "The licensor cannot revoke these freedoms as long as you follow the license terms.": always,  # noqa: E501
    "appropriate credit": lambda lic_ob: lic_ob.requires_attribution
    and lic_ob.license_code not in DEED_TEMPLATE_MAPPING,
    "You may do so in any reasonable manner, but not in any way that "
    "suggests the licensor endorses you or your use.": lambda lic_ob: lic_ob.requires_attribution  # noqa: E501
    and lic_ob.license_code not in DEED_TEMPLATE_MAPPING,
    "We never expect to see this string in a license deed.": never,
    "you must distribute your contributions under the": lambda lic_ob: lic_ob.requires_share_alike,  # noqa: E501
    "ShareAlike": lambda lic_ob: lic_ob.requires_share_alike,
    "same license": lambda lic_ob: lic_ob.requires_share_alike,
    "as the original.": lambda lic_ob: lic_ob.requires_share_alike,
    "Adapt": lambda lic_ob: lic_ob.permits_derivative_works
    and lic_ob.license_code not in DEED_TEMPLATE_MAPPING,
    "remix, transform, and build upon the material": lambda lic_ob: lic_ob.permits_derivative_works  # noqa: E501
    and lic_ob.license_code not in DEED_TEMPLATE_MAPPING,
    "you may not distribute the modified material.": lambda lic_ob: not lic_ob.permits_derivative_works,  # noqa: E501
    "NoDerivatives": lambda lic_ob: not lic_ob.permits_derivative_works,
    # It was decided NOT to include the "free cultural works" icon/text
    "This license is acceptable for Free Cultural Works.": never,
    "for any purpose, even commercially.": lambda lic_ob: lic_ob.license_code
    not in DEED_TEMPLATE_MAPPING
    and not lic_ob.prohibits_commercial_use,
    "You may not use the material for": lambda lic_ob: lic_ob.prohibits_commercial_use  # noqa: E501
    and lic_ob.license_code not in DEED_TEMPLATE_MAPPING,
    ">commercial purposes<": lambda lic_ob: lic_ob.prohibits_commercial_use
    and lic_ob.license_code not in DEED_TEMPLATE_MAPPING,
    "When the Licensor is an intergovernmental organization": lambda lic_ob: lic_ob.jurisdiction_code  # noqa: E501
    == "igo",
    "of this license is available. You should use it for new works,": lambda lic_ob: lic_ob.superseded,  # noqa: E501
    """href="/worldwide/""": lambda lic_ob: lic_ob.jurisdiction_code != ""
    and lic_ob.jurisdiction_code not in ["", "es", "igo"]
    and lic_ob.license_code not in DEED_TEMPLATE_MAPPING,
}


def expected_and_unexpected_strings_for_license(license):
    expected = [
        string_
        for string_ in strings_to_lambdas.keys()
        if strings_to_lambdas[string_](license)
    ]
    unexpected = [
        string_
        for string_ in strings_to_lambdas.keys()
        if not strings_to_lambdas[string_](license)
    ]
    return expected, unexpected


# All the valid license codes. They all start with "by", and have various
# combinations of "nc", "nd", and "sa", in that order. But not all combinations
# are valid, e.g. "nd" and "sa" are not compatible.
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


class AllLicensesViewTest(TestCase):
    def test_all_licenses_view(self):
        LegalCodeFactory()  # Have a legalcode for it to display
        url = reverse("all_licenses")
        rsp = self.client.get(url)
        self.assertEqual(200, rsp.status_code)
        self.assertTemplateUsed("all_licenses.html")


class LicensesTestsMixin:
    # Create some licenses to test in setUp
    def setUp(self):
        self.by = LicenseFactory(
            license_code="by",
            version="4.0",
            permits_derivative_works=True,
            permits_reproduction=True,
            permits_distribution=True,
            permits_sharing=True,
            requires_share_alike=False,
            requires_notice=True,
            requires_attribution=True,
            requires_source_code=False,
            prohibits_commercial_use=False,
            prohibits_high_income_nation_use=False,
        )
        self.by_nc = LicenseFactory(
            license_code="by-nc",
            version="4.0",
            permits_derivative_works=True,
            permits_reproduction=True,
            permits_distribution=True,
            permits_sharing=True,
            requires_share_alike=False,
            requires_notice=True,
            requires_attribution=True,
            requires_source_code=False,
            prohibits_commercial_use=True,
            prohibits_high_income_nation_use=False,
        )
        self.by_nc_nd = LicenseFactory(
            license_code="by-nc-nd",
            version="4.0",
            permits_derivative_works=False,
            permits_reproduction=True,
            permits_distribution=True,
            permits_sharing=True,
            requires_share_alike=False,
            requires_notice=True,
            requires_attribution=True,
            requires_source_code=False,
            prohibits_commercial_use=True,
            prohibits_high_income_nation_use=False,
        )
        self.by_nc_sa = LicenseFactory(
            license_code="by-nc-sa",
            version="4.0",
            permits_derivative_works=True,
            permits_reproduction=True,
            permits_distribution=True,
            permits_sharing=True,
            requires_share_alike=True,
            requires_notice=True,
            requires_attribution=True,
            requires_source_code=False,
            prohibits_commercial_use=True,
            prohibits_high_income_nation_use=False,
        )
        self.by_nd = LicenseFactory(
            license_code="by-nd",
            version="4.0",
            permits_derivative_works=False,
            permits_reproduction=True,
            permits_distribution=True,
            permits_sharing=True,
            requires_share_alike=False,
            requires_notice=True,
            requires_attribution=True,
            requires_source_code=False,
            prohibits_commercial_use=False,
            prohibits_high_income_nation_use=False,
        )
        self.by_sa = LicenseFactory(
            license_code="by-sa",
            version="4.0",
            permits_derivative_works=True,
            permits_reproduction=True,
            permits_distribution=True,
            permits_sharing=True,
            requires_share_alike=True,
            requires_notice=True,
            requires_attribution=True,
            requires_source_code=False,
            prohibits_commercial_use=False,
            prohibits_high_income_nation_use=False,
        )

        for license in License.objects.all():
            LegalCodeFactory(license=license, language_code="en")
            LegalCodeFactory(license=license, language_code="es")
            LegalCodeFactory(license=license, language_code="fr")

        self.by_sa_30_es = LicenseFactory(
            license_code="by-sa",
            version="3.0",
            jurisdiction_code="es",
            permits_derivative_works=True,
            permits_reproduction=True,
            permits_distribution=True,
            permits_sharing=True,
            requires_share_alike=True,
            requires_notice=True,
            requires_attribution=True,
            requires_source_code=False,
            prohibits_commercial_use=False,
            prohibits_high_income_nation_use=False,
        )
        LegalCodeFactory(
            license=self.by_sa_30_es, language_code="es-es"
        )  # Default lang

        super().setUp()


class ViewLicenseTest(TestCase):
    def test_view_license_with_jurisdiction_without_language_specified(self):
        lc = LegalCodeFactory(
            license__version="3.0",
            language_code="de",
            license__jurisdiction_code="de",
        )
        url = reverse(
            "licenses_default_language_with_jurisdiction",
            kwargs=dict(
                version="3.0",
                jurisdiction="de",
                license_code=lc.license.license_code,
            ),
        )
        rsp = self.client.get(url)
        self.assertEqual(200, rsp.status_code)
        self.assertTemplateUsed(rsp, "legalcode_page.html")
        self.assertTemplateUsed(
            rsp, "includes/legalcode_30_ported_license.html"
        )
        context = rsp.context
        self.assertContains(rsp, '''lang="de"''')
        self.assertEqual(lc, context["legalcode"])

    def test_view_license_identifying_jurisdiction_default_language(self):
        language_code = "de"
        lc = LegalCodeFactory(
            license__version="3.0",
            language_code=language_code,
            license__jurisdiction_code="de",
        )
        url = lc.license_url
        rsp = self.client.get(url)
        self.assertEqual(200, rsp.status_code)
        self.assertTemplateUsed(rsp, "legalcode_page.html")
        self.assertTemplateUsed(
            rsp, "includes/legalcode_30_ported_license.html"
        )
        context = rsp.context
        self.assertContains(rsp, f'''lang="{language_code}"''')
        self.assertEqual(lc, context["legalcode"])

    def test_view_license(self):
        for language_code in ["es", "ar", DEFAULT_LANGUAGE_CODE]:
            lc = LegalCodeFactory(
                license__version="4.0", language_code=language_code
            )
            url = lc.license_url
            rsp = self.client.get(url)
            self.assertEqual(200, rsp.status_code)
            self.assertTemplateUsed(rsp, "legalcode_page.html")
            self.assertTemplateUsed(rsp, "includes/legalcode_40_license.html")
            context = rsp.context
            self.assertEqual(lc, context["legalcode"])
            self.assertContains(rsp, f'''lang="{language_code}"''')
            if language_code == "es":
                self.assertContains(rsp, '''dir="ltr"''')
            elif language_code == "ar":
                self.assertContains(rsp, '''dir="rtl"''')

    def test_view_license_plain_text(self):
        for language_code in ["es", "ar", DEFAULT_LANGUAGE_CODE]:
            lc = LegalCodeFactory(
                license__version="4.0", language_code=language_code
            )
            url = lc.plain_text_url
            rsp = self.client.get(url)
            self.assertEqual(
                'text/plain; charset="utf-8"', rsp._headers["content-type"][1]
            )
            self.assertEqual(200, rsp.status_code)
            self.assertGreater(len(rsp.content.decode()), 0)
        lc = LegalCodeFactory(
            license__version="3.0",
            language_code="fr",
            license__license_code="by",
            license__jurisdiction_code="ch",
        )
        url = lc.plain_text_url
        rsp = self.client.get(url)
        self.assertEqual(
            'text/plain; charset="utf-8"', rsp._headers["content-type"][1]
        )
        self.assertEqual(200, rsp.status_code)
        self.assertGreater(len(rsp.content.decode()), 0)


class LicenseDeedViewTest(LicensesTestsMixin, TestCase):
    def validate_deed_text(self, rsp, license):
        self.assertEqual(200, rsp.status_code)
        self.assertEqual("en", rsp.context["legalcode"].language_code)
        text = rsp.content.decode("utf-8")
        if (
            "INVALID_VARIABLE" in text
        ):  # Some unresolved variable in the template
            msgs = ["INVALID_VARIABLE in output"]
            for line in text.splitlines():
                if "INVALID_VARIABLE" in line:
                    msgs.append(line)
            self.fail("\n".join(msgs))

        expected, unexpected = expected_and_unexpected_strings_for_license(
            license
        )
        for s in expected:
            with self.subTest(
                "|".join([license.license_code, license.version, s])
            ):
                if s not in text:
                    print(text)
                self.assertContains(rsp, s)
        for s in unexpected:
            with self.subTest(
                "|".join([license.license_code, license.version, s])
            ):
                self.assertNotContains(rsp, s)

    def test_text_in_deeds(self):
        LicenseFactory()
        for license in License.objects.filter(version="4.0"):
            with self.subTest(license.fat_code):
                # Test in English and for 4.0 since that's how we've set up the
                # strings to test for
                url = build_deed_url(
                    license.license_code,
                    license.version,
                    license.jurisdiction_code,
                    "en",
                )
                rsp = self.client.get(url)
                self.assertEqual(rsp.status_code, 200)
                self.validate_deed_text(rsp, license)

    def test_license_deed_view_code_version_jurisdiction_language(self):
        license = LicenseFactory(
            license_code="by-nc", jurisdiction_code="es", version="3.0"
        )
        language_code = "fr"
        lc = LegalCodeFactory(license=license, language_code=language_code)
        # "<code:license_code>/<version:version>/<jurisdiction:jurisdiction>
        #  /deed.<lang:target_lang>"
        url = lc.deed_url
        # Mock 'get_translation_object' because we have no 3.0 translations
        # imported yet and we can't use 4.0 to test jurisdictions.
        translation_object = DjangoTranslation(language="fr")
        with mock.patch.object(
            LegalCode, "get_translation_object"
        ) as mock_gto:
            mock_gto.return_value = translation_object
            rsp = self.client.get(url)
        self.assertEqual(200, rsp.status_code)

    def test_license_deed_view_code_version_jurisdiction(self):
        # "<code:license_code>/<version:version>/<jurisdiction:jurisdiction>/"
        lc = LegalCodeFactory(
            license__license_code="by-sa",
            license__version="3.0",
            license__jurisdiction_code="es",
            language_code="es",
        )
        url = lc.deed_url
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
    #     rsp = self.client.get(license.deed_url)
    #     self.validate_deed_text(rsp, license)
    #
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
    #             rsp = self.client.get(license.deed_url)
    #             self.validate_deed_text(rsp, license)
    #
    # def test_language(self):
    #     license = (
    #         License.objects.filter(
    #             license_code="by-nd",
    #             version="4.0",
    #             legal_codes__language_code="es",
    #         )
    #         .first()
    #     )
    #     rsp = self.client.get(license.deed_url)
    #     self.validate_deed_text(rsp, license)
    #
    # def test_use_jurisdiction_default_language(self):
    #     """
    #     If no language specified, but jurisdiction default language is not
    #     english, use that language instead of english.
    #     """
    #     license = License.objects.filter(
    #         version="3.0",
    #         jurisdiction_code="fr"
    #     ).first()
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


class BranchStatusViewTest(TestCase):
    def setUp(self):
        self.translation_branch = TranslationBranchFactory(
            language_code="fr",
        )

    def test_simple_branch(self):
        url = reverse(
            "branch_status", kwargs=dict(id=self.translation_branch.id)
        )
        with mock.patch("licenses.views.git"):
            with mock.patch.object(LegalCode, "get_pofile"):
                with mock.patch(
                    "licenses.views.branch_status_helper"
                ) as mock_helper:
                    mock_helper.return_value = {
                        "official_git_branch": settings.OFFICIAL_GIT_BRANCH,
                        "branch": self.translation_branch,
                        "commits": [],
                        "last_commit": None,
                    }
                    r = self.client.get(url)
        mock_helper.assert_called_with(mock.ANY, self.translation_branch)
        self.assertTemplateUsed(r, "licenses/branch_status.html")
        context = r.context
        self.assertEqual(self.translation_branch, context["branch"])
        self.assertEqual(
            settings.OFFICIAL_GIT_BRANCH, context["official_git_branch"]
        )

    def test_branch_helper_local_branch_exists(self):
        mock_repo = mock.MagicMock()
        mock_commit = mock.MagicMock(
            hexsha="0123456789abcdef",
            message="A message",
            committed_datetime=timezone.now(),
            committer="John Q. Committer",
        )
        mock_commits = [
            mock_commit,
            mock_commit,
            mock_commit,
            mock_commit,
        ]
        mock_repo.iter_commits.return_value = mock_commits

        # Something like this will be returned for each commit
        # Most will have a "previous" added, though.
        massaged_commit = {
            "committed_datetime": mock_commit.committed_datetime,
            "committer": "John Q. Committer",
            "hexsha": "0123456789abcdef",
            "message": "A message",
            "shorthash": "0123456",
        }

        expected_commits = [
            dict(massaged_commit)
            for i in range(min(NUM_COMMITS + 1, len(mock_commits)))
        ]
        for i, commit in enumerate(expected_commits):
            if (i + 1) < len(expected_commits):
                commit["previous"] = expected_commits[i + 1]
        expected_commits = expected_commits[:NUM_COMMITS]
        last_commit = expected_commits[0]

        result = branch_status_helper(mock_repo, self.translation_branch)

        self.assertEqual(
            {
                "branch": self.translation_branch,
                "commits": expected_commits,
                "last_commit": last_commit,
                "official_git_branch": settings.OFFICIAL_GIT_BRANCH,
            },
            result,
        )
        mock_repo.iter_commits.assert_called_with(
            f"origin/{self.translation_branch.branch_name}", max_count=4
        )

    def test_branch_helper_local_branch_does_not_exist_anywhere(self):
        mock_repo = mock.MagicMock()

        # Our mock repo should act like this branch does not exist anywhere
        mock_repo.branches = (
            object()
        )  # Will not have an attribute named 'branch_name'

        origin = mock_repo.remotes.origin

        class just_has_parent:
            pass

        origin.refs = (
            just_has_parent()
        )  # Will not have an attribute named 'branch_name'
        mock_parent_branch = mock.MagicMock()
        setattr(origin.refs, settings.OFFICIAL_GIT_BRANCH, mock_parent_branch)

        result = branch_status_helper(mock_repo, self.translation_branch)
        mock_repo.iter_commits.return_value = []
        self.assertEqual(
            {
                "branch": self.translation_branch,
                "commits": [],
                "last_commit": None,
                "official_git_branch": settings.OFFICIAL_GIT_BRANCH,
            },
            result,
        )
        mock_repo.iter_commits.assert_called_with(
            f"origin/{self.translation_branch.branch_name}", max_count=4
        )

    def test_branch_helper_branch_only_upstream(self):
        branch_name = self.translation_branch.branch_name

        mock_repo = mock.MagicMock()

        # Our mock repo should act like this branch does not exist here
        mock_repo.branches = (
            object()
        )  # Will not have an attribute named 'branch_name'

        # But it does exist upstream
        origin = mock_repo.remotes.origin

        class has_branch:
            pass

        origin.refs = has_branch()
        mock_upstream_branch = mock.MagicMock()
        setattr(origin.refs, branch_name, mock_upstream_branch)

        result = branch_status_helper(mock_repo, self.translation_branch)
        mock_repo.iter_commits.return_value = []
        self.assertEqual(
            {
                "branch": self.translation_branch,
                "commits": [],
                "last_commit": None,
                "official_git_branch": settings.OFFICIAL_GIT_BRANCH,
            },
            result,
        )
        mock_repo.iter_commits.assert_called_with(
            f"origin/{branch_name}", max_count=4
        )


class TranslationStatusViewTest(TestCase):
    def test_translation_status_view(self):
        TranslationBranchFactory()
        TranslationBranchFactory()
        TranslationBranchFactory()

        url = reverse("translation_status")
        with mock.patch.object(LegalCode, "get_pofile"):
            rsp = self.client.get(url)
        self.assertTemplateUsed(rsp, "licenses/translation_status.html")
        context = rsp.context
        self.assertEqual(3, len(context["branches"]))


class MetadataViewTest(TestCase):
    def test_metadata_view(self):
        LicenseFactory()
        with mock.patch.object(License, "get_metadata") as mock_get_metadata:
            mock_get_metadata.return_value = {"foo": "bar"}
            rsp = self.client.get(reverse("metadata"))
        self.assertEqual(200, rsp.status_code)
        mock_get_metadata.assert_called_with()
        self.assertEqual(b"- foo: bar\n", rsp.content)
