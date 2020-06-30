from django.urls import path, register_converter

from deeds.views import license_deed_view


"""
Example deeds at 

https://creativecommons.org/licenses/by/4.0/
https://creativecommons.org/licenses/by/4.0/deed.it
https://creativecommons.org/licenses/by-nc-sa/4.0/
https://creativecommons.org/licenses/by-nc-sa/4.0/deed.es

"""


class LicenseCodeConverter:
    regex = r"[-a-z+]+"

    def to_python(self, value):
        return value

    def to_url(self, value):
        return value


register_converter(LicenseCodeConverter, "code")


class JurisdictionConverter:
    regex = r"[a-zA-Z_-]+"

    def to_python(self, value):
        return value

    def to_url(self, value):
        return value


register_converter(JurisdictionConverter, "jurisdiction")


class VersionConverter:
    regex = r"[0-9.]+"

    def to_python(self, value):
        return value

    def to_url(self, value):
        return value


register_converter(VersionConverter, "version")


class LangConverter:
    regex = r"[a-zA-Z_-]+"

    def to_python(self, value):
        return value

    def to_url(self, value):
        return value


register_converter(LangConverter, "lang")

urlpatterns = [
    path(
        "<code:license_code>/<version:version>/", license_deed_view, name="license_deed"
    ),
    path(
        "<code:license_code>/<version:version>/deed",
        license_deed_view,
        name="license_deed_explicit",
    ),
    path(
        "<code:license_code>/<version:version>/deed.<lang:target_lang>",
        license_deed_view,
        name="license_deed_lang",
    ),
    path(
        "<code:license_code>/<version:version>/<jurisdiction:jurisdiction>/",
        license_deed_view,
        name="license_deed_jurisdiction",
    ),
    path(
        "<code:license_code>/<version:version>/<jurisdiction:jurisdiction>/deed",
        license_deed_view,
        name="license_deed_jurisdiction_explicit",
    ),
    path(
        "<code:license_code>/<version:version>/<jurisdiction:jurisdiction>/deed.<lang:target_lang>",
        license_deed_view,
        name="license_deed_lang_jurisdiction",
    ),
]
