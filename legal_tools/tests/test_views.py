# Standard library
import os.path
from unittest import mock

# Third-party
from django.conf import settings
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from django.utils.translation.trans_real import DjangoTranslation

# First-party/Local
from i18n.utils import get_default_language_for_jurisdiction_deed_ux
from legal_tools.models import UNITS_LICENSES, LegalCode, Tool, build_path
from legal_tools.rdf_utils import (
    convert_https_to_http,
    generate_foaf_logo_uris,
)
from legal_tools.tests.factories import (
    LegalCodeFactory,
    ToolFactory,
    TranslationBranchFactory,
)
from legal_tools.views import (
    NUM_COMMITS,
    branch_status_helper,
    get_category_and_category_title,
    get_deed_rel_path,
    get_legal_code_replaced_rel_path,
    normalize_path_and_lang,
    render_redirect,
)


def never(lic_obj):
    return False


def always(lic_obj):
    return True


strings_to_lambdas = {
    # Conditions under which we expect to see these strings in a deed page.
    # The lambda is called with a Tool object
    "INVALID_VARIABLE": never,  # Should never appear
    "You are free to:": lambda lic_ob: lic_ob.unit in UNITS_LICENSES,
    "You do not have to comply with the license for elements of "
    "the material in the public domain": lambda lic_ob: lic_ob.unit
    in UNITS_LICENSES,  # Shows up in standard_deed.html, not others
    "The licensor cannot revoke these freedoms as long as you follow the license terms.": always,  # noqa: E501
    "appropriate credit": lambda lic_ob: lic_ob.requires_attribution
    and lic_ob.unit in UNITS_LICENSES,
    "You may do so in any reasonable manner, but not in any way that "
    "suggests the licensor endorses you or your use.": lambda lic_ob: lic_ob.requires_attribution  # noqa: E501
    and lic_ob.unit in UNITS_LICENSES,
    "We never expect to see this string in a license deed.": never,
    "you must distribute your contributions under the": lambda lic_ob: lic_ob.requires_share_alike,  # noqa: E501
    "ShareAlike": lambda lic_ob: lic_ob.requires_share_alike,
    "same license": lambda lic_ob: lic_ob.requires_share_alike,
    "as the original.": lambda lic_ob: lic_ob.requires_share_alike,
    "Adapt": lambda lic_ob: lic_ob.permits_derivative_works
    and lic_ob.unit in UNITS_LICENSES,
    "remix, transform, and build upon the material": lambda lic_ob: lic_ob.permits_derivative_works  # noqa: E501
    and lic_ob.unit in UNITS_LICENSES,
    "you may not distribute the modified material.": lambda lic_ob: not lic_ob.permits_derivative_works,  # noqa: E501
    "NoDerivatives": lambda lic_ob: not lic_ob.permits_derivative_works,
    # It was decided NOT to include the "free cultural works" icon/text
    "This license is acceptable for Free Cultural Works.": never,
    "for any purpose, even commercially.": lambda lic_ob: not lic_ob.prohibits_commercial_use  # noqa: E501
    and lic_ob.unit in UNITS_LICENSES,
    "You may not use the material for": lambda lic_ob: lic_ob.prohibits_commercial_use  # noqa: E501
    and lic_ob.unit in UNITS_LICENSES,
    "commercial purposes": lambda lic_ob: lic_ob.prohibits_commercial_use
    and lic_ob.unit in UNITS_LICENSES,
    "When the Licensor is an intergovernmental organization": lambda lic_ob: lic_ob.jurisdiction_code  # noqa: E501
    == "igo",
    "of this license is available. You should use it for new works,": lambda lic_ob: lic_ob.superseded,  # noqa: E501
    """href="/worldwide/""": lambda lic_ob: lic_ob.jurisdiction_code != ""
    and lic_ob.jurisdiction_code not in ["", "es", "igo"]
    and lic_ob.unit in UNITS_LICENSES,
}


def expected_and_unexpected_strings_for_tool(tool):
    expected = [
        string_
        for string_ in strings_to_lambdas.keys()
        if strings_to_lambdas[string_](tool)
    ]
    unexpected = [
        string_
        for string_ in strings_to_lambdas.keys()
        if not strings_to_lambdas[string_](tool)
    ]
    return expected, unexpected


