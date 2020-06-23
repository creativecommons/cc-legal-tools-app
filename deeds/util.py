import os
import pkg_resources
import string
import smtplib
import urllib

from email.MIMEText import MIMEText
import email.Charset
email.Charset.add_charset('utf-8', email.Charset.SHORTEST, None, None)

import RDF
from lxml import etree
import jinja2
import routes
from webob import Response
from zope.component.globalregistry import base
from zope.i18n.interfaces import ITranslationDomain
from zope.i18n import translate

from cc.license._lib import rdf_helper, all_possible_license_versions
from cc.license._lib import functions as cclicense_functions
from cc.i18n import ccorg_i18n_setup
from cc.i18n import mappers
from cc.i18n.gettext_i18n import ugettext_for_locale
from cc.i18n.gettext_i18n import fake_ugettext as _
from cc.i18n.util import negotiate_locale
from cc.i18n.util import locale_to_lower_upper
from cc.i18n.util import get_all_supported_languages


MO_PATH = pkg_resources.resource_filename(
    'cc.i18n', 'mo')


BASE_TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), 'templates')

PERMITS_NAME_MAP = {
    "http://creativecommons.org/ns#DerivativeWorks": "nd",
    }

LANGUAGE_JURISDICTION_MAPPING = {}

JURISDICTION_CURRENCY_LOOKUP = {
    "jp" : "jp",
    "at" : "eu",
    "be" : "eu",
    "cy" : "eu",
    "ee" : "eu",
    "fi" : "eu",
    "fr" : "eu",
    "de" : "eu",
    "gr" : "eu",
    "ie" : "eu",
    "it" : "eu",
    "lu" : "eu",
    "mt" : "eu",
    "nl" : "eu",
    "pt" : "eu",
    "sk" : "eu",
    "si" : "eu",
    "es" : "eu",
}


def currency_symbol_from_request_form(req_form):
    """Returns 'jp', 'eu', or '' depending on what
    currency symbol should be used for the nc logo."""

    try:
        return JURISDICTION_CURRENCY_LOOKUP[req_form["field_jurisdiction"]]
    except KeyError:
        return ""


class Error(Exception): pass


TESTS_ENABLED = False
def _activate_testing():
    """
    Call this to activate testing in util.py
    """
    global TESTS_ENABLED
    TESTS_ENABLED = True


### ~~~~~~~~~~~~~~~~~~~~~~~
### Jinja2 templating stuff
### ~~~~~~~~~~~~~~~~~~~~~~~

def cctrans(locale, logical_key, **trans_values):
    """
    A method for translating via logical keys
    """
    ugettext = ugettext_for_locale(locale)
    return string.Template(ugettext(logical_key)).substitute(
        trans_values)


# Create the template loader
TEMPLATE_LOADER = jinja2.PackageLoader('cc.engine', 'templates')
TEMPLATE_ENV = jinja2.Environment(
    loader=TEMPLATE_LOADER,
    autoescape=True,
    extensions=['jinja2.ext.autoescape', 'jinja2.ext.i18n'])

# Add cctrans to the global context
TEMPLATE_ENV.globals['cctrans'] = cctrans


TEST_TEMPLATE_CONTEXT = {}

def _clear_test_template_context():
    TEST_TEMPLATE_CONTEXT.clear()


def render_template(request, locale, template_path, context):
    """
    Render a template with the request in the response.

    Also stores data for unit testing purposes if appropriate.
    """
    template = TEMPLATE_ENV.get_template(template_path)
    context['request'] = request
    context['locale'] = locale
    if not 'gettext' in context:
       context['gettext'] = ugettext_for_locale(locale)

    rendered = template.render(context)

    if TESTS_ENABLED:
        TEST_TEMPLATE_CONTEXT[template_path] = context

    return rendered


def XXrender_to_response(request, locale, template_path, context):
    """
    Convenience method for rendering a response along with the template
    """
    return Response(
        render_template(request, locale, template_path, context))


def get_locale_file_from_locale(locale):
    """
    Returns the path to the locale file as a string or None if
    that file does not exist.
    """
    language = locale_to_lower_upper(locale)

    this_locale_filename = pkg_resources.resource_filename(
        u'zope.i18n.locales', u'data/%s.xml' % language)

    if os.path.exists(this_locale_filename):
        return this_locale_filename
    else:
        return None
        

