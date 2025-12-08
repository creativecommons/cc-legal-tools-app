# Standard library
import csv
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


def get_translation_object(
    domain: str, language_code: str, language_default: str
) -> translation.trans_real.DjangoTranslation:
    """
    Return a DjangoTranslation object suitable to activate when we're wanting
    to render templates for this language code and domain. (The domain is
    typically specific to one or a few licenses that have common translations.)

    This fuction requires the legal code locales path to have been added to
    Django settings.LOCALE_PATHS

    WARNING: this *does* make assumptions about the internals of Django's
    translation system that could change on us.  It doesn't seem likely,
    though.
    """

    # Start with a translation object for the domain for this tool.
    tool_translation_object = translation.trans_real.DjangoTranslation(
        language=language_code,
        domain=domain,
        localedirs=settings.LEGAL_CODE_LOCALE_PATH,
    )

    # Add a fallback to the standard Django translation for this language. This
    # gets us the non-legal-code parts of the pages.
    if language_code in settings.LANGUAGES_AVAILABLE_DEEDS_UX:
        tool_translation_object.add_fallback(
            translation.trans_real.translation(language_code)
        )
    elif language_default in settings.LANGUAGES_AVAILABLE_DEEDS_UX:
        tool_translation_object.add_fallback(
            translation.trans_real.translation(language_default)
        )
    else:
        tool_translation_object.add_fallback(
            translation.trans_real.translation(settings.LANGUAGE_CODE)
        )

    return tool_translation_object


@contextmanager
def active_translation(
    translation_object: translation.trans_real.DjangoTranslation,
):
    """
    Context manager to do stuff within its context with a particular
    translation object set as the active translation.  (Use
    ``legal_code.get_translation_object()`` to get a translation object to use
    with this.)

    Bypasses all the language code stuff that Django does when you use its
    ``activate(language_code)`` function.

    The translation object should be a
    django.utils.translation.trans_real.DjangoTranslation object or a subclass.

    WARNING: this *does* make assumptions about the internals of Django's
    translation system that could change on us.  It doesn't seem likely,
    though.
    """

    previous_language = translation.trans_real.get_language()
    translation.trans_real._active.value = translation_object

    yield

    # The following logic is based on django.utils.translations.override()
    if previous_language is not None:
        translation.activate(previous_language)
    else:  # pragma: no cover
        translation.deactivate_all()


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


def parse_date(date_str: str):
    if date_str is None:
        return None
    try:
        date = dateutil.parser.isoparse(date_str)
        return date
    except ValueError:
        return None


def get_pofile_creation_date(pofile_obj: polib.POFile):
    try:
        po_creation_date = pofile_obj.metadata["POT-Creation-Date"]
    except KeyError:
        return None
    return parse_date(po_creation_date)


def get_pofile_revision_date(pofile_obj: polib.POFile):
    try:
        po_revision_date = pofile_obj.metadata["PO-Revision-Date"]
    except KeyError:
        return None
    return parse_date(po_revision_date)


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


def get_default_language_for_jurisdiction_deed_ux(jurisdiction_code):
    default_language = DEFAULT_JURISDICTION_LANGUAGES.get(
        jurisdiction_code, settings.LANGUAGE_CODE
    )
    if default_language in settings.LANGUAGES_AVAILABLE_DEEDS_UX:
        return default_language
    else:
        return settings.LANGUAGE_CODE

def get_default_language_for_jurisdiction_legal_code(jurisdiction_code):
    default_language = DEFAULT_JURISDICTION_LANGUAGES.get(
        jurisdiction_code, settings.LANGUAGE_CODE
    )
    if default_language in settings.LANGUAGES_AVAILABLE_LEGAL_CODE:
        return default_language
    else:
        return settings.LANGUAGE_CODE

def get_legal_code_pofiles():
    legal_code_pofiles = []
    for locale_name in os.listdir(settings.LEGAL_CODE_LOCALE_PATH):
        language_code = translation.to_language(locale_name)
        pofile_path = get_pofile_path(
            locale_or_legalcode="locale",
            language_code=language_code,
            translation_domain="django",
        )
        if not os.path.isfile(pofile_path):  # pragma: no cover
            continue
        legal_code_pofiles.append([language_code, pofile_path])
    legal_code_pofiles.sort(key=lambda x: x[0])
    return legal_code_pofiles