class ToolsTestsMixin:
    # Create some tools to test in setUp
    def setUp(self):
        self.by_40 = ToolFactory(
            base_url="https://creativecommons.org/licenses/by/4.0/",
            category="licenses",
            unit="by",
            version="4.0",
            permits_derivative_works=True,
            permits_reproduction=True,
            permits_distribution=True,
            permits_sharing=True,
            requires_share_alike=False,
            requires_notice=True,
            requires_attribution=True,
            prohibits_commercial_use=False,
            prohibits_high_income_nation_use=False,
        )
        self.by_nc_40 = ToolFactory(
            base_url="https://creativecommons.org/licenses/by-nc/4.0/",
            category="licenses",
            unit="by-nc",
            version="4.0",
            permits_derivative_works=True,
            permits_reproduction=True,
            permits_distribution=True,
            permits_sharing=True,
            requires_share_alike=False,
            requires_notice=True,
            requires_attribution=True,
            prohibits_commercial_use=True,
            prohibits_high_income_nation_use=False,
        )
        self.by_nc_nd_40 = ToolFactory(
            base_url="https://creativecommons.org/licenses/by-nc-nd/4.0/",
            category="licenses",
            unit="by-nc-nd",
            version="4.0",
            permits_derivative_works=False,
            permits_reproduction=True,
            permits_distribution=True,
            permits_sharing=True,
            requires_share_alike=False,
            requires_notice=True,
            requires_attribution=True,
            prohibits_commercial_use=True,
            prohibits_high_income_nation_use=False,
        )
        self.by_nc_sa_40 = ToolFactory(
            base_url="https://creativecommons.org/licenses/by-nc-sa/4.0/",
            category="licenses",
            unit="by-nc-sa",
            version="4.0",
            permits_derivative_works=True,
            permits_reproduction=True,
            permits_distribution=True,
            permits_sharing=True,
            requires_share_alike=True,
            requires_notice=True,
            requires_attribution=True,
            prohibits_commercial_use=True,
            prohibits_high_income_nation_use=False,
        )
        self.by_nd_40 = ToolFactory(
            base_url="https://creativecommons.org/licenses/by-nd/4.0/",
            category="licenses",
            unit="by-nd",
            version="4.0",
            permits_derivative_works=False,
            permits_reproduction=True,
            permits_distribution=True,
            permits_sharing=True,
            requires_share_alike=False,
            requires_notice=True,
            requires_attribution=True,
            prohibits_commercial_use=False,
            prohibits_high_income_nation_use=False,
        )
        self.by_sa_40 = ToolFactory(
            base_url="https://creativecommons.org/licenses/by-sa/4.0/",
            category="licenses",
            unit="by-sa",
            version="4.0",
            permits_derivative_works=True,
            permits_reproduction=True,
            permits_distribution=True,
            permits_sharing=True,
            requires_share_alike=True,
            requires_notice=True,
            requires_attribution=True,
            prohibits_commercial_use=False,
            prohibits_high_income_nation_use=False,
        )
        self.by_30 = ToolFactory(
            base_url="https://creativecommons.org/licenses/by/3.0/",
            category="licenses",
            unit="by",
            version="3.0",
            is_replaced_by=self.by_40,
            permits_derivative_works=True,
            permits_reproduction=True,
            permits_distribution=True,
            permits_sharing=True,
            requires_share_alike=False,
            requires_notice=True,
            requires_attribution=True,
            prohibits_commercial_use=False,
            prohibits_high_income_nation_use=False,
        )
        self.by_20 = ToolFactory(
            base_url="https://creativecommons.org/licenses/by/2.0/",
            category="licenses",
            unit="by",
            version="2.0",
            is_replaced_by=self.by_40,
            permits_derivative_works=True,
            permits_reproduction=True,
            permits_distribution=True,
            permits_sharing=True,
            requires_share_alike=False,
            requires_notice=True,
            requires_attribution=True,
            prohibits_commercial_use=False,
            prohibits_high_income_nation_use=False,
        )
        self.zero_10 = ToolFactory(
            base_url="https://creativecommons.org/publicdomain/zero/1.0/",
            category="publicdomain",
            unit="zero",
            version="1.0",
            permits_derivative_works=True,
            permits_reproduction=True,
            permits_distribution=True,
            permits_sharing=True,
            requires_share_alike=False,
            requires_notice=False,
            requires_attribution=False,
            prohibits_commercial_use=False,
            prohibits_high_income_nation_use=False,
        )

        for tool in Tool.objects.all():
            LegalCodeFactory(tool=tool, language_code="en")
            LegalCodeFactory(tool=tool, language_code="es")
            LegalCodeFactory(tool=tool, language_code="fr")

        self.by_30_es = ToolFactory(
            base_url="https://creativecommons.org/licenses/by/3.0/es/",
            category="licenses",
            unit="by",
            version="3.0",
            jurisdiction_code="es",
            is_replaced_by=self.by_40,
            permits_derivative_works=True,
            permits_reproduction=True,
            permits_distribution=True,
            permits_sharing=True,
            requires_share_alike=False,
            requires_notice=True,
            requires_attribution=True,
            prohibits_commercial_use=False,
            prohibits_high_income_nation_use=False,
        )
        # global default language
        LegalCodeFactory(tool=self.by_30_es, language_code="en")

        self.by_sa_30_es = ToolFactory(
            base_url="https://creativecommons.org/licenses/by-sa/3.0/es/",
            category="licenses",
            unit="by-sa",
            version="3.0",
            jurisdiction_code="es",
            is_replaced_by=self.by_sa_40,
            permits_derivative_works=True,
            permits_reproduction=True,
            permits_distribution=True,
            permits_sharing=True,
            requires_share_alike=True,
            requires_notice=True,
            requires_attribution=True,
            prohibits_commercial_use=False,
            prohibits_high_income_nation_use=False,
        )
        # Jurisdiction default language
        LegalCodeFactory(tool=self.by_sa_30_es, language_code="es")
        LegalCodeFactory(tool=self.by_sa_30_es, language_code="ca")

        self.by_sa_30_igo = ToolFactory(
            base_url="https://creativecommons.org/licenses/by-sa/3.0/igo/",
            category="licenses",
            unit="by-sa",
            version="3.0",
            jurisdiction_code="igo",
            is_replaced_by=self.by_sa_40,
            permits_derivative_works=True,
            permits_reproduction=True,
            permits_distribution=True,
            permits_sharing=True,
            requires_share_alike=True,
            requires_notice=True,
            requires_attribution=True,
            prohibits_commercial_use=False,
            prohibits_high_income_nation_use=False,
        )
        # Jurisdiction default language
        LegalCodeFactory(tool=self.by_sa_30_igo, language_code="en")
        LegalCodeFactory(tool=self.by_sa_30_igo, language_code="fr")

        self.by_30_th = ToolFactory(
            base_url="https://creativecommons.org/licenses/by/3.0/th/",
            category="licenses",
            unit="by",
            version="3.0",
            jurisdiction_code="th",
            is_replaced_by=self.by_40,
            permits_derivative_works=True,
            permits_reproduction=True,
            permits_distribution=True,
            permits_sharing=True,
            requires_share_alike=True,
            requires_notice=True,
            requires_attribution=True,
            prohibits_commercial_use=False,
            prohibits_high_income_nation_use=False,
        )
        # Jurisdiction default language
        LegalCodeFactory(tool=self.by_30_th, language_code="th")

        self.by_sa_20_es = ToolFactory(
            base_url="https://creativecommons.org/licenses/by-sa/2.0/es/",
            category="licenses",
            unit="by-sa",
            version="2.0",
            jurisdiction_code="es",
            is_replaced_by=self.by_sa_40,
            permits_derivative_works=True,
            permits_reproduction=True,
            permits_distribution=True,
            permits_sharing=True,
            requires_share_alike=True,
            requires_notice=True,
            requires_attribution=True,
            prohibits_commercial_use=False,
            prohibits_high_income_nation_use=False,
        )
        # Jurisdiction default language
        LegalCodeFactory(tool=self.by_sa_20_es, language_code="es")

        self.devnations = ToolFactory(
            base_url="https://creativecommons.org/licenses/devnations/2.0/",
            category="licenses",
            unit="devnations",
            version="2.0",
            deprecated_on="2007-06-04",
            permits_derivative_works=True,
            permits_reproduction=True,
            permits_distribution=True,
            permits_sharing=False,
            requires_share_alike=False,
            requires_notice=True,
            requires_attribution=True,
            prohibits_commercial_use=False,
            prohibits_high_income_nation_use=True,
        )
        LegalCodeFactory(tool=self.devnations, language_code="en")

        self.sampling = ToolFactory(
            base_url="https://creativecommons.org/licenses/sampling/1.0/",
            category="licenses",
            unit="sampling",
            version="1.0",
            deprecated_on="2007-06-04",
            permits_derivative_works=True,
            permits_reproduction=False,
            permits_distribution=False,
            permits_sharing=False,
            requires_share_alike=False,
            requires_notice=True,
            requires_attribution=True,
            prohibits_commercial_use=False,
            prohibits_high_income_nation_use=False,
        )
        LegalCodeFactory(tool=self.sampling, language_code="en")

        # sources (non-exhaustive)
        self.by_40.source = self.by_30
        self.by_40.save()
        self.by_30.source = self.by_20
        self.by_30.save()
        self.by_sa_20_es.source = self.by_20
        self.by_sa_20_es.save()

        super().setUp()


