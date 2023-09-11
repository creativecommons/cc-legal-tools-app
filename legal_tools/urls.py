"""
Example deeds at

https://creativecommons.org/licenses/by/4.0/
https://creativecommons.org/licenses/by/4.0/deed.it
https://creativecommons.org/licenses/by-nc-sa/4.0/
https://creativecommons.org/licenses/by-nc-sa/4.0/deed.es

"""

# Third-party
from django.urls import path, re_path, register_converter
from django.views.generic.base import RedirectView

# First-party/Local
from i18n import LANGUAGE_CODE_REGEX_STRING
from legal_tools.views import (
    view_branch_status,
    view_deed,
    view_dev_index,
    view_image_rdf,
    view_legal_code,
    view_legal_tool_rdf,
    view_list,
    view_metadata,
    view_ns_html,
)

# See Converter functions, below, for a description of the following regex:
RE_CATEGORY = r"licenses|publicdomain"
RE_JURISDICTION = r"[a-z]{2}|igo|scotland"
RE_UNIT = r"(?i)[-a-z0-9+]+"
RE_VERSION = r"[0-9]+[.][0-9]+"


class CategoryConverter:
    """
    Category must be either "licenses" or "publicdomain".
    """

    regex = RE_CATEGORY

    def to_python(self, value):
        return value

    def to_url(self, value):
        return value


register_converter(CategoryConverter, "category")


class UnitConverter:
    """
    units are short lowercase legal tool designations that may contain letters,
    dashes and pluses

    (see UNITS_LICENSES and UNITS_PUBLIC_DOMAIN in legal_tools.models)
    """

    regex = RE_UNIT

    def to_python(self, value):
        return value

    def to_url(self, value):
        return value


register_converter(UnitConverter, "unit")


class JurisdictionConverter:
    """
    jurisdiction should be ISO 3166-1 alpha-2 country code with the exceptions
    of "igo" and "scotland".
    """

    regex = RE_JURISDICTION

    def to_python(self, value):
        return value

    def to_url(self, value):
        return value


register_converter(JurisdictionConverter, "jurisdiction")


class VersionConverter:
    """
    version is in the format MAJOR.MINOR
    """

    regex = RE_VERSION

    def to_python(self, value):
        return value

    def to_url(self, value):
        return value


register_converter(VersionConverter, "version")


class LangConverter:
    """
    Django language codes should be lowercase IETF language tags
    """

    regex = LANGUAGE_CODE_REGEX_STRING

    def to_python(self, value):
        return value

    def to_url(self, value):
        return value


register_converter(LangConverter, "language_code")


# /licenses/
#       overview and links to the licenses (part of this project?)
# /licenses/?lang=es
#       overview and links to the licenses (part of this project?) in Spanish
#
# /licenses/by/4.0
#       deed for BY 4.0 English
# /licenses/by/4.0/deed.es
#       deed for BY 4.0 Spanish
# /licenses/by/4.0/legalcode
#       license BY 4.0 English
# /licenses/by/4.0/legalcode.es
#       license BY 4.0 Spanish
#
# /licenses/by/3.0/
#       deed for BY 3.0 Unported in English
# /licenses/by/3.0/legalcode
#       license for BY 3.0 Unported in English
#
# /licenses/by-nc-sa/3.0/de/
#       deed for by-nc-sa, 3.0, jurisdiction Germany, in German
# /licenses/by-nc-sa/3.0/de/deed.it
#       deed for by-nc-sa, 3.0, jurisdiction Germany, in Italian
# /licenses/by-nc-sa/3.0/de/legalcode
#       license for by-nc-sa, 3.0, jurisdiction Germany, in German
#       (I CANNOT find license for by-nc-sa 3.0 jurisdiction Germany in other
#       languages (/legalcode.it is a 404))
#
# /licenses/by-sa/2.5/ca/
#       deed for BY-SA 2.5, jurisdiction Canada, in English
# /licenses/by-sa/2.5/ca/deed.it
#       deed for BY-SA 2.5, jurisdiction Canada, in Italian
# /licenses/by-sa/2.5/ca/legalcode.en
#       license for BY-SA 2.5, jurisdiction Canada, in English
# /licenses/by-sa/2.5/ca/legalcode.fr
#       license for BY-SA 2.5, jurisdiction Canada, in French
#
# /licenses/by-sa/2.0/uk/
#       deed for BY-SA 2.0, jurisdiction England and Wales, in English
# /licenses/by-sa/2.0/uk/deed.es
#       deed for BY-SA 2.0, jurisdiction England and Wales, in Spanish
# /licenses/by-sa/2.0/uk/legalcode
#       license for BY-SA 2.0, jurisdiction England and Wales, in English


