import re
import urllib.parse

from distutils.version import StrictVersion
from functools import wraps
from typing import Callable
from typing import List

from django.http import HttpRequest
from django.http import HttpResponse
from django.http import HttpResponseNotFound
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.shortcuts import render
from django.utils import translation

from i18n.utils import get_well_translated_langs
from i18n.utils import locale_to_lower_upper
from i18n.utils import negotiate_locale
from i18n.utils import render_template
from i18n.utils import rtl_context_stuff
from licenses import FREEDOM_COLORS
from licenses.models import Jurisdiction
from licenses.models import License
from licenses.models import TranslatedLicenseName


# def fetch_https(uri):
#     https_uri = re.sub(r'^http://', 'https://', uri)
#     return requests.get(https_uri).text
#
# def licenses_view(request):
#     target_lang = util.get_target_lang_from_request(request)
#
#     context = {
#         'active_languages': get_well_translated_langs(),
#         'page_style': "bare"}
#     context.update(util.rtl_context_stuff(target_lang))
#
#     # Don't cache the response for internationalization reasons
#     response = render(
#         request,
#         'catalog_pages/licenses-index.html',
#         context
#     )
#     response.headers.add('Cache-Control', 'no-cache')
#     return response
#
#
# def publicdomain_view(request):
#     target_lang = util.get_target_lang_from_request(request)
#
#     return render(
#         request,
#         'publicdomain/index.html',
#         {
#             "locale": target_lang,
#         }
#     )

DEED_TEMPLATE_MAPPING = {
    "sampling": "licenses/sampling_deed.html",
    "sampling+": "licenses/sampling_deed.html",
    "nc-sampling+": "licenses/sampling_deed.html",
    "devnations": "licenses/devnations_deed.html",
    "CC0": "licenses/zero_deed.html",
    "mark": "licenses/pdmark_deed.html",
    "publicdomain": "licenses/publicdomain_deed.html",
}


# For removing the deed.foo section of a deed url
REMOVE_DEED_URL_RE = re.compile(r"^(.*?/)(?:deed)?(?:\..*)?$")