class ViewHelperFunctionsTest(ToolsTestsMixin, TestCase):
    def test_get_category_and_category_title_category_tool(self):
        category, category_title = get_category_and_category_title(
            category=None,
            tool=None,
        )
        self.assertEqual(category, "licenses")
        self.assertEqual(category_title, "Licenses")

        tool = Tool.objects.get(unit="by", version="4.0")
        category, category_title = get_category_and_category_title(
            category=None,
            tool=tool,
        )
        self.assertEqual(category, "licenses")
        self.assertEqual(category_title, "Licenses")

    def test_get_category_and_category_title_category_publicdomain(self):
        category, category_title = get_category_and_category_title(
            category="publicdomain",
            tool=None,
        )
        self.assertEqual(category, "publicdomain")
        self.assertEqual(category_title, "Public Domain")

    @override_settings(LANGUAGES_AVAILABLE_DEEDS_UX=["x1", "x2"])
    def test_get_deed_rel_path_mostly_translated_language_code(self):
        expected_deed_rel_path = "deed.x1"
        deed_rel_path = get_deed_rel_path(
            deed_url="/deed.x1",
            path_start="/",
            language_code="x1",
            language_default="x2",
        )
        self.assertEqual(expected_deed_rel_path, deed_rel_path)

    @override_settings(LANGUAGES_AVAILABLE_DEEDS_UX=["x1", "x2"])
    def test_get_deed_rel_path_less_translated_language_code(self):
        expected_deed_rel_path = "deed.x2"
        deed_rel_path = get_deed_rel_path(
            deed_url="/deed.x3",
            path_start="/",
            language_code="x3",
            language_default="x2",
        )
        self.assertEqual(expected_deed_rel_path, deed_rel_path)

    @override_settings(
        LANGUAGE_CODE="x1",
        LANGUAGES_AVAILABLE_DEEDS_UX=[],
    )
    def test_get_deed_rel_path_less_translated_language_default(self):
        expected_deed_rel_path = "deed.x1"
        deed_rel_path = get_deed_rel_path(
            deed_url="/deed.x3",
            path_start="/",
            language_code="x3",
            language_default="x2",
        )
        self.assertEqual(expected_deed_rel_path, deed_rel_path)

    def test_get_legal_code_replaced_rel_path_cache_miss(self):
        tool = Tool.objects.get(
            unit="by",
            version="3.0",
            jurisdiction_code="",
        )
        path_start = "/licenses/by/3.0"
        language_code = "en"
        language_default = get_default_language_for_jurisdiction_deed_ux(None)

        cache.clear()
        self.assertFalse(cache.has_key("by-4.0--en-replaced_deed_str"))
        self.assertFalse(cache.has_key("by-4.0--en-replaced_legal_code_title"))
        _, _, _, _ = get_legal_code_replaced_rel_path(
            tool.is_replaced_by, path_start, language_code, language_default
        )
        self.assertEqual(
            cache.get("by-4.0--en-replaced_deed_title"),
            "Deed - Attribution 4.0 International",
        )
        self.assertEqual(
            cache.get("by-4.0--en-replaced_legal_code_title"),
            "Legal Code - Attribution 4.0 International",
        )

    def test_normalize_path_and_lang(self):
        request_path = "/licenses/by/3.0/de/legalcode"
        jurisdiction = "de"
        norm_request_path, norm_language_code = normalize_path_and_lang(
            request_path,
            jurisdiction,
            language_code=None,
        )
        self.assertEqual(norm_request_path, f"{request_path}.de")
        self.assertEqual(norm_language_code, "de")


class ViewDevHomeTest(ToolsTestsMixin, TestCase):
    def test_view_dev_index_view(self):
        url = reverse("dev_index")
        rsp = self.client.get(url)
        self.assertEqual(200, rsp.status_code)
        self.assertTemplateUsed("dev/home.html")


class ViewListTest(ToolsTestsMixin, TestCase):
    def test_view_list_language_specified(self):
        url = reverse(
            "view_list_language_specified",
            kwargs={
                "category": "licenses",
                "language_code": "nl",
            },
        )
        rsp = self.client.get(url)
        self.assertEqual(200, rsp.status_code)
        self.assertTemplateUsed("list.html")

    def test_view_list_language_specified_invalid(self):
        url = reverse(
            "view_list_language_specified",
            kwargs={
                "category": "licenses",
                "language_code": "xyz",
            },
        )
        rsp = self.client.get(url)
        self.assertEqual(404, rsp.status_code)
        self.assertTemplateUsed("list.html")

    def test_view_list(self):
        url = reverse("view_list", kwargs={"category": "publicdomain"})
        rsp = self.client.get(url)
        self.assertEqual(200, rsp.status_code)
        self.assertTemplateUsed("list.html")

    def test_view_list_licenses(self):
        url = reverse("view_list_licenses")
        rsp = self.client.get(url)
        self.assertEqual(200, rsp.status_code)
        self.assertTemplateUsed("list.html")

    def test_view_list_publicdomain(self):
        url = reverse("view_list_publicdomain")
        rsp = self.client.get(url)
        self.assertEqual(200, rsp.status_code)
        self.assertTemplateUsed("list.html")