def load_legal_code_translations():
    """
    Process Deed & UX translations (store information on all and track those
    that meet or exceed the TRANSLATION_THRESHOLD).
    """
    legal_code_po_file_info = {}
    languages_available_legal_code = []
    for language_code, pofile_path in get_legal_code_pofiles():
        pofile_obj = polib.pofile(pofile_path)
        percent_translated = pofile_obj.percent_translated()
        legal_code_po_file_info[language_code] = {
            "percent_translated": percent_translated,
            "creation_date": get_pofile_creation_date(pofile_obj),
            "revision_date": get_pofile_revision_date(pofile_obj),
            "metadata": pofile_obj.metadata,
        }
        update_lang_info(language_code)
        if (
            percent_translated < settings.TRANSLATION_THRESHOLD
            and language_code != settings.LANGUAGE_CODE
        ):
            continue
        languages_available_legal_code.append(language_code)
    legal_code_po_file_info = dict(sorted(legal_code_po_file_info.items()))
    # Add global settings
    settings.DEEDS_UX_PO_FILE_INFO = legal_code_po_file_info
    settings.LANGUAGES_AVAILABLE_LEGAL_CODE = sorted(
        list(set(languages_available_legal_code))
    )

def get_jurisdiction_name(category, unit, version, jurisdiction_code):
    # For details on nomenclature for unported licenses, see:
    # https://wiki.creativecommons.org/wiki/License_Versions
    if unit in ["zero", "mark"]:
        jurisdiction_code = "=p10"
    elif category == "licenses" and not jurisdiction_code:
        if version == "4.0":
            jurisdiction_code = "=l40"
        elif version == "3.0":
            jurisdiction_code = "=l30"

    jurisdiction_default = JURISDICTION_NAMES.get("")
    jurisdiction_name = JURISDICTION_NAMES.get(
        jurisdiction_code, jurisdiction_default
    )

    return jurisdiction_name


def get_deeds_ux_pofiles():
    deed_ux_pofiles = []
    for locale_name in os.listdir(settings.DEEDS_UX_LOCALE_PATH):
        language_code = translation.to_language(locale_name)
        pofile_path = get_pofile_path(
            locale_or_legalcode="locale",
            language_code=language_code,
            translation_domain="django",
        )
        if not os.path.isfile(pofile_path):  # pragma: no cover
            continue
        deed_ux_pofiles.append([language_code, pofile_path])
    deed_ux_pofiles.sort(key=lambda x: x[0])
    return deed_ux_pofiles


def load_deeds_ux_translations():
    """
    Process Deed & UX translations (store information on all and track those
    that meet or exceed the TRANSLATION_THRESHOLD).
    """
    deeds_ux_po_file_info = {}
    languages_available_deeds_ux = []
    for language_code, pofile_path in get_deeds_ux_pofiles():
        pofile_obj = polib.pofile(pofile_path)
        percent_translated = pofile_obj.percent_translated()
        deeds_ux_po_file_info[language_code] = {
            "percent_translated": percent_translated,
            "creation_date": get_pofile_creation_date(pofile_obj),
            "revision_date": get_pofile_revision_date(pofile_obj),
            "metadata": pofile_obj.metadata,
        }
        update_lang_info(language_code)
        if (
            percent_translated < settings.TRANSLATION_THRESHOLD
            and language_code != settings.LANGUAGE_CODE
        ):
            continue
        languages_available_deeds_ux.append(language_code)
    deeds_ux_po_file_info = dict(sorted(deeds_ux_po_file_info.items()))
    # Add global settings
    settings.DEEDS_UX_PO_FILE_INFO = deeds_ux_po_file_info
    settings.LANGUAGES_AVAILABLE_DEEDS_UX = sorted(
        list(set(languages_available_deeds_ux))
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
        if not lang_info.get("name"):
            lang_info["name"] = locale.get_display_name("en")
        if not lang_info.get("name_local"):
            lang_info["name_local"] = locale.get_display_name(locale_name)
        if not lang_info.get("bidi"):
            lang_info["bidi"] = order_to_bidi[locale.character_order]
    except UnknownLocaleError:
        pass


def write_transstats_csv(output_file):
    csv_headers = [
        "lang_django",
        "lang_locale",
        "lang_transifex",
        "num_messages",
        "num_trans",
        "num_fuzzy",
        "percent_trans",
    ]

    with open(output_file, "w") as output_file:
        # Create CSV writer
        writer = csv.DictWriter(output_file, csv_headers, dialect="unix")
        writer.writeheader()

        # Load PO Files and write a row for each
        for language_code, pofile_path in get_deeds_ux_pofiles():
            locale_name = translation.to_locale(language_code)
            transifex_code = map_django_to_transifex_language_code(
                language_code
            )

            pofile_obj = polib.pofile(pofile_path)
            translated = len(pofile_obj.translated_entries())
            fuzzy = len(pofile_obj.fuzzy_entries())
            percent_translated = pofile_obj.percent_translated()

            writer.writerow(
                {
                    "lang_django": language_code,
                    "lang_locale": locale_name,
                    "lang_transifex": transifex_code,
                    "num_messages": len(pofile_obj),
                    "num_trans": translated,
                    "num_fuzzy": fuzzy,
                    "percent_trans": percent_translated,
                }
            )
