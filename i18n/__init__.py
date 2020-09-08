import os
import re

from django.conf import settings


CSV_HEADERS = ["lang", "num_messages", "num_trans", "num_fuzzy", "percent_trans"]
DEFAULT_INPUT_DIR = settings.LOCALE_PATHS[0]
DEFAULT_CSV_FILE = os.path.join(DEFAULT_INPUT_DIR, "transstats.csv")
# If something has no language listed, that generally means it's English.
# We want to set an actual language code on it so that once this data has
# been imported, we don't have to treat English as a special default.
DEFAULT_LANGUAGE_CODE = "en"
# These are based on what files are in creativecommons.org:docroot/legalcode
DEFAULT_JURISDICTION_LANGUAGES = {
    "am": ["am"],
    "ar": ["ar"],
    "az": ["az"],
    "be": ["fr", "nl"],
    "bg": ["bg"],
    "br": ["br"],
    "ca": ["en", "fr"],
    "ch": ["de", "fr"],
    "cs": ["cs"],
    "de": ["de"],
    "ee": ["ee"],
    "el": ["el"],
    "en": ["en"],
    "es": ["es", "ast", "ca", "es", "eu", "gl"],
    "eu": ["eu"],
    "fi": ["fi"],
    "fr": ["fr"],
    "hr": ["hr"],
    "hu": ["hu"],
    "id": ["id"],
    "igo": ["ar", "fr"],
    "in": ["in"],
    "it": ["it"],
    "ja": ["ja"],
    "ko": ["ko"],
    "lt": ["lt"],
    "lu": ["lu"],
    "lv": ["lv"],
    "mi": ["mi"],
    "mk": ["mk"],
    "mt": ["mt"],
    "my": ["my"],
    "nl": ["nl"],
    "no": ["no"],
    "pl": ["pl"],
    "pt": ["pt"],
    "ro": ["ro"],
    "ru": ["ru"],
    "se": ["se"],
    "sg": ["sg"],
    "si": ["si"],
    "sl": ["sl"],
    "sv": ["sv"],
    "th": ["th"],
    "tr": ["tr"],
    "tw": ["tw"],
    "ug": ["ug"],
    "uk": ["uk"],
}

LANGUAGE_CODE_REGEX_STRING = r"[a-zA-Z_-]*"
LANGUAGE_CODE_REGEX = re.compile(LANGUAGE_CODE_REGEX_STRING)