class DeedViewViewTest(ToolsTestsMixin, TestCase):
    def validate_deed_text(self, rsp, tool):
        self.assertEqual(200, rsp.status_code)
        text = rsp.content.decode("utf-8")
        if (
            "INVALID_VARIABLE" in text
        ):  # Some unresolved variable in the template
            msgs = ["INVALID_VARIABLE in output"]
            for line in text.splitlines():
                if "INVALID_VARIABLE" in line:
                    msgs.append(line)
            self.fail("\n".join(msgs))

        expected, unexpected = expected_and_unexpected_strings_for_tool(tool)
        for s in expected:
            with self.subTest("|".join([tool.unit, tool.version, s])):
                self.assertContains(rsp, s)
        for s in unexpected:
            with self.subTest("|".join([tool.unit, tool.version, s])):
                self.assertNotContains(rsp, s)

    def test_text_in_deeds(self):
        for tool in Tool.objects.filter(version="4.0"):
            with self.subTest(tool.identifier):
                # Test in English and for 4.0 since that's how we've set up
                # the strings to test for
                url = build_path(
                    base_url=tool.base_url,
                    document="deed",
                    language_code="en",
                )
                rsp = self.client.get(url)
                self.assertEqual(f"{rsp.status_code} {url}", f"200 {url}")
                self.validate_deed_text(rsp, tool)

    def test_deed_translation_by_40_es(self):
        # Test with valid Deed & UX and valid Legal Code translations
        legal_code = LegalCode.objects.get(
            tool__unit="by",
            tool__version="4.0",
            language_code="es",
        )
        url = legal_code.deed_url
        rsp = self.client.get(url)
        text = rsp.content.decode("utf-8")
        self.assertEqual(f"{rsp.status_code} {url}", f"200 {url}")
        if (
            "INVALID_VARIABLE" in text
        ):  # Some unresolved variable in the template
            msgs = ["INVALID_VARIABLE in output"]
            for line in text.splitlines():
                if "INVALID_VARIABLE" in line:
                    msgs.append(line)
            self.fail("\n".join(msgs))
        self.assertContains(rsp, "Atribución")
        self.assertContains(rsp, "No hay restricciones adicionales")
        self.assertContains(rsp, "Avisos")

    def test_deed_translation_by_40_gl(self):
        # Test with valid Deed & UX and *invalid* Legal Code translations
        language_code = "gl"
        tool = Tool.objects.get(
            unit="by",
            version="4.0",
        )
        url = os.path.join(
            "/",
            tool.category,
            tool.unit,
            tool.version,
            f"deed.{language_code}",
        )
        rsp = self.client.get(url)
        text = rsp.content.decode("utf-8")
        self.assertEqual(f"{rsp.status_code} {url}", f"200 {url}")
        if (
            "INVALID_VARIABLE" in text
        ):  # Some unresolved variable in the template
            msgs = ["INVALID_VARIABLE in output"]
            for line in text.splitlines():
                if "INVALID_VARIABLE" in line:
                    msgs.append(line)
            self.fail("\n".join(msgs))
        self.assertContains(rsp, "Atribución")
        self.assertContains(rsp, "Sen restricións adicionais")
        self.assertContains(rsp, "Notas")

    def test_deed_translation_by_30_es_gl(self):
        # Test with valid Deed & UX and *invalid* Legal Code translations
        # (with no jurisdiction default language legal code, but with
        #  global default lanage legal code)
        language_code = "gl"
        tool = Tool.objects.get(
            unit="by",
            version="3.0",
            jurisdiction_code="es",
        )
        url = os.path.join(
            "/",
            tool.category,
            tool.unit,
            tool.version,
            tool.jurisdiction_code,
            f"deed.{language_code}",
        )
        rsp = self.client.get(url)
        text = rsp.content.decode("utf-8")
        self.assertEqual(f"{rsp.status_code} {url}", f"200 {url}")
        if (
            "INVALID_VARIABLE" in text
        ):  # Some unresolved variable in the template
            msgs = ["INVALID_VARIABLE in output"]
            for line in text.splitlines():
                if "INVALID_VARIABLE" in line:
                    msgs.append(line)
            self.fail("\n".join(msgs))
        self.assertContains(rsp, "Atribución")
        self.assertContains(rsp, "Sen restricións adicionais")
        self.assertContains(rsp, "Notas")

    def test_view_deed_template_body_tools(self):
        lc = LegalCode.objects.get(
            tool__unit="by", tool__version="4.0", language_code="en"
        )
        url = lc.deed_url
        rsp = self.client.get(url)
        self.assertEqual(200, rsp.status_code)
        self.assertTemplateUsed("includes/deed_body_legal_tools.html")

    def test_view_deed_template_body_zero(self):
        lc = LegalCode.objects.get(tool__unit="zero", language_code="en")
        url = lc.deed_url
        rsp = self.client.get(url)
        self.assertEqual(200, rsp.status_code)
        self.assertTemplateUsed("includes/deed_body_zero.html")

    def test_view_deed_template_body_mark(self):
        lc = LegalCodeFactory(
            tool__base_url="https://creativecommons.org/publicdomain/"
            "mark/1.0/",
            tool__unit="mark",
            tool__version="1.0",
            language_code="en",
        )
        url = lc.deed_url
        rsp = self.client.get(url)
        self.assertEqual(200, rsp.status_code)
        self.assertTemplateUsed("includes/deed_body_mark.html")

    def test_view_deed_template_body_certification(self):
        lc = LegalCodeFactory(
            tool__base_url="https://creativecommons.org/publicdomain/"
            "certification/1.0/us/",
            tool__unit="certification",
            tool__version="1.0",
            tool__jurisdiction_code="us",
            language_code="en",
        )
        url = lc.deed_url
        rsp = self.client.get(url)
        self.assertEqual(200, rsp.status_code)
        self.assertTemplateUsed("includes/deed_body_certification.html")

    def test_view_deed_template_body_unimplemented(self):
        lc = LegalCodeFactory(
            tool__base_url="https://creativecommons.org/licenses/x/0.0",
            tool__unit="x",
            tool__version="0.0",
            language_code="en",
        )
        url = lc.deed_url
        rsp = self.client.get(url)
        self.assertEqual(200, rsp.status_code)
        self.assertTemplateUsed("includes/deed_body_unimplemented.html")

    def test_view_deed_invalid_language(self):
        lc = LegalCode.objects.get(
            tool__unit="zero",
            language_code="en",
        )
        url = lc.deed_url.replace("deed.en", "deed.xx")
        rsp = self.client.get(url)
        self.assertEqual(404, rsp.status_code)

    def test_view_deed_jurisdiction_language(self):
        lc = LegalCode.objects.get(
            tool__unit="by-sa",
            tool__version="3.0",
            tool__jurisdiction_code="es",
            language_code="es",
        )
        tool = lc.tool

        language_code = "fr"
        lc = LegalCodeFactory(tool=tool, language_code=language_code)
        # "<code:unit>/<version:version>/<jurisdiction:jurisdiction>
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

    def test_view_deed_jurisdiction(self):
        lc = LegalCode.objects.get(
            tool__unit="by-sa",
            tool__version="3.0",
            tool__jurisdiction_code="es",
            language_code="es",
        )
        url = lc.deed_url
        rsp = self.client.get(url)
        self.assertEqual(200, rsp.status_code)

    def test_view_deed_zero(self):
        lc = LegalCode.objects.get(
            tool__unit="zero",
            tool__version="1.0",
            language_code="en",
        )
        url = lc.deed_url
        rsp = self.client.get(url)
        self.assertEqual(200, rsp.status_code)

    def test_view_deed_replaced_specified_language(self):
        lc = LegalCode.objects.get(
            tool__unit="by",
            tool__version="2.0",
            language_code="en",
        )
        url = lc.deed_url
        rsp = self.client.get(url)
        self.assertEqual(200, rsp.status_code)
        self.assertTemplateUsed("includes/notice_newer_license.html")

    def test_view_deed_replaced_jurisdiction_language(self):
        lc = LegalCode.objects.get(
            tool__unit="by-sa",
            tool__version="3.0",
            tool__jurisdiction_code="es",
            language_code="ca",
        )
        url = lc.deed_url
        rsp = self.client.get(url)
        self.assertEqual(200, rsp.status_code)
        self.assertTemplateUsed("includes/notice_newer_license.html")

    # def test_deed_for_superseded_tool(self):
    #     unit = "by-nc-sa"
    #     version = "2.0"  # No 4.0 licenses have been superseded
    #
    #     new_tool = Tool.objects.get(
    #         unit=unit, version="3.0", jurisdiction_code=""
    #     )
    #     tool = Tool.objects.get(
    #         unit=unit, version=version, jurisdiction_code=""
    #     )
    #     tool.is_replaced_by = new_tool
    #     tool.save()
    #     rsp = self.client.get(tool.deed_url)
    #     self.validate_deed_text(rsp, tool)
    #
    # def test_jurisdictions(self):
    #     for code in ["es", "igo"]:
    #         with self.subTest(code):
    #             tool = ToolFactory(
    #                 unit="by-nd-sa",
    #                 jurisdiction_code="es",
    #                 version="3.7",
    #                 requires_share_alike=True,
    #                 permits_distribution=False,
    #                 requires_attribution=True,
    #                 prohibits_commercial_use=False,
    #                 permits_derivative_works=False,
    #             )
    #             rsp = self.client.get(tool.deed_url)
    #             self.validate_deed_text(rsp, tool)
    #
    # def test_language(self):
    #     tool = (
    #         Tool.objects.filter(
    #             unit="by-nd",
    #             version="4.0",
    #             legal_codes__language_code="es",
    #         )
    #         .first()
    #     )
    #     rsp = self.client.get(tool.deed_url)
    #     self.validate_deed_text(rsp, tool)
    #
    # def test_use_jurisdiction_default_language(self):
    #     """
    #     If no language specified, but jurisdiction default language is not
    #     english, use that language instead of english.
    #     """
    #     tool = Tool.objects.filter(
    #         version="3.0",
    #         jurisdiction_code="fr"
    #     ).first()
    #     url = reverse(
    #         "view_deed_jurisdiction",
    #         kwargs=dict(
    #             unit=tool.unit,
    #             version=tool.version,
    #             jurisdiction=tool.jurisdiction_code,
    #         ),
    #     )
    #     rsp = self.client.get(url)
    #     context = rsp.context
    #     self.assertEqual("fr", context["target_lang"])