def license_deed_view(
    request: HttpRequest,
    license_code: str,
    version: str,
    target_lang: str = None,
    jurisdiction: str = None,
):
    """
    The main and major deed generating view.
    Can be called with various combinations of arguments.
    See urls.py in this same directory.
    """
    # print(f"license_deed_view({license_code}, {version}, {target_lang}, {jurisdiction})")
    ##########################
    # Try and get the license.
    ##########################

    license_kwargs = {
        "license_code": license_code,
        "version": version,
    }

    if target_lang:
        license_kwargs["legal_codes__language__code"] = target_lang
    if jurisdiction:
        jurisdiction_object = get_object_or_404(
            Jurisdiction,
            url=f"http://creativecommons.org/international/{jurisdiction}/",
        )
        license_kwargs["jurisdiction"] = jurisdiction_object

    license = License.objects.filter(**license_kwargs).first()

    if not license:
        print("License not found, checking close matches")
        licenses = catch_license_versions_from_request(
            license_code=license_code,
            jurisdiction=jurisdiction,
            target_lang=target_lang,
        )
        print("Found %d versions" % len(licenses))

        if licenses:
            # If we can't get it, but others of that code exist, give
            # a special 404.
            print("404 but license catcher page")
            return license_catcher(request, license_code, target_lang, jurisdiction)
        else:
            # Otherwise, give the normal 404.
            print("no license found")
            return HttpResponseNotFound()

    ####################
    # Everything else ;)
    ####################
    # "color" of the license; the color reflects the relative amount
    # of freedom.
    color = FREEDOM_COLORS[license.level_of_freedom]

    # Get the language this view will be displayed in.
    #  - First checks to see if the routing matchdict specifies the language
    #  - Or, next gets the jurisdictions' default language if the jurisdiction
    #    specifies one
    #  - Otherwise it's english!
    if target_lang:
        pass
    elif license.jurisdiction and license.jurisdiction.default_language:
        target_lang = locale_to_lower_upper(license.jurisdiction.default_language.code)
    else:
        target_lang = "en"

    # print(license.id)

    # True if the legalcode for this license is available in
    # multiple languages (or a single language with a language code different
    # than that of the jurisdiction).
    legalcodes = license.legalcodes_for_language(target_lang)
    if len(legalcodes) > 1:  # or list(legalcodes)[0][2] is not None:
        multi_language = True
        legalcodes = sorted(
            legalcodes, key=lambda lc: lc[2]
        )  # FIXME: What is this supposed to be sorting by?
    else:
        multi_language = False

    license_title = None
    try:
        license_title = license.translated_title(target_lang)
    except TranslatedLicenseName.DoesNotExist:
        # don't have one for that language, use default
        license_title = license.translated_title()

    # Find out all the active languages
    active_languages = get_well_translated_langs()
    negotiated_locale = negotiate_locale(target_lang)

    # If negotiating the locale says that this isn't a valid language,
    # let's fall back to something that is.
    if target_lang != negotiated_locale:
        base_url = REMOVE_DEED_URL_RE.match(request.path_info).groups()[0]
        redirect_to = base_url + "deed." + negotiated_locale
        return HttpResponseRedirect(redirect_to=redirect_to)

    main_template = DEED_TEMPLATE_MAPPING.get(
        license.license_code, "licenses/standard_deed.html"
    )

    # We're not using reverse() here because the chooser isn't part
    # of this project.
    kwargs = {
        "license_code": license.license_code,
        "jurisdiction": license.jurisdiction and license.jurisdiction.url or "",
        "version": license.version,
        "lang": target_lang,
    }

    get_this = "/choose/results-one?%s" % urllib.parse.urlencode(kwargs)

    context = {
        "request": request,
        "license_code": license.license_code,
        "license_code_quoted": urllib.parse.quote(license.license_code),
        "license_title": license_title,
        "license": license,
        "multi_language": multi_language,
        "legalcodes": legalcodes,
        "color": color,
        "active_languages": active_languages,
        "target_lang": target_lang,
        "jurisdiction": kwargs["jurisdiction"],
        "get_this": get_this,
    }
    context.update(rtl_context_stuff(target_lang))

    return HttpResponse(render_template(request, target_lang, main_template, context))


def sort_licenses(x: License) -> StrictVersion:
    """
    Sort function for licenses (use as key in `sort` and `sorted`).
    Sorts by version, ascending.
    """
    return StrictVersion(x.version)


ALL_POSSIBLE_VERSIONS_CACHE = {}


def all_possible_license_versions(search_args: dict) -> List[License]:
    """
    Given a license code and optional jurisdiction, determine all
    possible license versions available.
    'jurisdiction' should be a short code and not a jurisdiction URI.

    Returns:
     An iterable of License objects
    """
    code = search_args.get("code", None)
    jurisdiction = search_args.get("jurisdiction", None)
    target_lang = search_args.get("target_lang", None)

    cache_key = (code, jurisdiction)
    if cache_key in ALL_POSSIBLE_VERSIONS_CACHE:
        return ALL_POSSIBLE_VERSIONS_CACHE[cache_key]

    license_kwargs = {
        "license_code": code,
    }
    if jurisdiction:
        license_kwargs[
            "jurisdiction__url"
        ] = f"http://creativecommons.org/international/{jurisdiction}/"
    if target_lang:
        license_kwargs["legal_codes__language__code"] = target_lang

    license_results = sorted(
        License.objects.filter(**license_kwargs), key=sort_licenses
    )
    ALL_POSSIBLE_VERSIONS_CACHE[cache_key] = license_results
    return license_results


