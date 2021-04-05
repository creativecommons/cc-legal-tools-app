# Standard library
import re

default_app_config = "licenses.apps.LicensesConfig"

FREEDOM_LEVEL_MAX = 1
FREEDOM_LEVEL_MID = 2
FREEDOM_LEVEL_MIN = 3

FREEDOM_COLORS = {
    FREEDOM_LEVEL_MIN: "red",
    FREEDOM_LEVEL_MID: "yellow",
    FREEDOM_LEVEL_MAX: "green",
}
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

# These mostly APPEAR to have the format X.Y, where X and Y are digits.
# To be forgiving, we accept any mix of digits and ".".
# There's also at least one with an empty version (MIT).
VERSION_REGEX_STRING = r"[0-9.]+|"
VERSION_REGEX = re.compile(VERSION_REGEX_STRING)