class ViewLegalCodeTest(TestCase):
    #    def test_view_legal_code_with_jurisdiction_without_language_specified(
    #        self
    #    ):
    #        lc = LegalCodeFactory(
    #            tool__category="licenses",
    #            tool__version="3.0",
    #            language_code="de",
    #            tool__jurisdiction_code="de",
    #        )
    #        url = reverse(
    #            "tools_default_language_with_jurisdiction",
    #            kwargs=dict(
    #                version="3.0",
    #                jurisdiction="de",
    #                unit=lc.tool.unit,
    #            ),
    #        )
    #        rsp = self.client.get(url)
    #        self.assertEqual(200, rsp.status_code)
    #        self.assertTemplateUsed(rsp, "legalcode.html")
    #        self.assertTemplateUsed(
    #            rsp, "includes/legalcode_crude_html.html"
    #        )
    #        context = rsp.context
    #        self.assertContains(rsp, 'lang="de"')
    #        self.assertEqual(lc, context["legal_code"])

    def test_view_legal_code_identifying_jurisdiction_default_language(self):
        language_code = "de"
        lc = LegalCodeFactory(
            html="crude",
            language_code=language_code,
            tool__category="licenses",
            tool__base_url="https://creativecommons.org"
            "/licenses/by/3.0/de/",
            tool__unit="by",
            tool__version="3.0",
            tool__jurisdiction_code="de",
        )
        url = lc.legal_code_url
        rsp = self.client.get(url)
        self.assertEqual(200, rsp.status_code)
        self.assertTemplateUsed(rsp, "legalcode.html")
        self.assertTemplateUsed(rsp, "includes/legalcode_crude_html.html")
        context = rsp.context
        self.assertContains(rsp, f'lang="{language_code}"')
        self.assertEqual(lc, context["legal_code"])

    @override_settings(
        LANGUAGES_AVAILABLE_DEEDS_UX=["ar", settings.LANGUAGE_CODE],
    )
    def test_view_legal_code_40(self):
        tool = ToolFactory(
            category="licenses",
            base_url="https://creativecommons.org/licenses/by/4.0/",
            unit="by",
            version="4.0",
        )
        for language_code in ["ar", "es", settings.LANGUAGE_CODE]:
            lc = LegalCodeFactory(
                tool=tool,
                language_code=language_code,
            )
            url = lc.legal_code_url
            rsp = self.client.get(url)
            self.assertEqual(200, rsp.status_code)
            self.assertTemplateUsed(rsp, "legalcode.html")
            for template in (
                "base.html",
                "legalcode.html",
                "includes/notice_about_cc_and_trademark.html",
                "includes/notice_about_licenses_and_cc.html",
                "includes/footer.html",
                "includes/header.html",
                "includes/legalcode_licenses_4.0.html",
                "includes/legalcode_contextual_menu.html",
                "includes/related_links.html",
                "includes/use_of_licenses.html",
            ):
                self.assertTemplateUsed(rsp, template)
            context = rsp.context
            self.assertEqual(lc, context["legal_code"])
            self.assertContains(rsp, f'lang="{language_code}"')
            if language_code == "es":
                self.assertContains(rsp, 'dir="ltr"')
            elif language_code == "ar":
                self.assertContains(rsp, 'dir="rtl"')

    @override_settings(
        LANGUAGES_AVAILABLE_DEEDS_UX=["es", settings.LANGUAGE_CODE],
    )
    def test_view_legal_code_30_default_translated(self):
        language_code = "ast"
        lc = LegalCodeFactory(
            tool__category="licenses",
            tool__base_url="https://creativecommons.org/licenses/by/3.0/es/",
            tool__unit="by",
            tool__version="3.0",
            tool__jurisdiction_code="es",
            language_code=language_code,
            html="<html></html>",
        )
        url = lc.legal_code_url
        rsp = self.client.get(url)
        self.assertEqual(200, rsp.status_code)
        self.assertTemplateUsed(rsp, "legalcode.html")
        self.assertTemplateUsed(rsp, "includes/legalcode_crude_html.html")
        context = rsp.context
        self.assertEqual(lc, context["legal_code"])
        self.assertContains(rsp, f'lang="{language_code}"')
        self.assertContains(rsp, 'dir="ltr"')

    @override_settings(
        LANGUAGES_AVAILABLE_DEEDS_UX=[settings.LANGUAGE_CODE],
    )
    def test_view_legal_code_30_default_untranslated(self):
        language_code = "ast"
        lc = LegalCodeFactory(
            tool__category="licenses",
            tool__base_url="https://creativecommons.org/licenses/by/3.0/es/",
            tool__unit="by",
            tool__version="3.0",
            tool__jurisdiction_code="es",
            language_code=language_code,
            html="<html></html>",
        )
        url = lc.legal_code_url
        rsp = self.client.get(url)
        self.assertEqual(200, rsp.status_code)
        self.assertTemplateUsed(rsp, "legalcode.html")
        self.assertTemplateUsed(rsp, "includes/legalcode_crude_html.html")
        context = rsp.context
        self.assertEqual(lc, context["legal_code"])
        self.assertContains(rsp, f'lang="{language_code}"')
        self.assertContains(rsp, 'dir="ltr"')

    # NOTE: plaintext functionality disabled
    # def test_view_legal_code_plain_text(self):
    #     tool = ToolFactory(
    #         base_url="https://creativecommons.org/licenses/by/4.0/",
    #         version="4.0",
    #     )
    #     for language_code in [settings.LANGUAGE_CODE]:
    #         lc = LegalCodeFactory(
    #             tool=tool,
    #             language_code=language_code,
    #         )
    #         url = lc.plain_text_url
    #         rsp = self.client.get(url)
    #         self.assertEqual(
    #             'text/plain; charset="utf-8"',
    #             rsp._headers["content-type"][1]
    #         )
    #         self.assertEqual(200, rsp.status_code)
    #         self.assertGreater(len(rsp.content.decode()), 0)
    #     lc = LegalCodeFactory(
    #         tool__version="3.0",
    #         language_code="fr",
    #         tool__unit="by",
    #         tool__jurisdiction_code="ch",
    #     )
    #     url = lc.plain_text_url
    #     rsp = self.client.get(url)
    #     self.assertEqual(
    #         'text/plain; charset="utf-8"', rsp._headers["content-type"][1]
    #     )
    #     self.assertEqual(200, rsp.status_code)
    #     self.assertGreater(len(rsp.content.decode()), 0)

    def test_legal_code_translation_by_40_es(self):
        language_code = "es"
        legal_code = LegalCodeFactory(
            tool__category="licenses",
            tool__base_url="https://creativecommons.org/licenses/by/4.0/",
            tool__unit="by",
            tool__version="4.0",
            language_code=language_code,
        )
        url = legal_code.legal_code_url
        rsp = self.client.get(url)
        text = rsp.content.decode("utf-8")
        self.assertEqual(f"{rsp.status_code} {url}", f"200 {url}")
        self.assertEqual("es", rsp.context["legal_code"].language_code)
        if (
            "INVALID_VARIABLE" in text
        ):  # Some unresolved variable in the template
            msgs = ["INVALID_VARIABLE in output"]
            for line in text.splitlines():
                if "INVALID_VARIABLE" in line:
                    msgs.append(line)
            self.fail("\n".join(msgs))
        self.assertContains(rsp, "Sección 1 – Definiciones")
        self.assertContains(
            rsp, 'Sección 4 – Derechos "Sui Generis" sobre Bases de Datos.'
        )
        self.assertContains(rsp, "Sección 8 – Interpretación")

    def test_view_legal_code_replaced_specified_language(self):
        by_40 = LegalCodeFactory(
            tool__category="licenses",
            tool__base_url="https://creativecommons.org/licenses/by/4.0/",
            tool__unit="by",
            tool__version="4.0",
            language_code="es",
        )
        by_30 = LegalCodeFactory(
            tool__category="licenses",
            tool__base_url="https://creativecommons.org/licenses/by/3.0/",
            tool__unit="by",
            tool__version="3.0",
            tool__is_replaced_by=by_40.tool,
            language_code="es",
        )
        url = by_30.legal_code_url
        rsp = self.client.get(url)
        self.assertEqual(200, rsp.status_code)
        self.assertTemplateUsed("includes/notice_newer_license.html")

    def test_view_legal_code_replaced_jurisdiction_language(self):
        by_40 = LegalCodeFactory(
            tool__category="licenses",
            tool__base_url="https://creativecommons.org/licenses/by/4.0/",
            tool__unit="by",
            tool__version="4.0",
            language_code="es",
        )
        by_30_es = LegalCodeFactory(
            tool__category="licenses",
            tool__base_url="https://creativecommons.org/licenses/by/3.0/es/",
            tool__unit="by",
            tool__version="3.0",
            tool__jurisdiction_code="es",
            tool__is_replaced_by=by_40.tool,
            language_code="ast",
        )
        url = by_30_es.legal_code_url
        rsp = self.client.get(url)
        self.assertEqual(200, rsp.status_code)
        self.assertTemplateUsed("includes/notice_newer_license.html")

    def test_view_legal_code_replaced_default_language(self):
        by_40 = LegalCodeFactory(
            tool__category="licenses",
            tool__base_url="https://creativecommons.org/licenses/by/4.0/",
            tool__unit="by",
            tool__version="4.0",
            language_code="en",
        )
        by_30_es = LegalCodeFactory(
            tool__category="licenses",
            tool__base_url="https://creativecommons.org/licenses/by/3.0/es/",
            tool__unit="by",
            tool__version="3.0",
            tool__jurisdiction_code="es",
            tool__is_replaced_by=by_40.tool,
            language_code="es",
        )
        url = by_30_es.legal_code_url
        rsp = self.client.get(url)
        self.assertEqual(200, rsp.status_code)
        self.assertTemplateUsed("includes/notice_newer_license.html")


