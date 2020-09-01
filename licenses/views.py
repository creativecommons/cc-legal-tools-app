import re
import urllib.parse

from django.shortcuts import render
from django.utils import translation

from i18n import DEFAULT_LANGUAGE_CODE
from i18n.utils import get_language_for_jurisdiction
from i18n.utils import rtl_context_stuff
from licenses.models import License


DEED_TEMPLATE_MAPPING = {
    # license_code : template name
    "sampling": "licenses/sampling_deed.html",
    "sampling+": "licenses/sampling_deed.html",
    "nc-sampling+": "licenses/sampling_deed.html",
    "devnations": "licenses/devnations_deed.html",
    "CC0": "licenses/zero_deed.html",
    "mark": "licenses/pdmark_deed.html",
    "publicdomain": "licenses/publicdomain_deed.html",
    # others use "licenses/standard_deed.html"
}


# For removing the deed.foo section of a deed url
REMOVE_DEED_URL_RE = re.compile(r"^(.*?/)(?:deed)?(?:\..*)?$")


def home(request):
    # Make a nested set of dictionaries organizing the license deeds by
    # license code, version, and jurisdiction. See the home.html template
    # for how it's used.
    licenses_by_code = {}
    for license in License.objects.order_by(
        "license_code", "-version", "jurisdiction_code"
    ):
        licenses_by_code.setdefault(license.license_code, {})
        licenses_by_code[license.license_code].setdefault(license.version, {})
        licenses_by_code[license.license_code][license.version].setdefault(
            license.jurisdiction_code, []
        )
        licenses_by_code[license.license_code][license.version][
            license.jurisdiction_code
        ].append(license)

    context = {
        "licenses_by_code": licenses_by_code,
    }
    return render(request, "home.html", context)


def license_deed_view(request, license, target_lang):
    """
    Display the page for the deed for this license, in the specified language.
    (There's no URL for this; the other views use this after figuring out which
    license and language to use.)
    """
    template = DEED_TEMPLATE_MAPPING.get(
        license.license_code, "licenses/standard_deed.html"
    )
    context = {
        "license": license,
        "target_lang": target_lang,
        "get_this": "/choose/results-one?license_code=%s&amp;jurisdiction=%s&amp;version=%s&amp;lang=%s"
        % (
            urllib.parse.quote(license.license_code),
            license.jurisdiction_code,
            license.version,
            target_lang,
        ),
    }
    context.update(rtl_context_stuff(target_lang))
    with translation.override(target_lang):
        return render(request, template, context)


def license_deed_view_code_version_jurisdiction_language(
    request, license_code, version, jurisdiction, target_lang
):
    # Any license with this code, version, and jurisdiction will do.
    # Then we'll render the deed template in the target lang.
    license = License.objects.filter(
        license_code=license_code, version=version, jurisdiction_code=jurisdiction,
    ).first()
    return license_deed_view(request, license, target_lang)


def license_deed_view_code_version_jurisdiction(
    request, license_code, version, jurisdiction
):
    """
    If no language specified, but jurisdiction default language is not english,
    use that language instead of english.
    """
    target_lang = get_language_for_jurisdiction(jurisdiction)
    return license_deed_view_code_version_jurisdiction_language(
        request, license_code, version, jurisdiction, target_lang
    )


def license_deed_view_code_version_language(
    request, license_code, version, target_lang
):
    # Any license with this code and version, and no jurisdiction, will do.
    # Then we'll render the deed template in the target lang.
    license = License.objects.filter(
        license_code=license_code, version=version, jurisdiction_code="",
    ).first()
    return license_deed_view(request, license, target_lang)


def license_deed_view_code_version_english(request, license_code, version):
    target_lang = DEFAULT_LANGUAGE_CODE
    return license_deed_view_code_version_language(
        request, license_code, version, target_lang
    )


# ################# 4.0 Styled Pages ########################
# def license_detail(request):
#     return render(request, "licenses/licenses_detail.html")


# def sampling_detail(request):
#     return render(request, "licenses/sampling_deed_detail.html")


# def deed_detail(request):
#     return render(request, "licenses/deed_detail.html")
