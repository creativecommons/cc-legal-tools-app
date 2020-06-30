import csv
import os

from babel import Locale
from django.conf import settings
from django.template.loader import get_template
from django.utils import translation
from django.utils.encoding import force_text

from i18n import DEFAULT_CSV_FILE, CSV_HEADERS


def get_locale_dir(locale_name):
    localedir = settings.LOCALE_PATHS[0]
    return os.path.join(localedir, locale_name, "LC_MESSAGES")


def locales_with_directories():
    """
    Return list of locale names under our locale dir.
    """
    dir = settings.LOCALE_PATHS[0]
    return [
        item
        for item in os.listdir(dir)
        if os.path.isdir(os.path.join(dir, item))
    ]


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


def get_locale_text_orientation(locale):
    """
    Find out whether the locale is ltr or rtl
    """
    l = Locale.parse(locale)
    return 'ltr' if l.character_order == 'left-to-right' else 'rtl'


_ACTIVE_LANGUAGES = None


def active_languages():
    """Return a sequence of dicts, where each element consists of the
    following keys:

    * code: the language code
    * name: the translated name of this language

    for each available language."""
    from django.conf import settings
    return settings.LANGUAGES  # ?? FIXME ??

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


CACHED_APPLICABLE_LANGS = {}
CACHED_WELL_TRANSLATED_LANGS = {}


def get_well_translated_langs(threshold=settings.TRANSLATION_THRESHOLD,
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
    from deeds import mappers

    cache_key = (threshold, trans_file, append_english)

    if cache_key in CACHED_WELL_TRANSLATED_LANGS:
        return CACHED_WELL_TRANSLATED_LANGS[cache_key]

    trans_stats = get_all_trans_stats(trans_file)

    qualified_langs = set([
        lang for lang, data in trans_stats.items()
        if data['percent_trans'] >= threshold])

    # Add english if necessary.
    if not 'en' in qualified_langs and append_english:
        qualified_langs.add('en')

    # this loop is long hand for clarity; it's only done once, so
    # the additional performance cost should be negligible
    result = []

    for code in qualified_langs:
        gettext = ugettext_for_locale(code)
        if code in mappers.LANG_MAP:
            # we have a translation for this name...
            name = gettext(mappers.LANG_MAP[code])
            result.append(dict(code=code, name=name))

    result = sorted(result, key=lambda lang: lang['name'].lower())

    CACHED_WELL_TRANSLATED_LANGS[cache_key] = result

    return result


def ugettext_for_locale(locale):
    def _wrapped_ugettext(message):
        with translation.override(locale):
            return force_text(message)
    return _wrapped_ugettext


TRANSLATION_THRESHOLD = 80
CACHED_TRANS_STATS = {}


def get_all_trans_stats(trans_file=DEFAULT_CSV_FILE):
    """
    Get all of the statistics on all translations, how much they are done

    Keyword arguments:
    - trans_file: specify from which CSV file we're gathering statistics.
        Used for testing, You probably don't need this.

    Returns:
      A dictionary of dictionaries formatted like:
      {'no': {  # key is the language name
         'num_messages': 564,  # number of messages, total
         'num_trans': 400,  # number of messages translated
         'num_fuzzy': 14,  # number of fuzzy messages
         'num_untrans': 150,  # number of untranslated, non-fuzzy messages
         'percent_trans': 70},  # percentage of file translated
       [...]}
    """
    # return cached statistics, if available
    if trans_file in CACHED_TRANS_STATS:
        return CACHED_TRANS_STATS[trans_file]

    if not os.path.exists(trans_file):
        raise IOError(
            f"No such CSV file {trans_file}.  Maybe run `python manage.py transstats`?")

    reader = csv.DictReader(open(trans_file, 'r'), CSV_HEADERS)
    stats = {}

    # record statistics
    for line in reader:
        num_messages = int(line['num_messages'])
        num_trans = int(line['num_trans'])
        num_fuzzy = int(line['num_fuzzy'])
        num_untrans = num_messages - num_trans - num_fuzzy
        percent_trans = int(line['percent_trans'])

        stats[line['lang']] = {
            'num_messages': num_messages,
            'num_trans': num_trans,
            'num_fuzzy': num_fuzzy,
            'num_untrans': num_untrans,
            'percent_trans': percent_trans}

    # cache and return
    CACHED_TRANS_STATS[trans_file] = stats
    return stats


def render_template(request, locale, template_path, context):
    """
    Render a Django template with the request in the response.

    Also stores data for unit testing purposes if appropriate.
    """
    # template = TEMPLATE_ENV.get_template(template_path)
    template = get_template(template_path)

    context['request'] = request
    context['locale'] = locale
    if not 'gettext' in context:
       context['gettext'] = ugettext_for_locale(locale)

    rendered = template.render(context)

    return rendered


def locale_to_lower_upper(locale):
    """
    Take a locale, regardless of style, and format it like "en_US"
    """
    if '-' in locale:
        lang, country = locale.split('-', 1)
        return '%s_%s' % (lang.lower(), country.upper())
    elif '_' in locale:
        lang, country = locale.split('_', 1)
        return '%s_%s' % (lang.lower(), country.upper())
    else:
        return locale.lower()