class ViewBranchStatusTest(TestCase):
    def setUp(self):
        self.translation_branch = TranslationBranchFactory(
            language_code="fr",
        )

    # TODO: evalute when branch status is re-implemented
    # def test_simple_branch(self):
    #     url = reverse(
    #         "branch_status", kwargs=dict(id=self.translation_branch.id)
    #     )
    #     with mock.patch("legal_tools.views.git"):
    #         with mock.patch.object(LegalCode, "get_pofile"):
    #             with mock.patch(
    #                 "legal_tools.views.branch_status_helper"
    #             ) as mock_helper:
    #                 mock_helper.return_value = {
    #                     "official_git_branch": settings.OFFICIAL_GIT_BRANCH,
    #                     "branch": self.translation_branch,
    #                     "commits": [],
    #                     "last_commit": None,
    #                 }
    #                 r = self.client.get(url)
    #                 # Call a second time to test cache and fully exercise
    #                 # branch_status()
    #                 self.client.get(url)
    #     mock_helper.assert_called_with(mock.ANY, self.translation_branch)
    #     self.assertTemplateUsed(r, "dev/branch_status.html")
    #     context = r.context
    #     self.assertEqual(self.translation_branch, context["branch"])
    #     self.assertEqual(
    #         settings.OFFICIAL_GIT_BRANCH, context["official_git_branch"]
    #     )

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


