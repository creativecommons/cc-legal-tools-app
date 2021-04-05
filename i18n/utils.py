# Standard library
import os
import re
from contextlib import contextmanager

# Third-party
import polib
from babel import Locale, UnknownLocaleError
from django.conf import settings
from django.utils.encoding import force_text
from django.utils.translation import override, ugettext
from django.utils.translation.trans_real import DjangoTranslation, translation

# First-party/Local
from i18n import (
    DEFAULT_JURISDICTION_LANGUAGES,
    DEFAULT_LANGUAGE_CODE,
    DJANGO_LANGUAGE_CODES,
    FILENAME_LANGUAGE_CODES,
)

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
#     return [
#         item for item in os.listdir(dir)
#         if os.path.isdir(os.path.join(dir, item))
#     ]


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


# This function looks like a good candidate for caching, but we might be
# changing the translated files while running and need to be sure we always
# read and use the one that's there right now. Anyway, this site doesn't
# need to perform all that well, since it just generates static files.
def get_translation_object(
    *, django_language_code: str, domain: str
) -> DjangoTranslation:
    """
    Return a DjangoTranslation object suitable to activate
    when we're wanting to render templates for this language code and domain.
    (The domain is typically specific to one or a few licenses that
    have common translations.)
    """

    license_locale_dir = os.path.join(
        settings.TRANSLATION_REPOSITORY_DIRECTORY, "translations"
    )
    # Start with a translation object for the domain for this license.
    license_translation_object = DjangoTranslation(
        language=django_language_code,
        domain=domain,
        localedirs=[license_locale_dir],
    )
    # Add a fallback to the standard Django translation for this language. This
    # gets us the non-legalcode parts of the pages.
    license_translation_object.add_fallback(translation(django_language_code))

    return license_translation_object


@contextmanager
def active_translation(translation: DjangoTranslation):
    """
    Context manager to do stuff within its context with a
    particular translation object set as the active translation.
    (Use ``get_translation_object`` to get a translation
    object to use with this.)

    Bypasses all the language code stuff that Django does
    when you use its ``activate(language_code)`` function.

    The translation object should be a DjangoTranslation
    (from django.utils.translation.trans_real) or a subclass.

    Warning: this *does* make assumptions about the internals
    of Django's translation system that could change on us.
    It doesn't seem likely, though.
    """
    # import non-public value here to keep its scope
    # as limited as possible:
    # Third-party
    from django.utils.translation.trans_real import _active

    # Either _active.value points at a DjangoTranslation
    # object, or _active has no 'value' attribute.
    previous_translation = getattr(_active, "value", None)
    _active.value = translation

    yield

    if previous_translation is None:
        del _active.value
    else:
        _active.value = previous_translation


def save_pofile_as_pofile_and_mofile(pofile: polib.POFile, pofile_path: str):
    """Returns pofile_abspath, mofile_abspath"""
    pofile.save(pofile_path)
    mofilepath = re.sub(r"\.po$", ".mo", pofile_path)
    pofile.save_as_mofile(mofilepath)
    return (pofile_path, mofilepath)


def save_content_as_pofile_and_mofile(path: str, content: bytes):
    """Returns pofile_abspath, mofile_abspath"""
    pofile = polib.pofile(pofile=content.decode(), encoding="utf-8")
    return save_pofile_as_pofile_and_mofile(pofile, path)


def get_pofile_content(pofile: polib.POFile) -> str:
    """
    Return the content of the pofile object - a string
    that contains what would be in the po file on the disk
    if we saved it.
    """
    # This isn't really worth its own function, except that mocking
    # __unicode__ for tests is a pain, and it's easier to have this
    # function so we can just mock it.
    return pofile.__unicode__()


def cc_to_django_language_code(cc_language_code: str) -> str:
    """
    Given a CC language code, return the language code that Django
    uses to represent that language.
    """
    return DJANGO_LANGUAGE_CODES.get(cc_language_code, cc_language_code)


def cc_to_filename_language_code(cc_language_code: str) -> str:
    """
    Given a CC language code, return the language code to use
    in its gettext translation files.
    """
    return FILENAME_LANGUAGE_CODES.get(cc_language_code, cc_language_code)


def get_default_language_for_jurisdiction(
    jurisdiction_code, default_language=DEFAULT_LANGUAGE_CODE
):
    # Input: a jurisdiction code
    # Output: a CC language code
    return DEFAULT_JURISDICTION_LANGUAGES.get(
        jurisdiction_code, default_language
    )


def get_locale_text_orientation(locale_identifier: str) -> str:
    """
    Find out whether the locale is ltr or rtl
    """
    try:
        locale = Locale.parse(locale_identifier, sep="-")
    except UnknownLocaleError:
        raise ValueError(
            "No locale found with identifier %r" % locale_identifier
        )
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
        with override(locale):
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
#             f"No such CSV file {trans_file}. Maybe run"
#             " `python manage.py transstats`?"
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