def catch_license_versions_from_request(
    *, license_code: str, jurisdiction: str, target_lang: str
) -> List[License]:
    """
    If we're a view that tries to figure out what alternate licenses
    might exist from the user's request, this utility helps look for
    those.

    Returns an iterable of License objects.
    """

    licenses = []
    # Most wide search is by code. Lines below this insert more specific
    # searches before this one if we have the information to do those searches.
    searches = [{"code": license_code}]
    if license_code == "by-nc-nd":
        # Some older licenses have nc, nd in the opposite order
        searches.append({"code": "by-nd-nc"})
    if jurisdiction:
        # Look to see if there are other licenses of that code, possibly of
        # that jurisdiction.  Otherwise, we'll just look it up by code.  Also,
        # if by jurisdiction fails, by code will be the fallback.
        for search in list(searches):
            searches.insert(0, dict(search, jurisdiction=jurisdiction))
    if target_lang:
        # Start by looking for this specific language.
        for search in list(searches):
            searches.insert(0, dict(search, target_lang=target_lang))

    for search_args in searches:
        licenses += all_possible_license_versions(search_args)
        if licenses:
            break

    return licenses


def get_license(view) -> Callable[..., HttpResponse]:
    """
    View decorator to look up a license from the view parms
    and pass it in.  license_code, jurisdiction, and version
    must all be in the URL.
    """

    @wraps(view)
    def new_view_func(request: HttpRequest, *args, **kwargs):
        try:
            license = License.objects.get(
                license_code=kwargs["license_code"],
                jurisdiction__code=kwargs["jurisdiction"],
                version=kwargs["version"],
            )
        except License.DoesNotExist:
            return HttpResponseNotFound()
        else:
            kwargs["license"] = license
            del kwargs["license_code"]
            del kwargs["jurisdiction"]
            del kwargs["version"]

        return view(request, *args, **kwargs)

    return new_view_func


# This function could probably use a better name, but I can't think of
# one!
def license_catcher(
    request, license_code: str, target_lang: str, jurisdiction: str
) -> HttpResponse:
    """
    If someone chooses something like /licenses/by/ (fails to select a
    version, etc) help point them to the available licenses.
    """
    licenses = catch_license_versions_from_request(
        license_code=license_code, jurisdiction=jurisdiction, target_lang=target_lang,
    )
    # Returns an iterable of License objects

    if not licenses:
        return HttpResponseNotFound()

    context = {
        "request": request,
        "license_versions": reversed(licenses),
        "license_class": licenses[0].license_class,
        "page_style": "bare",
    }
    if target_lang:
        context["target_lang"] = target_lang
        context.update(rtl_context_stuff(target_lang))
        with translation.override(target_lang):
            # This is a helper page, but it's still for not-found situations.
            # 404!
            return render(
                request, "catalog_pages/license_catcher.html", context, status=404,
            )
    else:
        # This is a helper page, but it's still for not-found situations.
        # 404!
        return render(
            request, "catalog_pages/license_catcher.html", context, status=404,
        )


def home(request):
    # Make a nested set of dictionaries organizing the English licenses by
    # license code, version, and jurisdiction. See the home.html template
    # for how it's used.
    licenses_by_code = {}
    for license in License.objects.filter(
        legal_codes__language__code__startswith="en"
    ).select_related("jurisdiction"):
        licenses_by_code.setdefault(license.license_code, {})
        licenses_by_code[license.license_code].setdefault(license.version, {})
        licenses_by_code[license.license_code][license.version].setdefault(
            license.jurisdiction, []
        )
        licenses_by_code[license.license_code][license.version][
            license.jurisdiction
        ].append(license)

    context = {
        "licenses_by_code": licenses_by_code,
    }
    return render(request, "home.html", context)

################# 4.0 Styled Pages ########################
def license_detail(request):
    return render(request, "licenses/licenses_detail.html")

def sampling_detail(request):
    return render(request, "licenses/sampling_deed.html")

def deed_detail(request):
    return render(request, "licenses/deed_detail.html")