# Translation Branch Status is not yet supported
#
# class ViewTranslationStatusTest(TestCase):
#    def test_view_dev_index_translation_status(self):
#        TranslationBranchFactory()
#        TranslationBranchFactory()
#        TranslationBranchFactory()
#
#        # Ensure there is at least one language information dictionary without
#        # a bidi key
#        del settings.LANG_INFO["en"]["bidi"]
#
#        url = reverse("dev_index")
#        with mock.patch.object(LegalCode, "get_pofile"):
#            rsp = self.client.get(url)
#        self.assertTemplateUsed(rsp, "dev/index.html")
#        context = rsp.context
#        self.assertEqual(3, len(context["branches"]))


class ViewMetadataTest(TestCase):
    def test_view_metadata(self):
        ToolFactory(category="licenses", unit="by", version="1.1")
        ToolFactory(category="publicdomain", unit="zero", version="1.1")
        with mock.patch.object(Tool, "get_metadata") as mock_get_metadata:
            mock_get_metadata.return_value = {"foo": "bar"}
            rsp = self.client.get(reverse("metadata"))
        self.assertEqual(200, rsp.status_code)
        mock_get_metadata.assert_called_with()
        self.assertEqual(
            b"licenses:\n- by_11: &id001\n    foo: bar\n"
            b"publicdomain:\n- zero_11: *id001\n",
            rsp.content,
        )


class ViewNsHtmlTest(TestCase):
    def test_view_ns_html(self):
        for url in ["/rdf/ns", "/rdf/ns.html"]:
            rsp = self.client.get(url)
            self.assertTemplateUsed("ns.html")
            self.assertEqual(rsp.status_code, 200)


class ViewPageNotFoundTest(TestCase):
    def test_view_page_not_found(self):
        url = "/d-o-e-s/n.o.t/e_x_i_s_t"
        rsp = self.client.get(url)
        self.assertTemplateUsed("404.html")
        self.assertEqual(rsp.status_code, 404)