def _get_xpath_attribute(etree, path, attribute):
    """
    Get an attribute from a node grabbed from xpath.
    If not found, return None.
    """
    try:
        return etree.xpath(path)[0].attrib[attribute]
    except IndexError, KeyError:
        return None


# XXX: Apparently this is deprecated, I guess?  Keeping for now until
#   we're sure we don't need it.
def get_locale_identity_data(locale):
    """
    Get the identity data for a locale
    """
    locale_filename = get_locale_file_from_locale(locale)
    
    if not locale_filename:
        return {}

    locale_tree = etree.parse(file(locale_filename))
    identity_data = {}
    identity_data['language'] = _get_xpath_attribute(
        locale_tree, '/ldml/identity/language', 'type')
    identity_data['script'] = _get_xpath_attribute(
        locale_tree, '/ldml/identity/script', 'type')
    identity_data['territory'] = _get_xpath_attribute(
        locale_tree, '/ldml/identity/territory', 'type')
    identity_data['variant'] = _get_xpath_attribute(
        locale_tree, '/ldml/identity/variant', 'type')
    
    return identity_data


def get_locale_text_orientation(locale):
    """
    Find out whether the locale is ltr or rtl
    """
    locale_filename = get_locale_file_from_locale(locale)

    if not locale_filename:
        return u'ltr'

    locale_tree = etree.parse(file(locale_filename))
    try:
        char_orientation = locale_tree.xpath(
            '/ldml/layout/orientation')[0].attrib['characters']
        if char_orientation == u'right-to-left':
            return u'rtl'
        else:
            return u'ltr'
    except IndexError:
        return u'ltr'


def subset_dict(orig_dict, subset_keys):
    """
    Take a dictionary, return a subset of it based on a list of
    allowed keys.

    Args:
      - orig_dict: the dictionary to subset
      - subset_keys: a list of keys that are allowed in the new dictionary

    Returns:
      A new dictionary with only the subset keys
    """
    new_dict = {}

    for key in subset_keys:
        if orig_dict.has_key(key):
            new_dict[key] = orig_dict[key]

    return new_dict


def publicdomain_partner_get_params(request_form):
    """
    Take a request form (GET or POST parameters) and use it to
    generate an appropriate urlencoded get parameters to link with on
    a partner interface to the CC0 and/or PDM partner pages
    """
    get_params_dict = subset_dict(
        request_form,
        ['lang', 'partner', 'exit_url', 'stylesheet'])

    get_params = urllib.urlencode(get_params_dict)

    return get_params


_ACTIVE_LANGUAGES = None

def active_languages():
    """Return a sequence of dicts, where each element consists of the
    following keys:

    * code: the language code
    * name: the translated name of this language

    for each available language."""
    global _ACTIVE_LANGUAGES
    if _ACTIVE_LANGUAGES:
        return _ACTIVE_LANGUAGES

    # get a list of avaialable translations
    domain = base.queryUtility(ITranslationDomain, ccorg_i18n_setup.I18N_DOMAIN)
    lang_codes = set(domain.getCatalogsInfo().keys())

    # determine the intersection of available translations and
    # launched jurisdiction locales
    launched_locales = set()
    jurisdictions = cclicense_functions.get_valid_jurisdictions()

    for jurisdiction in jurisdictions:
        query_string = (
            'PREFIX dc: <http://purl.org/dc/elements/1.1/> '
            'SELECT ?lang WHERE {'
            '  <%s> dc:language ?lang}') % jurisdiction

        query = RDF.Query(
            str(query_string),
            query_language='sparql')
        this_juri_locales = set(
            [locale_to_lower_upper(str(result['lang']))
             for result in query.execute(rdf_helper.JURI_MODEL)])

        # Append those locales that are applicable to this domain
        launched_locales.update(lang_codes.intersection(this_juri_locales))

    # XXX: Have to hack in Esperanto here because it's technically an
    # "Unported" language but there is no unported RDF jurisdiction in
    # jurisdictions.rdf..
    launched_locales.add('eo')

    # make our sequence have a predictable order
    launched_locales = list(launched_locales)

    # this loop is long hand for clarity; it's only done once, so
    # the additional performance cost should be negligible
    result = []
    for code in launched_locales:

        if code == 'test': continue

        gettext = ugettext_for_locale(negotiate_locale(code))
        name = gettext(mappers.LANG_MAP[code])
        result.append(dict(code=code, name=name))

    result = sorted(result, key=lambda lang: lang['name'].lower())

    _ACTIVE_LANGUAGES = result

    return result


