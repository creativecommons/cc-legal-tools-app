# Standard library
import logging
import os

# Third-party
from django.conf import settings

logger = logging.getLogger(__name__)

CSV_HEADERS = [
    "lang",
    "num_messages",
    "num_trans",
    "num_fuzzy",
    "percent_trans",
]
DEFAULT_INPUT_DIR = settings.LOCALE_PATHS[0]
DEFAULT_CSV_FILE = os.path.abspath(
    os.path.realpath(os.path.join(DEFAULT_INPUT_DIR, "transstats.csv"))
)
# If something has no language listed, that generally means it's English.
# We want to set an actual language code on it so that once this data has
# been imported, we don't have to treat English as a special default.
DEFAULT_LANGUAGE_CODE = "en"

# The DEFAULT_JURISDICTION_LANGUAGES and JURISDICTION_NAMES are largely based
# on jurisdictions.rdf in the cc.licenserdf repo.
# The language codes here are CC language codes, which sometimes differ from
# Django language codes.
DEFAULT_JURISDICTION_LANGUAGES = {
    # Map jurisdiction code to language code.
    # "jurisdiction code": "Django language code"
    #
    # IMPORTANT: language codes and jurisdictions are different:
    # - jurisdictions are ISO 3166-1 alpha-2 codes
    # - Django language codes are lowercase Django RFC5646 language tags:
    #   https://github.com/django/django/blob/main/django/conf/global_settings.py
    #
    # For example:
    # - "ar" is the ISO 3166-1 alpha-2 code for Argentina
    # - "ar" is the RFC5646 language tag for Arabic
    #
    # See the "JURISDICTION_NAMES", just below this.
    "am": "hy",  # Armenian - not in jurisdictions.rdf
    "ar": "es",
    "at": "de",
    # jurisdictions.rdf says au is "en-gb", but:
    # Deed: https://creativecommons.org/licenses/by/3.0/au/
    # Deed: https://creativecommons.org/licenses/by/3.0/au/deed.en
    # https://creativecommons.org/licenses/by/3.0/au/deed.en-gb
    #   -> REDIRECTS to https://creativecommons.org/licenses/by/3.0/au/deed.en
    # Valid: https://creativecommons.org/licenses/by/3.0/au/legalcode
    # NOT: https://creativecommons.org/licenses/by/3.0/au/legalcode.en
    # NOT: https://creativecommons.org/licenses/by/3.0/au/legalcode.en-gb
    "au": "en",
    "az": "az",
    "be": "fr",
    "bg": "bg",
    "br": "pt-br",
    # For "ca", jurisdictions.rdf says "en-gb" but the filename is _en.html.
    # and the URL is
    # https://creativecommons.org/licenses/by/3.0/ca/legalcode.en
    # NOT https://creativecommons.org/licenses/by/3.0/ca
    # NOT https://creativecommons.org/licenses/by/3.0/ca/
    # NOT https://creativecommons.org/licenses/by/3.0/ca/legalcode.en-gb
    "ca": "en",
    # NOT https://creativecommons.org/licenses/by/3.0/ch/legalcode
    # YES https://creativecommons.org/licenses/by/3.0/ch/legalcode.de
    "ch": "de",  # ch=Switzerland, default in jurisdictions.rdf=de
    "cl": "es",
    "cn": "zh-hans",  # "cn" is China Mainland, language is simplified Chinese
    "co": "es",
    "cr": "es",
    "cz": "cs",
    "de": "de",
    "dk": "da",
    "ec": "es",
    "ee": "et",
    "eg": "ar",
    # For "es", jurisdictions.rdf says "es-es".
    # Deed https://creativecommons.org/licenses/by/3.0/es/ is valid
    # NOT https://creativecommons.org/licenses/by/3.0/es/legalcode
    # License https://creativecommons.org/licenses/by/3.0/es/legalcode.es is
    # valid
    # NOT https://creativecommons.org/licenses/by/3.0/es/legalcode.es-es
    # BUT the filename is by-nc-nd_3.0_es_es ????
    "es": "es",
    "fi": "fi",
    "fr": "fr",
    "ge": "ka",  # Georgia not in jurisdictions.rdf. Georgian?
    "gr": "el",
    "gt": "es",
    # Deed: https://creativecommons.org/licenses/by/3.0/hk/
    # License: https://creativecommons.org/licenses/by/3.0/hk/legalcode
    "hk": "en-gb",
    "hr": "hr",
    "hu": "hu",
    "ie": "en-gb",
    "igo": "en",
    "il": "he",
    "in": "en-gb",
    "it": "it",
    "jo": "ja",
    "jp": "ja",
    "kr": "ko",
    "lu": "fr",
    "mk": "mk",
    "mt": "en",
    "mx": "es",
    "my": "ms",
    "ng": "nl",
    "nl": "nl",
    "no": "no",
    "nz": "en",
    "pe": "es",
    "ph": "en",
    "pl": "pl",
    "pr": "es",
    "pt": "pt",
    "ro": "ro",
    "rs": "sr",
    "scotland": "en-gb",
    "se": "sv",
    "sg": "en-gb",
    "si": "sl",
    "th": "th",
    "tw": "zh-hant",
    "ua": "zh-hant",
    "ug": "en",
    "uk": "en-gb",
    "us": "en",
    "ve": "es",
    "vn": "vi",
    "za": "en-gb",
}
JURISDICTION_NAMES = {
    "": "Unported",
    "am": "Armenia",
    "ar": "Argentina",
    "at": "Austria",
    "au": "Australia",
    "az": "Azerbaijan",
    "be": "Belgium",
    "bg": "Bulgaria",
    "br": "Brazil",
    "ca": "Canada",
    "ch": "Switzerland",
    "cl": "Chile",
    "cn": "China Mainland",
    "co": "Colombia",
    "cr": "Costa Rica",
    "cz": "Czech Republic",
    "de": "Germany",
    "dk": "Denmark",
    "ec": "Ecuador",
    "ee": "Estonia",
    "eg": "Egypt",
    "es": "Spain",
    "fi": "Finland",
    "fr": "France",
    "ge": "Georgia",
    "gr": "Greece",
    "gt": "Guatemala",
    "hk": "Hong Kong",
    "hr": "Croatia",
    "hu": "Hungary",
    "ie": "Ireland",
    "igo": "IGO",
    "il": "Israel",
    "in": "India",
    "it": "Italy",
    "jo": "Jordan",
    "jp": "Japan",
    "kr": "Korea",
    "lu": "Luxembourg",
    "mk": "Macedonia",
    "mt": "Malta",
    "mx": "Mexico",
    "my": "Malaysia",
    "ng": "Nigeria",
    "nl": "Netherlands",
    "no": "Norway",
    "nz": "New Zealand",
    "pe": "Peru",
    "ph": "Philippines",
    "pl": "Poland",
    "pr": "Puerto Rico",
    "pt": "Portugal",
    "ro": "Romania",
    "rs": "Serbia",
    "scotland": "UK: Scotland",
    "se": "Sweden",
    "sg": "Singapore",
    "si": "Slovenia",
    "th": "Thailand",
    "tw": "Taiwan",
    "ua": "Ukraine",
    "ug": "Uganda",
    "uk": "UK: England & Wales",
    "us": "United States",
    "ve": "Venezuela",
    "vn": "Vietnam",
    "za": "South Africa",
}
LANGUAGE_CODE_REGEX_STRING = r"[a-zA-Z_-]*"
LANGMAP_DJANGO_TO_TRANSIFEX = {
    # Django language code: Transifex language code
    #
    # Django language codes are lowercase Django RFC5646 language tags:
    # https://github.com/django/django/blob/main/django/conf/global_settings.py
    #
    # Transifex language codes are ISO 639 language codes optionally followed
    # by a ISO 3166 country code or ISO 15924 script code
    # https://www.transifex.com/explore/languages/
    "en-gb": "en_GB",
    "pt-br": "pt_BR",
    "zh-hans": "zh-Hans",
    "zh-hant": "zh-Hant",
}
LANGMAP_LEGACY_TO_DJANGO = {
    # Legacy language code: Django language code
    #
    # Django language codes are lowercase Django RFC5646 language tags:
    # https://github.com/django/django/blob/main/django/conf/global_settings.py
    "es-es": "es",
    "sr-cyrl": "sr",
    "zh": "zh-hans",
    "zh-cn": "zh-hans",
    "zh-tw": "zh-hant",
}
FILENAME_LANGUAGE_CODES = {
    # CC language code: language code for path to translation files
    # (Don't ask me why... this just seems to be how it is.)
    "en-GB": "en",
    "zh-Hans": "zh_Hans",
    "zh-Hant": "zh_Hant",
}
