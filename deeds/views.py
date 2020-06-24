from distutils.version import StrictVersion
import re
import urllib
from functools import wraps
from typing import List, Optional

import requests
from django.http import HttpResponse, HttpResponseNotFound
from django.shortcuts import render
from django.utils import translation

from deeds import util

# from lxml import etree
# from lxml.cssselect import CSSSelector
# from webob import Response, exc
#
# from cc.engine.decorators import get_license
# from cc.engine import util
# from cc.i18n import ccorg_i18n_setup
# from cc.i18n.util import (
#     get_well_translated_langs, negotiate_locale, locale_to_lower_lower)
# from cc.license import by_code
# from cc.licenserdf.tools.license import license_rdf_filename
#
# from cc.i18n.util import locale_to_lower_upper
# from deeds.util import locale_to_lower_upper, locale_to_lower_lower, get_well_translated_langs, negotiate_locale
from deeds.util import locale_to_lower_upper, locale_to_lower_lower
from licenses.models import Language, License, Jurisdiction


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
REMOVE_DEED_URL_RE = re.compile("^(.*?/)(?:deed)?(?:\..*)?$")


def license_deed_view(
    request, license_code, version, target_lang=None, jurisdiction=None
):
    """
    The main and major deed generating view.
    """
    ##########################
    # Try and get the license.
    ##########################

    license_kwargs = {
        "license_code": license_code,
        "version": version,
    }

    if target_lang:
        license_kwargs["language__code"] = target_lang
    if jurisdiction:
        license_kwargs[
            "jurisdiction__url"
        ] = f"http://creativecommons.org/international/{jurisdiction}/"

    license = License.objects.filter(**license_kwargs).first()

    # FIXME: Do we need the logic from here?
    # license = by_code(
    #     request.matchdict['code'],
    #     jurisdiction=request.matchdict.get('jurisdiction'),
    #     version=request.matchdict.get('version'))
    if not license:
        license_versions = catch_license_versions_from_request(
            license_code, version, target_lang, jurisdiction
        )

        if license_versions:
            # If we can't get it, but others of that code exist, give
            # a special 404.
            return license_catcher(request)
        else:
            # Otherwise, give the normal 404.
            return exc.HTTPNotFound()

    ####################
    # Everything else ;)
    ####################
    # "color" of the license; the color reflects the relative amount
    # of freedom.
    if license.license_code in ("devnations", "sampling"):
        color = "red"
    elif (
        license.license_code.find("sampling") > -1
        or license.license_code.find("nc") > -1
        or license.license_code.find("nd") > -1
    ):
        color = "yellow"
    else:
        color = "green"

    # Get the language this view will be displayed in.
    #  - First checks to see if the routing matchdict specifies the language
    #  - Or, next gets the jurisdictions' default language if the jurisdiction
    #    specifies one
    #  - Otherwise it's english!
    if target_lang:
        pass
    elif license.jurisdiction.default_language:
        target_lang = locale_to_lower_upper(license.jurisdiction.default_language.code)
    else:
        target_lang = "en"

    # True if the legalcode for this license is available in
    # multiple languages (or a single language with a language code different
    # than that of the jurisdiction).
    #
    # Stored in the RDF, we'll just check license.legalcodes() :)
    legalcodes = license.legalcodes(target_lang)
    if len(legalcodes) > 1 or list(legalcodes)[0][2] is not None:
        multi_language = True
        legalcodes = sorted(legalcodes, key=lambda lc: lc[2])
    else:
        multi_language = False

    # Use the lower-dash style for all RDF-related locale stuff
    rdf_style_target_lang = locale_to_lower_lower(target_lang)

    license_title = None
    try:
        license_title = license.translated_title(rdf_style_target_lang)
    except KeyError:
        # don't have one for that language, use default
        license_title = license.translated_title()

    conditions = {}
    for code in license.license_code.split("-"):
        conditions[code] = 1

    # Find out all the active languages
    active_languages = get_well_translated_langs()
    negotiated_locale = negotiate_locale(target_lang)

    # If negotiating the locale says that this isn't a valid language,
    # let's fall back to something that is.
    if target_lang != negotiated_locale:
        base_url = REMOVE_DEED_URL_RE.match(request.path_info).groups()[0]
        redirect_to = base_url + "deed." + negotiated_locale
        return exc.HTTPFound(location=redirect_to)

    main_template = DEED_TEMPLATE_MAPPING.get(
        license.license_code, "licenses/standard_deed.html"
    )

    # We're not using reverse() here because the chooser isn't part
    # of this project.
    get_this = (
        "/choose/results-one?license_code=%s&amp;jurisdiction=%s&amp;version=%s&amp;lang=%s"
        % (
            urllib.quote(license.license_code),
            license.jurisdiction.code,
            license.version,
            target_lang,
        )
    )

    context = {
        "request": request,
        "license_code": license.license_code,
        "license_code_quoted": urllib.quote(license.license_code),
        "license_title": license_title,
        "license": license,
        "multi_language": multi_language,
        "legalcodes": legalcodes,
        "color": color,
        "conditions": conditions,
        "active_languages": active_languages,
        "target_lang": target_lang,
        "jurisdiction": license.jurisdiction.code,
        "get_this": get_this,
    }
    context.update(util.rtl_context_stuff(target_lang))

    return HttpResponse(
        util.render_template(request, target_lang, main_template, context)
    )