def get_all_license_urls():
    qstring = """
              PREFIX cc: <http://creativecommons.org/ns#>
              PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>

              SELECT ?luri
              WHERE {
                     ?luri rdf:type cc:License .
                    }
              """
    query = RDF.Query(qstring, query_language='sparql')
    return tuple(str(s['luri'].uri)
                 for s in query.execute(rdf_helper.ALL_MODEL))


def unicode_cleaner(string):
    if isinstance(string, unicode):
        return string

    try:
        return string.decode('utf-8')
    except UnicodeError:
        try:
            return string.decode('latin-1')
        except UnicodeError:
            return string.decode('utf-8', 'ignore')


def rtl_context_stuff(locale):
    """
    This is to accomodate the old templating stuff, which requires:
     - text_orientation
     - is_rtl
     - is_rtl_align

    We could probably adjust the templates to just use
    text_orientation but maybe we'll do that later.
    """
    text_orientation = get_locale_text_orientation(locale)

    # 'rtl' if the request locale is represented right-to-left;
    # otherwise an empty string.
    is_rtl = text_orientation == 'rtl'

    # Return the appropriate alignment for the request locale:
    # 'text-align:right' or 'text-align:left'.
    if text_orientation == 'rtl':
        is_rtl_align = 'text-align: right'
    else:
        is_rtl_align = 'text-align: left'

    return {'get_ltr_rtl': text_orientation,
            'is_rtl': is_rtl,
            'is_rtl_align': is_rtl_align}
    
    
def plain_template_view(template_name, request):
    """
    Not an actual view, but used to build these more tedious views
    """
    target_lang = get_target_lang_from_request(request)

    template = get_zpt_template(
        template_name,
        target_lang=target_lang)
    engine_template = get_zpt_template(
        'macros_templates/engine.pt',
        target_lang=target_lang)

    context = {'request': request,
               'engine_template': engine_template}
    context.update(rtl_context_stuff(target_lang))

    return Response(
        template.pt_render(context))


class UnsafeResource(Error): pass

def safer_resource_filename(package, resource):
    """
    Prevent "../../../../etc/passwd"-like resource_filename attempts
    """
    filename = os.path.abspath(
        pkg_resources.resource_filename(package, resource))
    if not filename.startswith(pkg_resources.resource_filename(package, '')):
        raise UnsafeResource("Resource resolves outside of package")

    return filename


### ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
### Special email test stuff begins HERE
### ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

# We have two "test inboxes" here:
# 
# EMAIL_TEST_INBOX:
# ----------------
#   If you're writing test views, you'll probably want to check this.
#   It contains a list of MIMEText messages.
#
# EMAIL_TEST_MBOX_INBOX:
# ----------------------
#   This collects the messages from the FakeMhost inbox.  It's reslly
#   just here for testing the send_email method itself.
#
#   Anyway this contains:
#    - from
#    - to: a list of email recipient addresses
#    - message: not just the body, but the whole message, including
#      headers, etc.
#
# ***IMPORTANT!***
# ----------------
# Before running tests that call functions which send email, you should
# always call _clear_test_inboxes() to "wipe" the inboxes clean. 

EMAIL_TEST_INBOX = []
EMAIL_TEST_MBOX_INBOX = []


class FakeMhost(object):
    """
    Just a fake mail host so we can capture and test messages
    from send_email
    """
    def connect(self):
        pass

    def sendmail(self, from_addr, to_addrs, message):
        EMAIL_TEST_MBOX_INBOX.append(
            {'from': from_addr,
             'to': to_addrs,
             'message': message})

def _clear_test_inboxes():
    global EMAIL_TEST_INBOX
    global EMAIL_TEST_MBOX_INBOX
    EMAIL_TEST_INBOX = []
    EMAIL_TEST_MBOX_INBOX = []

### ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
### </Special email test stuff>
### ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

def send_email(from_addr, to_addrs, subject, message_body):
    # TODO: make a mock mhost if testing is enabled
    if TESTS_ENABLED:
        mhost = FakeMhost()
    else:
        mhost = smtplib.SMTP()

    mhost.connect()

    message = MIMEText(message_body.encode('utf-8'), 'plain', 'utf-8')
    message['Subject'] = subject
    message['From'] = from_addr
    message['To'] = ', '.join(to_addrs)

    if TESTS_ENABLED:
        EMAIL_TEST_INBOX.append(message)

    return mhost.sendmail(from_addr, to_addrs, message.as_string())


