# Standard library
import os
import re
from contextlib import contextmanager

# Third-party
import dateutil.parser
import polib
from babel import Locale
from babel.core import UnknownLocaleError
from django.conf import settings
from django.conf.locale import LANG_INFO
from django.utils import translation

# First-party/Local
from i18n import (
    DEFAULT_JURISDICTION_LANGUAGES,
    JURISDICTION_NAMES,
    LANGMAP_DJANGO_TO_REDIRECTS,
    LANGMAP_DJANGO_TO_TRANSIFEX,
    LANGMAP_LEGACY_TO_DJANGO,
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
) -> translation.trans_real.DjangoTranslation:
    """
    Return a DjangoTranslation object suitable to activate when we're wanting
    to render templates for this language code and domain.  (The domain is
    typically specific to one or a few licenses that have common translations.)

    This fuction requires the legal code locales path to have been added to
    Django settings.LOCALE_PATHS
    """

    # Start with a translation object for the domain for this license.
    license_translation_object = translation.trans_real.DjangoTranslation(
        language=django_language_code,
        domain=domain,
    )
    # Add a fallback to the standard Django translation for this language. This
    # gets us the non-legal-code parts of the pages.
    license_translation_object.add_fallback(
        translation.trans_real.translation(django_language_code)
    )

    return license_translation_object


@contextmanager
def active_translation(
    translation_obj: translation.trans_real.DjangoTranslation,
):
    """
    Context manager to do stuff within its context with a particular
    translation object set as the active translation.  (Use
    ``get_translation_object`` to get a translation object to use with this.)

    Bypasses all the language code stuff that Django does when you use its
    ``activate(language_code)`` function.

    The translation object should be a
    django.utils.translation.trans_real.DjangoTranslation object or a subclass.

    WARNING: this *does* make assumptions about the internals of Django's
    translation system that could change on us.  It doesn't seem likely,
    though.
    """
    _active = translation.trans_real._active

    # Either _active.value points at a DjangoTranslation
    # object, or _active has no 'value' attribute.
    previous_translation = getattr(_active, "value", None)
    _active.value = translation_obj

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


def get_pofile_content(pofile: polib.POFile) -> str:  # pragma: no cover
    """
    Return the content of the pofile object - a string that contains what would
    be in the po file on the disk if we saved it.

    This isn't really worth its own function, except that mocking __unicode__
    for tests is a pain, and it's easier to have this function so we can just
    mock it.
    """
    return pofile.__unicode__()


def get_pofile_path(
    locale_or_legalcode: str,
    language_code: str,
    translation_domain: str,
    data_dir=None,
):
    if data_dir is None:
        data_dir = settings.DATA_REPOSITORY_DIR
    pofile_path = os.path.abspath(
        os.path.realpath(
            os.path.join(
                data_dir,
                locale_or_legalcode,
                translation.to_locale(language_code),
                "LC_MESSAGES",
                f"{translation_domain}.po",
            )
        )
    )
    return pofile_path


def get_pofile_creation_date(pofile_obj: polib.POFile):
    try:
        po_creation_date = pofile_obj.metadata["POT-Creation-Date"]
    except KeyError:
        return None
    try:
        creation_date = dateutil.parser.parse(po_creation_date)
        return creation_date
    except dateutil.parser._parser.ParserError:
        return None


def get_pofile_revision_date(pofile_obj: polib.POFile):
    try:
        po_revision_date = pofile_obj.metadata["PO-Revision-Date"]
    except KeyError:
        return None
    try:
        revision_date = dateutil.parser.parse(po_revision_date)
        return revision_date
    except dateutil.parser._parser.ParserError:
        return None


def map_django_to_redirects_language_codes(django_language_code: str) -> list:
    """
    Given a Django language code, return a list of languages codes that should
    redirect to it.

    Django language codes are lowercase IETF language tags

    At a minimum, the returned redirect_codes is a list containing only the
    UPPERCASE Django language code.
    """

    redirect_codes = []
    legacy_codes = LANGMAP_DJANGO_TO_REDIRECTS.get(django_language_code, [])
    legacy_codes.append(django_language_code)
    for language_code in legacy_codes:
        # Only lowercase language codes are expected
        assert language_code == language_code.lower()
        redirect_codes.append(language_code)
        redirect_codes.append(language_code.upper())
        for separator in ["-", "@", "_"]:
            if separator in language_code:
                parts = language_code.split(separator)
                # add variant with all parts after the first UPPERCASE
                redirect_codes.append(
                    separator.join(
                        [
                            parts[0],
                        ]
                        + [part.upper() for part in parts[1:]]
                    )
                )
                # add variant with all parts after the first Titlecase
                redirect_codes.append(
                    separator.join(
                        [
                            parts[0],
                        ]
                        + [part.title() for part in parts[1:]]
                    )
                )
    redirect_codes = sorted(list(set(redirect_codes)))
    redirect_codes.remove(django_language_code)
    return redirect_codes


