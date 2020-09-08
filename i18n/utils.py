from contextlib import ContextDecorator

from babel import Locale, UnknownLocaleError
from django.utils import translation
from django.utils.encoding import force_text
from django.utils.translation import ugettext, activate, get_language
from django.utils.translation.trans_real import DjangoTranslation, deactivate_all

from i18n import DEFAULT_LANGUAGE_CODE, DEFAULT_JURISDICTION_LANGUAGES


CACHED_APPLICABLE_LANGS = {}
CACHED_WELL_TRANSLATED_LANGS = {}


# def get_locale_dir(locale_name):
#     localedir = settings.LOCALE_PATHS[0]
#     return os.path.join(localedir, locale_name, "LC_MESSAGES")
#
#
# def locales_with_directories():
#     """
#     Return list of locale names under our locale dir.
#     """
#     dir = settings.LOCALE_PATHS[0]
#     return [item for item in os.listdir(dir) if os.path.isdir(os.path.join(dir, item))]


LANGUAGE_JURISDICTION_MAPPING = {}
JURISDICTION_CURRENCY_LOOKUP = {
    "jp": "jp",
    "at": "eu",
    "be": "eu",
    "cy": "eu",
    "ee": "eu",
    "fi": "eu",
    "fr": "eu",
    "de": "eu",
    "gr": "eu",
    "ie": "eu",
    "it": "eu",
    "lu": "eu",
    "mt": "eu",
    "nl": "eu",
    "pt": "eu",
    "sk": "eu",
    "si": "eu",
    "es": "eu",
}


def get_language_for_jurisdiction(jurisdiction_code, default_language=DEFAULT_LANGUAGE_CODE):
    langs = DEFAULT_JURISDICTION_LANGUAGES.get(jurisdiction_code, [])
    if len(langs) == 1:
        return langs[0]
    return default_language


def get_locale_text_orientation(locale_identifier: str) -> str:
    """
    Find out whether the locale is ltr or rtl
    """
    try:
        locale = Locale.parse(locale_identifier)
    except UnknownLocaleError:
        raise ValueError("No locale found with identifier %r" % locale_identifier)
    return "ltr" if locale.character_order == "left-to-right" else "rtl"


def rtl_context_stuff(locale_identifier):
    """
    This is to accomodate the old templating stuff, which requires:
     - text_orientation
     - is_rtl
     - is_rtl_align

    We could probably adjust the templates to just use
    text_orientation but maybe we'll do that later.
    """
    text_orientation = get_locale_text_orientation(locale_identifier)

    # 'rtl' if the request locale is represented right-to-left;
    # otherwise an empty string.
    is_rtl = text_orientation == "rtl"

    # Return the appropriate alignment for the request locale:
    # 'text-align:right' or 'text-align:left'.
    if text_orientation == "rtl":
        is_rtl_align = "text-align: right"
    else:
        is_rtl_align = "text-align: left"

    return {
        "get_ltr_rtl": text_orientation,
        "is_rtl": is_rtl,
        "is_rtl_align": is_rtl_align,
    }


# def get_well_translated_langs(
#     threshold=settings.TRANSLATION_THRESHOLD,
#     trans_file=DEFAULT_CSV_FILE,
#     append_english=True,
# ):
#     """
#     Get an alphebatized and name-rendered list of all languages above
#     a certain threshold of translation.
#
#     Keyword arguments:
#     - threshold: percentage that languages should be translated at or above
#     - trans_file: specify from which CSV file we're gathering statistics.
#         Used for testing, You probably don't need this.
#     - append_english: Add English to the list, even if it's completely
#         "untranslated" (since English is the default for messages,
#         nobody translates it)
#
#     Returns:
#       An alphebatized sequence of dicts, where each element consists
#       of the following keys:
#        - code: the language code
#        - name: the translated name of this language
#       for each available language.
#       An unsorted set of all qualified language codes
#     """
#     cache_key = (threshold, trans_file, append_english)
#
#     if cache_key in CACHED_WELL_TRANSLATED_LANGS:
#         return CACHED_WELL_TRANSLATED_LANGS[cache_key]
#
#     trans_stats = get_all_trans_stats(trans_file)
#
#     qualified_langs = set(
#         [
#             lang
#             for lang, data in trans_stats.items()
#             if data["percent_trans"] >= threshold
#         ]
#     )
#
#     # Add english if necessary.
#     if "en" not in qualified_langs and append_english:
#         qualified_langs.add("en")
#
#     # this loop is long hand for clarity; it's only done once, so
#     # the additional performance cost should be negligible
#     result = []
#
#     for code in qualified_langs:
#         # Come up with names for languages in their own languages
#         gettext = ugettext_for_locale(code)
#         if code in mappers.LANG_MAP:
#             # we (should) have a translation for this name...
#             name = gettext(mappers.LANG_MAP[code])
#             result.append(dict(code=code, name=name))
#
#     result = sorted(result, key=lambda lang: lang["name"].lower())
#
#     CACHED_WELL_TRANSLATED_LANGS[cache_key] = result
#
#     return result