LICENSE_INFO_EMAIL_BODY = _(
    """Thank you for using a Creative Commons legal tool for your work.

You have selected %(license_title)s.
You should include a reference to this on the web page that includes
the work in question.

Here is the suggested HTML:

%(license_html)s

Tips for marking your work can be found at
http://wiki.creativecommons.org/Marking.  Information on the supplied HTML and
metadata can be found at http://wiki.creativecommons.org/CC_REL.

This email and tech support has been brought to you by the nonprofit folks at
Creative Commons. CC relies on donations to provide you with licenses and
services like this. Please consider a donation to our annual fund:
https://creativecommons.net/donate.

Thank you!
Creative Commons Support
info@creativecommons.org""")

LICENSE_INFO_EMAIL_SUBJECT = _(
    'Your Creative Commons License Information')


def send_license_info_email(license_title, license_html,
                            recipient_email, locale):
    """
    Send license information email to a user.

    Arguments:
     - license_title: title of the license
     - license_html: copy-paste license HTML
     - recipient_email: the user that is getting this email
     - locale: language email should be sent in

    Returns:
      A boolean specifying whether or not the email sent successfully
    """

    gettext = ugettext_for_locale(locale)
    email_body = gettext(LICENSE_INFO_EMAIL_BODY) % {
            'license_title': license_title,
            'license_html': license_html}

    try:
        send_email(
            'info@creativecommons.org', [recipient_email],
            translate(
                LICENSE_INFO_EMAIL_SUBJECT,
                target_language=negotiate_locale(locale)),
            email_body)
        return True
    except smtplib.SMTPException:
        return False


ACCEPT_LANG_CACHE = {}
def get_target_lang_from_request(request, default_locale='en'):
    request_form = request.GET or request.POST

    if request_form.has_key('lang') and request_form['lang'] != '':
        return locale_to_lower_upper(request_form['lang'])

    try:
        if request.matchdict.has_key('target_lang'):
            target_lang = request.matchdict['target_lang']
        else:
            header_value = request.accept_language.header_value

            if ACCEPT_LANG_CACHE.has_key(header_value):
                return ACCEPT_LANG_CACHE[header_value]

            # clean the header into something we can use
            accept_lang = []
            for part in header_value.split(","):
                try:
                    locale, quality = map(str.strip, part.split(";"))
                    quality = float(quality)
                except ValueError:
                    locale = part.strip()
                    quality = 1
                accept_lang.append((locale_to_lower_upper(locale), quality))
            
            available = list(get_all_supported_languages())

            def run_matches(accept_lang, available):
                best = -1
                target_lang = None
                for locale, quality in accept_lang:
                    if quality > best and available.count(locale):
                        best = quality
                        target_lang = locale
                return target_lang

            # search for exact matches
            target_lang = run_matches(accept_lang, available)
        
            if not target_lang:
                # search for near matches
                reduced_accept = [(v.split("_")[0], q) for v,q in accept_lang]
                reduced_available = [i.split("_")[0] for i in available]
                target_lang = run_matches(reduced_accept, reduced_available)

    except AttributeError:
        # header was not defined
        header_value = default_locale
        target_lang = None
                              
    if not target_lang:
        # screw it
        target_lang = default_locale

    try:
        ACCEPT_LANG_CACHE[header_value] = target_lang
    except NameError as e:
        # We didn't set the header_value, so don't try to use it as a key
        pass

    return locale_to_lower_upper(target_lang)


def generate_404_response(request, routing, environ, staticdirector):
    """
    Create a 'nice looking' 404 response.
    """
    request.matchdict = {}
    request.urlgen = routes.URLGenerator(routing.mapping, environ)
    request.staticdirect = staticdirector

    target_lang = get_target_lang_from_request(request)

    context = {'page_style': 'bare'}
    context.update(rtl_context_stuff(target_lang))

    return Response(
        render_template(
            request, target_lang,
            'catalog_pages/404.html', context),
        status=404)


