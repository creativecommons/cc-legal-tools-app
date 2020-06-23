import re
import urllib
import requests
from django.shortcuts import render

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
from deeds.util import locale_to_lower_upper, locale_to_lower_lower, get_well_translated_langs, negotiate_locale


def fetch_https(uri):
    https_uri = re.sub(r'^http://', 'https://', uri)
    return requests.get(https_uri).text

def licenses_view(request):
    target_lang = util.get_target_lang_from_request(request)

    context = {
        'active_languages': get_well_translated_langs(),
        'page_style': "bare"}
    context.update(util.rtl_context_stuff(target_lang))

    # Don't cache the response for internationalization reasons
    response = render(
        request,
        'catalog_pages/licenses-index.html',
        context
    )
    response.headers.add('Cache-Control', 'no-cache')
    return response


def publicdomain_view(request):
    target_lang = util.get_target_lang_from_request(request)

    return render(
        request,
        'publicdomain/index.html',
        {
            "locale": target_lang,
        }
    )


DEED_TEMPLATE_MAPPING = {
    'sampling': 'licenses/sampling_deed.html',
    'sampling+': 'licenses/sampling_deed.html',
    'nc-sampling+': 'licenses/sampling_deed.html',
    'devnations': 'licenses/devnations_deed.html',
    'CC0': 'licenses/zero_deed.html',
    'mark': 'licenses/pdmark_deed.html',
    'publicdomain': 'licenses/publicdomain_deed.html'}


# For removing the deed.foo section of a deed url
REMOVE_DEED_URL_RE = re.compile('^(.*?/)(?:deed)?(?:\..*)?$')


def license_deed_view(request):
    """
    The main and major deed generating view.
    """
    ##########################
    # Try and get the license.
    ##########################
    license = by_code(
        request.matchdict['code'],
        jurisdiction=request.matchdict.get('jurisdiction'),
        version=request.matchdict.get('version'))
    if not license:
        license_versions = util.catch_license_versions_from_request(request)

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
    if license.license_code in ('devnations', 'sampling'):
       color = 'red'
    elif license.license_code.find('sampling') > -1 or \
             license.license_code.find('nc') > -1 or \
             license.license_code.find('nd') > -1:
       color = 'yellow'
    else:
       color = 'green'

    # Get the language this view will be displayed in.
    #  - First checks to see if the routing matchdict specifies the language
    #  - Or, next gets the jurisdictions' default language if the jurisdiction
    #    specifies one
    #  - Otherwise it's english!
    if request.matchdict.has_key('target_lang'):
        target_lang = request.matchdict.get('target_lang')
    elif license.jurisdiction.default_language:
        target_lang = locale_to_lower_upper(
            license.jurisdiction.default_language)
    else:
        target_lang = 'en'

    # True if the legalcode for this license is available in
    # multiple languages (or a single language with a language code different
    # than that of the jurisdiction).
    #
    # Stored in the RDF, we'll just check license.legalcodes() :)
    legalcodes = license.legalcodes(target_lang)
    if len(legalcodes) > 1 \
            or list(legalcodes)[0][2] is not None:
        multi_language = True
        legalcodes = sorted(legalcodes, key=lambda lc: lc[2])
    else:
        multi_language = False

    # Use the lower-dash style for all RDF-related locale stuff
    rdf_style_target_lang = locale_to_lower_lower(target_lang)

    license_title = None
    try:
        license_title = license.title(rdf_style_target_lang)
    except KeyError:
        # don't have one for that language, use default
        license_title = license.title()

    conditions = {}
    for code in license.license_code.split('-'):
        conditions[code] = 1

    # Find out all the active languages
    active_languages = get_well_translated_langs()
    negotiated_locale = negotiate_locale(target_lang)

    # If negotiating the locale says that this isn't a valid language,
    # let's fall back to something that is.
    if target_lang != negotiated_locale:
        base_url = REMOVE_DEED_URL_RE.match(request.path_info).groups()[0]
        redirect_to = base_url + 'deed.' + negotiated_locale
        return exc.HTTPFound(location=redirect_to)

    if DEED_TEMPLATE_MAPPING.has_key(license.license_code):
        main_template = DEED_TEMPLATE_MAPPING[license.license_code]
    else:
        main_template = 'licenses/standard_deed.html'

    get_this = "/choose/results-one?license_code=%s&amp;jurisdiction=%s&amp;version=%s&amp;lang=%s" % (urllib.quote(license.license_code), license.jurisdiction.code, license.version, target_lang)

    context = {
        'request': request,
        'license_code': license.license_code,
        'license_code_quoted': urllib.quote(license.license_code),
        'license_title': license_title,
        'license': license,
        'multi_language': multi_language,
        'legalcodes': legalcodes,
        'color': color,
        'conditions': conditions,
        'active_languages': active_languages,
        'target_lang': target_lang,
        'jurisdiction':license.jurisdiction.code,
        'get_this': get_this,
        }
    context.update(util.rtl_context_stuff(target_lang))

    return Response(
        util.render_template(
            request, target_lang,
            main_template, context))


@get_license
def license_rdf_view(request, license):
    rdf_response = Response(file(license_rdf_filename(license.uri)).read())
    rdf_response.headers['Content-Type'] = 'application/rdf+xml; charset=UTF-8'
    return rdf_response


@get_license
def license_legalcode_view(request, license):
    return Response('license legalcode')


@get_license
def license_legalcode_plain_view(request, license):
    parser = etree.HTMLParser()
    legalcode = etree.fromstring(fetch_https(license.uri + "legalcode"), parser)

    # remove the CSS <link> tags
    for tag in legalcode.iter('link'):
        tag.getparent().remove(tag)

    # remove the img tags
    for tag in legalcode.iter("img"):
        tag.getparent().remove(tag)

    # remove anchors
    for tag in legalcode.iter('a'):
        tag.getparent().remove(tag)

    # remove //p[@id="header"]
    header_selector = CSSSelector('#header')
    for p in header_selector(legalcode):
        p.getparent().remove(p)

    # add our base CSS into the mix
    etree.SubElement(
        legalcode.find("head"), "link",
        {"rel":"stylesheet",
         "type":"text/css",
         "href":"https://yui.yahooapis.com/2.6.0/build/fonts/fonts-min.css"})

    # return the serialized document
    return Response(etree.tostring(legalcode))


# This function could probably use a better name, but I can't think of
# one!
def license_catcher(request):
    """
    If someone chooses something like /licenses/by/ (fails to select a
    version, etc) help point them to the available licenses.
    """
    target_lang = util.get_target_lang_from_request(request)

    license_versions = util.catch_license_versions_from_request(request)

    if not license_versions:
        return exc.HTTPNotFound()

    context = {'request': request,
               'license_versions': reversed(license_versions),
               'license_class': license_versions[0].license_class,
               'page_style': 'bare',
               'target_lang': target_lang}
    context.update(util.rtl_context_stuff(target_lang))

    # This is a helper page, but it's still for not-found situations.
    # 404!
    return Response(
        util.render_template(
            request, target_lang,
            'catalog_pages/license_catcher.html', context),
        status=404)


def moved_permanently_redirect(request):
    """
    General method for redirecting to something that's moved permanently
    """
    return exc.HTTPMovedPermanently(
        location=request.matchdict['redirect_to'])
