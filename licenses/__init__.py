FREEDOM_LEVEL_MAX = 1
FREEDOM_LEVEL_MID = 2
FREEDOM_LEVEL_MIN = 3

FREEDOM_COLORS = {
    FREEDOM_LEVEL_MIN: "red",
    FREEDOM_LEVEL_MID: "yellow",
    FREEDOM_LEVEL_MAX: "green",
}
# If something has no language listed, that generally means it's English.
# We want to set an actual language code on it so that once this data has
# been imported, we don't have to treat English as a special default.
DEFAULT_LANGUAGE_CODE = "en"
MISSING_LICENSES = [
    "http://creativecommons.org/licenses/by-nc/2.1/",
    "http://creativecommons.org/licenses/by-nd/2.1/",
    "http://creativecommons.org/licenses/by-nc-nd/2.1/",
    "http://creativecommons.org/licenses/by-sa/2.1/",
    "http://creativecommons.org/licenses/by-nc-sa/2.1/",
    "http://creativecommons.org/licenses/nc/2.0/",
    "http://creativecommons.org/licenses/nc-sa/2.0/",
    "http://creativecommons.org/licenses/by/2.1/",
    "http://creativecommons.org/licenses/nd-nc/2.0/",
    "http://creativecommons.org/licenses/by-nd-nc/2.0/",
    "http://creativecommons.org/licenses/nd/2.0/",
    "http://creativecommons.org/licenses/sa/2.0/",
]

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