def catch_license_versions_from_request(request):
    """
    If we're a view that tries to figure out what alternate licenses
    might exist from the user's request, this utility helps look for
    those.
    """

    license_versions = []
    code = request.matchdict['code']
    searches = [[code]]
    if request.matchdict.has_key('jurisdiction'):
        # Look to see if there are other licenses of that code, possibly of
        # that jurisdiction.  Otherwise, we'll just look it up by code.  Also,
        # if by jurisdiction fails, by code will be the fallback.
        searches.insert(0, [code, request.matchdict['jurisdiction']])

    for search_args in searches:
        license_versions += all_possible_license_versions(*search_args)
        if code == u'by-nc-nd':
            other_search = [u'by-nd-nc'] + search_args[1:]
            license_versions += all_possible_license_versions(*other_search)
        if license_versions:
            break

    return license_versions


def locale_to_lower_upper(locale):
    """
    Take a locale, regardless of style, and format it like "en-us"
    """
    if '-' in locale:
        lang, country = locale.split('-', 1)
        return '%s_%s' % (lang.lower(), country.upper())
    elif '_' in locale:
        lang, country = locale.split('_', 1)
        return '%s_%s' % (lang.lower(), country.upper())
    else:
        return locale.lower()


def locale_to_lower_lower(locale):
    """
    Take a locale, regardless of style, and format it like "en_US"
    """
    if '_' in locale:
        lang, country = locale.split('_', 1)
        return '%s-%s' % (lang.lower(), country.lower())
    else:
        return locale.lower()


# Locale negotiation tools
CACHED_APPLICABLE_LANGS = {}


def negotiate_locale(locale, mo_path=MO_PATH):
    """
    Choose the appropriate locale, using fallbacks, given the
    'requested' locale.

    Actually just a wrapper function for applicable_langs().
    """
    return applicable_langs(locale, mo_path)[0]


def applicable_langs(locale, mo_path=MO_PATH):
    """
    Return all available languages "applicable" to a requested locale.
    """
    cache_key = (locale, mo_path)
    if CACHED_APPLICABLE_LANGS.has_key(cache_key):
        return CACHED_APPLICABLE_LANGS[cache_key]

    applicable_langs = []
    if os.path.exists(os.path.join(mo_path, locale)):
        applicable_langs.append(locale)

    if '_' in locale:
        root_lang = locale.split('_')[0]
        if os.path.exists(os.path.join(mo_path, root_lang)):
            applicable_langs.append(root_lang)

    if not 'en' in applicable_langs:
        applicable_langs.append('en')

    # Don't cache silly languages that only fallback to en anyway, to
    # (semi-)prevent caching infinite amounts of BS
    if not locale == 'en' and len(applicable_langs) == 1:
        return applicable_langs

    CACHED_APPLICABLE_LANGS[cache_key] = applicable_langs
    return applicable_langs
CACHED_WELL_TRANSLATED_LANGS = {}
def get_well_translated_langs(threshold=TRANSLATION_THRESHOLD,
                              trans_file=DEFAULT_CSV_FILE,
                              append_english=True):
    """
    Get an alphebatized and name-rendered list of all languages above
    a certain threshold of translation.

    Keyword arguments:
    - threshold: percentage that languages should be translated at or above
    - trans_file: specify from which CSV file we're gathering statistics.
        Used for testing, You probably don't need this.
    - append_english: Add English to the list, even if it's completely
        "untranslated" (since English is the default for messages,
        nobody translates it)

    Returns:
      An alphebatized sequence of dicts, where each element consists
      of the following keys:
       - code: the language code
       - name: the translated name of this language
      for each available language.
      An unsorted set of all qualified language codes
    """
    from cc.i18n import mappers

    cache_key = (threshold, trans_file, append_english)

    if CACHED_WELL_TRANSLATED_LANGS.has_key(cache_key):
        return CACHED_WELL_TRANSLATED_LANGS[cache_key]

    trans_stats = get_all_trans_stats(trans_file)

    qualified_langs = set([
        lang for lang, data in trans_stats.iteritems()
        if data['percent_trans'] >= threshold])

    # Add english if necessary.
    if not 'en' in qualified_langs and append_english:
        qualified_langs.add('en')

    # this loop is long hand for clarity; it's only done once, so
    # the additional performance cost should be negligible
    result = []

    for code in qualified_langs:
        from cc.i18n.gettext_i18n import ugettext_for_locale
        gettext = ugettext_for_locale(code)
        if code in mappers.LANG_MAP:
            # we have a translation for this name...
            name = gettext(mappers.LANG_MAP[code])
            result.append(dict(code=code, name=name))

    result = sorted(result, key=lambda lang: lang['name'].lower())

    CACHED_WELL_TRANSLATED_LANGS[cache_key] = result

    return result
