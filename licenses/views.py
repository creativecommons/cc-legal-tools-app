import re
from collections import OrderedDict

from django.shortcuts import get_object_or_404, render
from django.utils.translation import override

from i18n import DEFAULT_LANGUAGE_CODE
from i18n.utils import get_language_for_jurisdiction
from licenses.constants import VARYING_MESSAGE_IDS
from licenses.models import LegalCode, License

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
    # Get the list of license codes and languages that occur among the 4.0 licenses
    # to let the template iterate over them as it likes.
    codes_for_40 = (
        License.objects.filter(version="4.0")
        .order_by("license_code")
        .distinct("license_code")
        .values_list("license_code", flat=True)
    )
    languages_for_40 = (
        LegalCode.objects.filter(license__version="4.0")
        .order_by("language_code")
        .distinct("language_code")
        .values_list("language_code", flat=True)
    )

    licenses_by_version = [
        ("4.0", codes_for_40, languages_for_40),
    ]

    context = {
        "licenses_by_version": licenses_by_version,
        # "licenses_by_code": licenses_by_code,
        "legalcodes": LegalCode.objects.filter(
            license__version="4.0", language_code__in=["en", "es", "ar", "de"]
        ).order_by("license__license_code", "language_code"),
    }
    return render(request, "home.html", context)


def view_license(request, license_code, version, jurisdiction=None, language_code=None):
    if language_code is None and jurisdiction:
        language_code = get_language_for_jurisdiction(jurisdiction)
    language_code = language_code or DEFAULT_LANGUAGE_CODE

    legalcode = get_object_or_404(
        LegalCode,
        license__license_code=license_code,
        license__version=version,
        license__jurisdiction_code=jurisdiction or "",
        language_code=language_code,
    )
    translation = legalcode.get_translation_object()
    with override(language=language_code):
        return render(
            request,
            "legalcode_40_page.html",
            {
                "fat_code": legalcode.license.fat_code(),
                "legalcode": legalcode,
                "license_medium": translation.translate("license_medium"),
                "title": translation.translate("license_medium"),
                "translation": translation,  # the full "Translation" object
                "t": translation.translations,  # the msgid -> translated message dictionary
            },
        )


def view_deed(request, license_code, version, jurisdiction=None, language_code=None):
    if language_code is None and jurisdiction:
        language_code = get_language_for_jurisdiction(jurisdiction)
    language_code = language_code or DEFAULT_LANGUAGE_CODE

    legalcode = get_object_or_404(
        LegalCode,
        license__license_code=license_code,
        license__version=version,
        license__jurisdiction_code=jurisdiction or "",
        language_code=language_code,
    )
    translation = legalcode.get_translation_object()
    with override(language=language_code):
        return render(
            request,
            "deed_40.html",
            {
                "fat_code": legalcode.license.fat_code(),
                "legalcode": legalcode,
                "license": legalcode.license,
                "license_medium": translation.translations["license_medium"],
                "title": translation.translations["license_medium"],
                "translation": translation,
                "t": translation.translations,
            },
        )


def translation_consistency(request, version, language_code):  # pragma: no cover
    assert isinstance(version, str)
    legalcodes = LegalCode.objects.filter(
        language_code=language_code, license__version=version
    ).order_by("license__license_code")
    for lc in legalcodes:
        t = lc.get_translation_object()
        lc.num_translated = t.num_translated()
        lc.num_messages = t.num_messages()
        lc.percent_translated = t.percent_translated()

        lc.compared_to = {}
        for lc2 in legalcodes:
            lc.compared_to[lc2.license.license_code] = t.compare_to(
                lc2.get_translation_object()
            )

    sorted_codes = list(
        legalcodes.order_by("license__license_code").values_list(
            "license__license_code", flat=True
        )
    )

    lcs_by_code = {lc.license.license_code: lc for lc in legalcodes}

    row_headers = sorted_codes
    col_headers = sorted_codes

    english_for_key = {}
    for lc in legalcodes:
        license = lc.license
        en_lc = LegalCode.objects.get(language_code="en", license=license)
        english_for_key.update(en_lc.get_translation_object().translations)

    matrix = OrderedDict()
    translation_differences = OrderedDict()
    for row in row_headers:
        if row not in matrix:
            matrix[row] = OrderedDict()
        for col in col_headers:
            row_lc = lcs_by_code[row]
            comparison = row_lc.compared_to[col]
            matrix[row][col] = len(comparison["different_translations"])

            for msgid, translations in comparison["different_translations"].items():
                if msgid not in VARYING_MESSAGE_IDS:
                    key = english_for_key[msgid]
                    if key not in translation_differences:
                        translation_differences[key] = set()
                    for txt in translations:
                        translation_differences[key].add(txt)

    return render(
        request,
        "translation_consistency.html",
        {
            "codes": sorted_codes,
            "col_headers": col_headers,
            "row_headers": row_headers,
            "language_code": language_code,
            "legalcodes": legalcodes,
            "matrix": matrix,
            "translation_differences": translation_differences,
        },
    )