def map_django_to_redirects_language_codes_lowercase(
    django_language_code: str,
) -> list:
    """
    Given a Django language code, return a list of lowercase languages codes
    that should redirect to it. The list may be empty.

    Django language codes are lowercase IETF language tags
    """
    redirect_codes = map_django_to_redirects_language_codes(
        django_language_code
    )
    redirect_codes = [
        redirect_code.lower()
        for redirect_code in redirect_codes
        if redirect_code.lower() != django_language_code
    ]
    redirect_codes = sorted(list(set(redirect_codes)))
    return redirect_codes


def map_django_to_transifex_language_code(django_language_code: str) -> str:
    """
    Given a Django language code, return a Transifex language code.

    Django language codes are lowercase IETF language tags

    Transifex language codes are POSIX Locales
    """
    transifex_language_code = django_language_code
    # Lookup special cases
    transifex_language_code = LANGMAP_DJANGO_TO_TRANSIFEX.get(
        transifex_language_code,
        transifex_language_code,
    )
    return transifex_language_code


def map_legacy_to_django_language_code(legacy_language_code: str) -> str:
    """
    Given a Legacy language code, return a Django language code.

    Legacy language codes include:
    - POSIX Locales (ex. Transifex language codes)
    - conventential IETF language tags (instead of lowercase, ex. zh-Hans)

    Django language codes are lowercase IETF language tag
    """
    django_language_code = legacy_language_code
    # Normalize: lowercase
    django_language_code = django_language_code.lower()
    # Noarmalize: use dash
    django_language_code = django_language_code.replace("@", "-")
    django_language_code = django_language_code.replace("_", "-")
    # Lookup special cases
    django_language_code = LANGMAP_LEGACY_TO_DJANGO.get(
        django_language_code,
        django_language_code,
    )
    return django_language_code


def get_default_language_for_jurisdiction(
    jurisdiction_code, default_language=settings.LANGUAGE_CODE
):
    # Input: a jurisdiction code
    # Output: a CC language code
    return DEFAULT_JURISDICTION_LANGUAGES.get(
        jurisdiction_code, default_language
    )


def get_jurisdiction_name(category, unit, version, jurisdiction_code):
    jurisdiction_name = JURISDICTION_NAMES.get(
        jurisdiction_code, jurisdiction_code
    )
    # For details on nomenclature for unported licenses, see:
    # https://wiki.creativecommons.org/wiki/License_Versions
    if unit in ["zero", "mark"]:
        jurisdiction_name = "Universal"
    elif category == "licenses" and jurisdiction_name.lower() == "unported":
        if version == "4.0":
            jurisdiction_name = "International"
        elif version == "3.0":
            jurisdiction_name = "International (unported)"
        else:
            jurisdiction_name = "Generic (unported)"
    return jurisdiction_name


def load_deeds_ux_translations():
    """
    Process Deed & UX translations (store information on all and track those
    that meet or exceed the TRANSLATION_THRESHOLD).
    """
    deeds_ux_po_file_info = {}
    languages_mostly_translated = []
    for locale_name in os.listdir(settings.DEEDS_UX_LOCALE_PATH):
        language_code = translation.to_language(locale_name)
        pofile_path = get_pofile_path(
            locale_or_legalcode="locale",
            language_code=language_code,
            translation_domain="django",
        )
        if not os.path.isfile(pofile_path):  # pragma: no cover
            continue
        pofile_obj = polib.pofile(pofile_path)
        percent_translated = pofile_obj.percent_translated()
        deeds_ux_po_file_info[language_code] = {
            "percent_translated": percent_translated,
            "creation_date": get_pofile_creation_date(pofile_obj),
            "revision_date": get_pofile_revision_date(pofile_obj),
            "metadata": pofile_obj.metadata,
        }
        update_lang_info(language_code)
        if percent_translated < settings.TRANSLATION_THRESHOLD:
            continue
        languages_mostly_translated.append(language_code)
    deeds_ux_po_file_info = dict(sorted(deeds_ux_po_file_info.items()))
    # Add global settings
    settings.DEEDS_UX_PO_FILE_INFO = deeds_ux_po_file_info
    settings.LANGUAGES_MOSTLY_TRANSLATED = sorted(
        list(set(languages_mostly_translated))
    )


def update_lang_info(language_code):
    """
    Normalize language information using Babel
    """
    order_to_bidi = {
        "left-to-right": False,
        "right-to-left": True,
    }
    locale_name = translation.to_locale(language_code)
    try:
        locale = Locale.parse(locale_name)
        if language_code not in LANG_INFO:
            LANG_INFO[language_code] = {}
        lang_info = LANG_INFO[language_code]
        lang_info["name"] = locale.get_display_name("en")
        lang_info["name_local"] = locale.get_display_name(locale_name)
        lang_info["bidi"] = order_to_bidi[locale.character_order]
    except UnknownLocaleError:
        pass


# def ugettext_for_locale(locale):
#     def _wrapped_ugettext(message):
#         with override(locale):
#             return force_text(ugettext(message))
#
#     return _wrapped_ugettext
#
#
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


# CACHED_TRANS_STATS = {}
#
#
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