class RenderRedirect(TestCase):
    def test_render_redirect_en_ltr(self):
        destination = "DESTINATION"
        language_code = "en"
        title = "TITLE"
        rendered = render_redirect(title, destination, language_code)
        rendered = rendered.decode("utf-8")
        self.assertTemplateUsed("redirect.html")
        self.assertIn(f'dir="ltr" lang="{language_code}">', rendered)
        self.assertIn(f"Redirect to: {title}", rendered)
        self.assertIn(f'<meta content="0;url={destination}"', rendered)

    def test_render_redirect_ar_rtl(self):
        destination = "DESTINATION"
        language_code = "ar"
        title = "TITLE"
        rendered = render_redirect(title, destination, language_code)
        rendered = rendered.decode("utf-8")
        self.assertTemplateUsed("redirect.html")
        self.assertIn(f'dir="rtl" lang="{language_code}">', rendered)
        self.assertIn(f"Redirect to: {title}", rendered)
        self.assertIn(f'<meta content="0;url={destination}"', rendered)


class ViewLegalToolRdf(ToolsTestsMixin, TestCase):
    def validate_rdf_properties(self, tool, content):
        base_url_http = convert_https_to_http(tool.base_url)
        logo_uris = generate_foaf_logo_uris(
            tool.unit, tool.version, tool.jurisdiction_code
        )
        self.assertIn(
            f'<cc:License rdf:about="{base_url_http}">',
            content,
        )
        creator_url_http = convert_https_to_http(tool.creator_url)
        self.assertIn(
            f'<dcterms:creator rdf:resource="{creator_url_http}"/>',
            content,
        )
        self.assertIn(
            f"<dcterms:hasVersion>{tool.version}</dcterms:hasVersion>",
            content,
        )
        self.assertIn(
            f"<dcterms:identifier>{tool.unit}</dcterms:identifier>",
            content,
        )
        self.assertIn(
            f'<foaf:logo rdf:resource="{logo_uris["large"]}"/>',
            content,
        )
        self.assertIn(
            f'<foaf:logo rdf:resource="{logo_uris["small"]}"/>',
            content,
        )

    def test_view_legal_tool_rdf_singles_mixin(self):
        for tool in Tool.objects.all():
            url = build_path(
                base_url=tool.base_url,
                document="rdf",
            )
            response = self.client.get(url)
            content = response.content.decode()
            self.assertEqual(f"{response.status_code} {url}", f"200 {url}")
            with self.subTest(tool.identifier):
                self.validate_rdf_properties(tool, content)

    def test_view_legal_tool_rdf_singles_faker(self):
        ToolFactory()
        for tool in Tool.objects.all():
            url = build_path(
                base_url=tool.base_url,
                document="rdf",
            )
            response = self.client.get(url)
            content = response.content.decode()
            self.assertEqual(f"{response.status_code} {url}", f"200 {url}")
            with self.subTest(tool.identifier):
                self.validate_rdf_properties(tool, content)

    def test_view_legal_tool_rdf_source(self):
        tool = Tool.objects.get(unit="by", version="4.0")
        url = build_path(
            base_url=tool.base_url,
            document="rdf",
        )
        response = self.client.get(url)
        content = response.content.decode()
        self.assertEqual(f"{response.status_code} {url}", f"200 {url}")
        self.assertIn(
            "<dcterms:source>http://creativecommons.org/licenses/by/3.0/"
            "</dcterms:source>",
            content,
        )

    def test_view_legal_tool_rdf_index_mixin(self):
        url = os.path.join(
            Tool.objects.first().creator_url, "rdf", "index.rdf"
        )
        response = self.client.get(url)
        content = response.content.decode()
        self.assertEqual(f"{response.status_code} {url}", f"200 {url}")
        for tool in Tool.objects.all():
            with self.subTest(tool.identifier):
                self.validate_rdf_properties(tool, content)

    def test_view_legal_tool_rdf_index_faker(self):
        ToolFactory()
        url = os.path.join(
            Tool.objects.first().creator_url, "rdf", "index.rdf"
        )
        response = self.client.get(url)
        content = response.content.decode()
        self.assertEqual(f"{response.status_code} {url}", f"200 {url}")
        for tool in Tool.objects.all():
            with self.subTest(tool.identifier):
                self.validate_rdf_properties(tool, content)

    def test_view_legal_tool_rdf_images_mixin(self):
        url = os.path.join(
            Tool.objects.first().creator_url, "rdf", "images.rdf"
        )
        response = self.client.get(url)
        content = response.content.decode()
        self.assertEqual(f"{response.status_code} {url}", f"200 {url}")
        for tool in Tool.objects.all():
            with self.subTest(tool.identifier):
                logo_uris = generate_foaf_logo_uris(
                    tool.unit, tool.version, tool.jurisdiction_code
                )
                self.assertIn(
                    f'  <rdf:Description rdf:about="{logo_uris["large"]}">\n'
                    "    <exif:height>31</exif:height>\n"
                    "    <exif:width>88</exif:width>\n"
                    "  </rdf:Description>\n",
                    content,
                )
                self.assertIn(
                    f'  <rdf:Description rdf:about="{logo_uris["small"]}">\n'
                    "    <exif:height>15</exif:height>\n"
                    "    <exif:width>80</exif:width>\n"
                    "  </rdf:Description>\n",
                    content,
                )


class ViewLegacyPlaintext(ToolsTestsMixin, TestCase):
    def test_view_legacy_plaintext_file_exists(self):
        tool = Tool.objects.get(unit="by", version="4.0")
        url = build_path(base_url=tool.base_url, document="legalcode")
        url = f"{url}.txt"
        response = self.client.get(url)
        content = response.content.decode()
        self.assertEqual(f"{response.status_code} {url}", f"200 {url}")
        self.assertEqual(response.headers["Content-Type"], "text/plain")
        self.assertIn("Attribution 4.0 International", content)

    def test_view_legacy_plaintext_file_does_not_exist(self):
        tool = Tool.objects.get(unit="by", version="2.0")
        url = build_path(base_url=tool.base_url, document="legalcode")
        url = f"{url}.txt"
        response = self.client.get(url)
        self.assertEqual(f"{response.status_code} {url}", f"404 {url}")