urlpatterns = [
    # DEV #####################################################################
    path(
        "",
        view_dev_index,
        name="dev_index",
    ),
    # METADATA ################################################################
    path(
        "licenses/metadata.yaml",
        view_metadata,
        name="metadata",
    ),
    # LIST PAGES ##############################################################
    # List: with language
    path(
        "<category:category>/list.<language_code:language_code>",
        view_list,
        name="view_list_language_specified",
    ),
    # List: no language
    path(
        "<category:category>/list",
        view_list,
        name="view_list",
    ),
    # List: Licenses list, no language
    path(
        "licenses/list",
        view_list,
        kwargs=dict(category="licenses"),
        name="view_list_licenses",
    ),
    # List: Public Domain list, no language
    path(
        "publicdomain/list",
        view_list,
        kwargs=dict(category="publicdomain"),
        name="view_list_publicdomain",
    ),
    # DEED PAGES ##############################################################
    # Redirect URLs without a document/layer to the deed (no language_code)
    re_path(
        f"^(?P<path>(?:{RE_CATEGORY})/{RE_UNIT}/{RE_VERSION}"
        f"(/(?:{RE_JURISDICTION}))?)/?$",
        # "^(?P<path>licenses/by/4.0)",
        RedirectView.as_view(url="/%(path)s/deed", permanent=False),
        name="nodocument_redirect",
    ),
    # Deed: with Jurisdiction (ported), with language_code
    path(
        "<category:category>/<unit:unit>/<version:version>"
        "/<jurisdiction:jurisdiction>/deed.<language_code:language_code>",
        view_deed,
        name="view_deed_ported_language_specified",
    ),
    # Deed: with Jurisdiction (ported), no language_code
    path(
        "<category:category>/<unit:unit>/<version:version>"
        "/<jurisdiction:jurisdiction>/deed",
        view_deed,
        name="view_deed_ported",
    ),
    # Deed: no Jurisdiction (international/unported), with language_code
    path(
        "<category:category>/<unit:unit>/<version:version>/deed"
        ".<language_code:language_code>",
        view_deed,
        kwargs=dict(jurisdiction=""),
        name="view_deed_unported_language_specified",
    ),
    # Deed: no Jurisdiction (international/unported), no language_code
    path(
        "<category:category>/<unit:unit>/<version:version>/deed",
        view_deed,
        kwargs=dict(jurisdiction=""),
        name="view_deed_unported",
    ),
    # LEGALCODE PAGES #########################################################
    # Legalcode: with Jurisdiction (ported), with language_code
    path(
        "<category:category>/<unit:unit>/<version:version>"
        "/<jurisdiction:jurisdiction>/legalcode.<language_code:language_code>",
        view_legal_code,
        name="view_legal_code_ported_language_specified",
    ),
    # Legalcode: with Jurisdiction (ported), no language_code
    path(
        "<category:category>/<unit:unit>/<version:version>"
        "/<jurisdiction:jurisdiction>/legalcode",
        view_legal_code,
        name="view_legal_code_ported",
    ),
    # Legalcode: no Jurisdiction (international/unported), with language_code
    path(
        "<category:category>/<unit:unit>/<version:version>/legalcode"
        ".<language_code:language_code>",
        view_legal_code,
        kwargs=dict(jurisdiction=""),
        name="view_legal_code_unported_language_specified",
    ),
    # Legalcode: no Jurisdiction (international/unported), no language_code
    path(
        "<category:category>/<unit:unit>/<version:version>/legalcode",
        view_legal_code,
        kwargs=dict(jurisdiction=""),
        name="view_legal_code_unported",
    ),
    # NOTE: plaintext functionality disabled
    # # Plaintext Legalcode: no Jurisdiction (int/unported), no language_code
    # path(
    #     "<category:category>/<unit:unit>/<version:version>/legalcode.txt",
    #     view_legal_code,
    #     kwargs=dict(jurisdiction="", is_plain_text=True),
    #     name="view_legal_code_unported",
    # ),
    # CCREL DOCUMENTS #########################################################
    # Legal tool RDF/XML: no Jurisdiction (international/unported)
    path(
        "<category:category>/<unit:unit>/<version:version>/rdf",
        view_legal_tool_rdf,
        name="view_legal_tool_rdf_unported",
    ),
    # Legal tool RDF/XML: with Jurisdiction (ported)
    path(
        "<category:category>/<unit:unit>/<version:version>/"
        "<jurisdiction:jurisdiction>/rdf",
        view_legal_tool_rdf,
        name="view_legal_tool_rdf_ported",
    ),
    # index.rdf - RDF/XML of all legal tools
    path(
        "rdf/index.rdf",
        view_legal_tool_rdf,
        name="view_legal_tool_rdf_index",
    ),
    # images.rdf - RDF/XML of all legal tool images (badges)
    path(
        "rdf/images.rdf",
        view_image_rdf,
        name="view_image_rdf",
    ),
    # images.rdf - ccREL description & namespace
    re_path(
        r"^rdf/ns",
        view_ns_html,
        name="ns_html",
    ),
    # Redirect /ns to /rdf/ns
    re_path(
        r"^ns",
        RedirectView.as_view(url="/rdf/ns", permanent=False),
        name="ns_html_redirect",
    ),
    # TRANSLATION PAGES #######################################################
    re_path(
        r"^dev/status/(?P<id>\d+)/$",
        view_branch_status,
        name="branch_status",
    ),
]
