"""
Example deeds at

https://creativecommons.org/licenses/by/4.0/
https://creativecommons.org/licenses/by/4.0/deed.it
https://creativecommons.org/licenses/by-nc-sa/4.0/
https://creativecommons.org/licenses/by-nc-sa/4.0/deed.es

"""

# Third-party
from django.urls import path, register_converter

# First-party/Local
from i18n import DEFAULT_LANGUAGE_CODE, LANGUAGE_CODE_REGEX_STRING
from licenses import VERSION_REGEX_STRING
from licenses.views import all_licenses, metadata_view, view_deed, view_license


class LicenseCodeConverter:
    """
    Licenses codes look like "MIT" or "by-sa" or "by-nc-nd" or "CC0".
    We accept any mix of letters, digits, and dashes.
    """

    regex = r"(?i)[-a-z0-9+]+"

    def to_python(self, value):
        return value

    def to_url(self, value):
        return value


register_converter(LicenseCodeConverter, "code")


class JurisdictionConverter:
    """
    jurisdiction should be ISO 3166-1 alpha-2 country code
        ISO 3166-1 alpha-2 - Wikipedia
        https://en.wikipedia.org/wiki/ISO_3166-1_alpha-2

    BUT it also looks as if we use "igo" and "scotland".
    """

    regex = r"[a-z]{2}|igo|scotland"

    def to_python(self, value):
        return value

    def to_url(self, value):
        return value


register_converter(JurisdictionConverter, "jurisdiction")


class VersionConverter:

    regex = VERSION_REGEX_STRING

    def to_python(self, value):
        return value

    def to_url(self, value):
        return value


register_converter(VersionConverter, "version")


class LangConverter:
    """
    language should be RFC 5646 language tag (RFC 5646)
    https://tools.ietf.org/html/rfc5646.html
    However, RFC 5646 was finalized after most of the legacy ccEngine was written.
    Some of the language tags are based on older specs.

    A more specific RFC 5646 regex might be
    ^((?:(en-GB-oed|i-ami|i-bnn|i-default|i-enochian|i-hak|i-klingon|i-lux|i-mingo|i-navajo|i-pwn|i-tao|i-tay|i-tsu|sgn-BE-FR|sgn-BE-NL|sgn-CH-DE)|(art-lojban|cel-gaulish|no-bok|no-nyn|zh-guoyu|zh-hakka|zh-min|zh-min-nan|zh-xiang))|((?:([A-Za-z]{2,3}(-(?:[A-Za-z]{3}(-[A-Za-z]{3}){0,2}))?)|[A-Za-z]{4}|[A-Za-z]{5,8})(-(?:[A-Za-z]{4}))?(-(?:[A-Za-z]{2}|[0-9]{3}))?(-(?:[A-Za-z0-9]{5,8}|[0-9][A-Za-z0-9]{3}))*(-(?:[0-9A-WY-Za-wy-z](-[A-Za-z0-9]{2,8})+))*(-(?:x(-[A-Za-z0-9]{1,8})+))?)|(?:x(-[A-Za-z0-9]{1,8})+))$  # noqa: E501
    but that might exclude some older tags, so let's just keep it simple for
    now and match any combination of letters, underscores, and dashes.

    (Why underscores? Because of en_GB being used some places.)
    """

    regex = LANGUAGE_CODE_REGEX_STRING

    def to_python(self, value):
        return value

    def to_url(self, value):
        return value


register_converter(LangConverter, "lang")


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


# DEEDS
urlpatterns = [
    # Debug page that displays all licenses
    path("all/", all_licenses, name="all_licenses"),
    path("metadata.yaml", metadata_view, name="metadata"),
    #
    # LICENSE PAGES
    #
    path(  # All four specified: /licenses/by-sa/2.5/ca/legalcode.en
        "<code:license_code>/<version:version>/<jurisdiction:jurisdiction>"
        "/legalcode.<lang:language_code>",
        view_license,
        name="view_40_license",
    ),
    path(
        # Jurisdiction empty:
        # e.g. /licenses/by/4.0/legalcode.es - license BY 4.0 Spanish
        "<code:license_code>/<version:version>/legalcode.<lang:language_code>",
        view_license,
        kwargs=dict(jurisdiction=""),
        name="view_40_license",
    ),
    path(
        # Jurisdiction and language empty (default to English):
        # e.g. /licenses/by/4.0/legalcode - license BY 4.0 English
        "<code:license_code>/<version:version>/legalcode",
        view_license,
        name="licenses_default_jurisdiction_and_language",
        kwargs=dict(language_code=DEFAULT_LANGUAGE_CODE, jurisdiction=""),
    ),
    path(
        # Jurisdiction empty:
        # e.g. /licenses/by/4.0/legalcode.es.txt - license BY 4.0 Spanish Plain
        # Text
        "<code:license_code>/<version:version>/legalcode.<lang:language_code>"
        ".txt",
        view_license,
        kwargs=dict(jurisdiction="", is_plain_text=True),
        name="view_40_license_txt",
    ),
    path(
        # Jurisdiction and language empty (default to English):
        # e.g. /licenses/by/4.0/legalcode/index.txt - license BY 4.0 English
        # Plain Text
        "<code:license_code>/<version:version>/legalcode/index.txt",
        view_license,
        name="licenses_default_jurisdiction_and_language_txt",
        kwargs=dict(
            language_code=DEFAULT_LANGUAGE_CODE,
            jurisdiction="",
            is_plain_text=True,
        ),
    ),
    path(
        # Language empty (default to THE JURISDICTION'S LANGUAGE):
        # e.g. /licenses/by-nc-sa/3.0/de/legalcode
        "<code:license_code>/<version:version>/<jurisdiction:jurisdiction>"
        "/legalcode",
        view_license,
        name="licenses_default_language_with_jurisdiction",
    ),
    path(
        # Jurisdiction and language set
        # e.g. /licenses/by-nc-sa/3.0/de/legalcode
        "<code:license_code>/<version:version>/<jurisdiction:jurisdiction>"
        "/legalcode.<lang:language_code>.txt",
        view_license,
        name="licenses_default_language_with_jurisdiction",
        kwargs=dict(is_plain_text=True),
    ),
    #
    # DEED PAGES
    #
    path(
        "<code:license_code>/<version:version>/",
        view_deed,
        name="license_deed_view_code_version_english",
    ),
    path(
        "<code:license_code>/<version:version>/deed.<lang:language_code>",
        view_deed,
        name="license_deed_view_code_version_language",
    ),
    path(
        "<code:license_code>/<version:version>/<jurisdiction:jurisdiction>/",
        view_deed,
        name="license_deed_view_code_version_jurisdiction",
    ),
    path(
        "<code:license_code>/<version:version>/<jurisdiction:jurisdiction>"
        "/deed.<lang:language_code>",
        view_deed,
        name="license_deed_view_code_version_jurisdiction_language",
    ),
]