def ugettext_for_locale(locale):
    def _wrapped_ugettext(message):
        with translation.override(locale):
            return force_text(ugettext(message))

    return _wrapped_ugettext


TRANSLATION_THRESHOLD = 80
CACHED_TRANS_STATS = {}


# def get_all_trans_stats(trans_file=DEFAULT_CSV_FILE):
#     """
#     Get all of the statistics on all translations, how much they are done
#
#     Keyword arguments:
#     - trans_file: specify from which CSV file we're gathering statistics.
#         Used for testing, You probably don't need this.
#
#     Returns:
#       A dictionary of dictionaries formatted like:
#       {'no': {  # key is the language name
#          'num_messages': 564,  # number of messages, total
#          'num_trans': 400,  # number of messages translated
#          'num_fuzzy': 14,  # number of fuzzy messages
#          'num_untrans': 150,  # number of untranslated, non-fuzzy messages
#          'percent_trans': 70},  # percentage of file translated
#        [...]}
#     """
#     # return cached statistics, if available
#     if trans_file in CACHED_TRANS_STATS:
#         return CACHED_TRANS_STATS[trans_file]
#
#     if not os.path.exists(trans_file):
#         raise IOError(
#             f"No such CSV file {trans_file}.  Maybe run `python manage.py transstats`?"
#         )
#
#     reader = csv.DictReader(open(trans_file, "r"), CSV_HEADERS)
#     stats = {}
#
#     # record statistics
#     for line in reader:
#         num_messages = int(line["num_messages"])
#         num_trans = int(line["num_trans"])
#         num_fuzzy = int(line["num_fuzzy"])
#         num_untrans = num_messages - num_trans - num_fuzzy
#         percent_trans = int(line["percent_trans"])
#
#         stats[line["lang"]] = {
#             "num_messages": num_messages,
#             "num_trans": num_trans,
#             "num_fuzzy": num_fuzzy,
#             "num_untrans": num_untrans,
#             "percent_trans": percent_trans,
#         }
#
#     # cache and return
#     CACHED_TRANS_STATS[trans_file] = stats
#     return stats


def locale_to_lower_upper(locale):
    """
    Take a locale, regardless of style, and format it like "en_US"
    """
    if "-" in locale:
        lang, country = locale.split("-", 1)
        return "%s_%s" % (lang.lower(), country.upper())
    elif "_" in locale:
        lang, country = locale.split("_", 1)
        return "%s_%s" % (lang.lower(), country.upper())
    else:
        return locale.lower()


# def applicable_langs(locale):
#     """
#     Return all available languages "applicable" to a requested locale.
#     """
#     cache_key = (locale,)
#     if cache_key in CACHED_APPLICABLE_LANGS:
#         return CACHED_APPLICABLE_LANGS[cache_key]
#
#     mo_path = settings.LOCALE_PATHS[0]
#
#     applicable_langs = []
#     if os.path.exists(os.path.join(mo_path, locale)):
#         applicable_langs.append(locale)
#
#     if "_" in locale:
#         root_lang = locale.split("_")[0]
#         if os.path.exists(os.path.join(mo_path, root_lang)):
#             applicable_langs.append(root_lang)
#
#     if "en" not in applicable_langs:
#         applicable_langs.append("en")
#
#     # Don't cache silly languages that only fallback to en anyway, to
#     # (semi-)prevent caching infinite amounts of BS
#     if not locale == "en" and len(applicable_langs) == 1:
#         print("Not caching result")
#         return applicable_langs
#
#     CACHED_APPLICABLE_LANGS[cache_key] = applicable_langs
#     return applicable_langs


class activate_domain_language(ContextDecorator):
    def __init__(self, domain, language):
        self.domain = domain
        self.language = language

    def __enter__(self):
        lang_plus_domain = f"{self.language}_{self.domain}".replace("-", "_")

        from django.utils.translation.trans_real import _translations

        if lang_plus_domain not in _translations:
            trans = DjangoTranslation(language=lang_plus_domain, domain=self.domain)
            _translations[lang_plus_domain] = trans

        self.old_language = get_language()
        activate(lang_plus_domain)

    def __exit__(self, exc_type, exc_value, traceback):
        if self.old_language is None:
            deactivate_all()
        else:
            activate(self.old_language)