def sort_licenses(x: License, y: License) -> int:
    """
    Sort function for licenses.
    Sorts by version, ascending.
    """
    x_version = StrictVersion(x.version)
    y_version = StrictVersion(y.version)

    if x_version > y_version:
        return 1
    elif x_version == y_version:
        return 0
    else:
        return -1


ALL_POSSIBLE_VERSIONS_CACHE = {}


def all_possible_license_versions(
    code: str, jurisdiction: Optional[str] = None
) -> List[str]:
    """
    Given a license code and optional jurisdiction, determine all
    possible license versions available.
    'jurisdiction' should be a short code and not a jurisdiction URI.

    Returns:
     A list of URIs.
    """
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

    license_results = [
        license.about
        for license in sorted(
            License.objects.filter(**license_kwargs), key=sort_licenses
        )
    ]
    ALL_POSSIBLE_VERSIONS_CACHE[cache_key] = license_results
    return license_results


def catch_license_versions_from_request(
    license_code: str, version: str, target_lang: str, jurisdiction: str
) -> List[str]:
    """
    If we're a view that tries to figure out what alternate licenses
    might exist from the user's request, this utility helps look for
    those.

    Returns a list of license URLs.
    """

    license_versions = []
    searches = [[license_code]]
    if jurisdiction:
        # Look to see if there are other licenses of that code, possibly of
        # that jurisdiction.  Otherwise, we'll just look it up by code.  Also,
        # if by jurisdiction fails, by code will be the fallback.
        searches.insert(0, [license_code, jurisdiction])

    for search_args in searches:
        license_versions += all_possible_license_versions(*search_args)
        if license_code == "by-nc-nd":
            other_search = ["by-nd-nc"] + search_args[1:]
            license_versions += all_possible_license_versions(*other_search)
        if license_versions:
            break

    return license_versions


def get_license(view):
    """
    View decorator to look up a license from the view parms
    and pass it in.  license_code, jurisdiction, and version
    must all be in the URL.
    """

    @wraps(view)
    def new_view_func(request, *args, **kwargs):
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


@get_license
def license_rdf_view(request, license):
    rdf_response = Response(file(license_rdf_filename(license.uri)).read())
    rdf_response.headers["Content-Type"] = "application/rdf+xml; charset=UTF-8"
    return rdf_response


@get_license
def license_legalcode_view(request, license):
    return Response("license legalcode")


@get_license
def license_legalcode_plain_view(request, license):
    parser = etree.HTMLParser()
    legalcode = etree.fromstring(fetch_https(license.uri + "legalcode"), parser)

    # remove the CSS <link> tags
    for tag in legalcode.iter("link"):
        tag.getparent().remove(tag)

    # remove the img tags
    for tag in legalcode.iter("img"):
        tag.getparent().remove(tag)

    # remove anchors
    for tag in legalcode.iter("a"):
        tag.getparent().remove(tag)

    # remove //p[@id="header"]
    header_selector = CSSSelector("#header")
    for p in header_selector(legalcode):
        p.getparent().remove(p)

    # add our base CSS into the mix
    etree.SubElement(
        legalcode.find("head"),
        "link",
        {
            "rel": "stylesheet",
            "type": "text/css",
            "href": "https://yui.yahooapis.com/2.6.0/build/fonts/fonts-min.css",
        },
    )

    # return the serialized document
    return Response(etree.tostring(legalcode))


# This function could probably use a better name, but I can't think of
# one!
def license_catcher(request, target_lang: str, jurisdiction: str) -> HttpResponse:
    """
    If someone chooses something like /licenses/by/ (fails to select a
    version, etc) help point them to the available licenses.
    """
    target_lang = util.get_target_lang_from_request(request)

    license_versions = util.catch_license_versions_from_request(request)

    if not license_versions:
        return exc.HTTPNotFound()

    context = {
        "request": request,
        "license_versions": reversed(license_versions),
        "license_class": license_versions[0].license_class,
        "page_style": "bare",
        "target_lang": target_lang,
    }
    context.update(util.rtl_context_stuff(target_lang))

    # This is a helper page, but it's still for not-found situations.
    # 404!
    with translation.override(target_lang):
        return render(
            request,
            "catalog_pages/license_catcher.html",
            context,
            status=404,
        )


def moved_permanently_redirect(request):
    """
    General method for redirecting to something that's moved permanently
    """
    return exc.HTTPMovedPermanently(location=request.matchdict["redirect_to"])
