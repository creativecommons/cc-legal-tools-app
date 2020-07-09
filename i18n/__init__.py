import os

from django.conf import settings


CSV_HEADERS = ["lang", "num_messages", "num_trans", "num_fuzzy", "percent_trans"]
DEFAULT_INPUT_DIR = settings.LOCALE_PATHS[0]
DEFAULT_CSV_FILE = os.path.join(DEFAULT_INPUT_DIR, "transstats.csv")
