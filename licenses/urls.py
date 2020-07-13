from django.urls import path, register_converter

from licenses.views import license_deed_view


"""
Example deeds at

https://creativecommons.org/licenses/by/4.0/
https://creativecommons.org/licenses/by/4.0/deed.it
https://creativecommons.org/licenses/by-nc-sa/4.0/
https://creativecommons.org/licenses/by-nc-sa/4.0/deed.es

"""


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
    jurisdiction should be ISO 3166-1 alpha-2 country code (ISO 3166-1 alpha-2 - Wikipedia)
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
    """
    These all APPEAR to have the format X.Y, where X and Y are digits.
    To be forgiving, we accept any mix of digits and ".".
    """
    regex = r"[0-9.]+"

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
    ^((?:(en-GB-oed|i-ami|i-bnn|i-default|i-enochian|i-hak|i-klingon|i-lux|i-mingo|i-navajo|i-pwn|i-tao|i-tay|i-tsu|sgn-BE-FR|sgn-BE-NL|sgn-CH-DE)|(art-lojban|cel-gaulish|no-bok|no-nyn|zh-guoyu|zh-hakka|zh-min|zh-min-nan|zh-xiang))|((?:([A-Za-z]{2,3}(-(?:[A-Za-z]{3}(-[A-Za-z]{3}){0,2}))?)|[A-Za-z]{4}|[A-Za-z]{5,8})(-(?:[A-Za-z]{4}))?(-(?:[A-Za-z]{2}|[0-9]{3}))?(-(?:[A-Za-z0-9]{5,8}|[0-9][A-Za-z0-9]{3}))*(-(?:[0-9A-WY-Za-wy-z](-[A-Za-z0-9]{2,8})+))*(-(?:x(-[A-Za-z0-9]{1,8})+))?)|(?:x(-[A-Za-z0-9]{1,8})+))$
    but that might exclude some older tags, so let's just keep it simple for now
    and match any combination of letters, underscores, and dashes.

    (Why underscores? Because of en_GB being used some places.)
    """
    regex = r"[a-zA-Z_-]*"

    def to_python(self, value):
        return value

    def to_url(self, value):
        return value


register_converter(LangConverter, "lang")

urlpatterns = [
    path(
        "<code:license_code>/<version:version>/<jurisdiction:jurisdiction>/deed.<lang:target_lang>",
        license_deed_view,
        name="license_deed_lang_jurisdiction",
    ),
    path(
        "<code:license_code>/<version:version>/<jurisdiction:jurisdiction>/deed",
        license_deed_view,
        name="license_deed_jurisdiction_explicit",
    ),
    path(
        "<code:license_code>/<version:version>/deed.<lang:target_lang>",
        license_deed_view,
        name="license_deed_lang",
    ),
    path(
        "<code:license_code>/<version:version>/deed",
        license_deed_view,
        name="license_deed_explicit",
    ),
    path(
        "<code:license_code>/<version:version>/<jurisdiction:jurisdiction>/",
        license_deed_view,
        name="license_deed_jurisdiction",
    ),
    path(
        "<code:license_code>/<version:version>/", license_deed_view, name="license_deed"
    ),
]
