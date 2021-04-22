# Standard library
import os

# Third-party
import dj_database_url

# First-party/Local
from cc_licenses.settings.dev import *  # noqa: F401, F403

# Override settings here
# TRANSLATION_REPOSITORY_DEPLOY_KEY = "/path/to/ssh/private/key"

# If DATABASE_URL environment variable is not set, then localhost is assumed.
# Also see DATABASES variable in settings base.by.
if os.getenv("DEV_DATABASE_URL"):
    DATABASES["default"] = dj_database_url.config(  # noqa: F405
        env="DEV_DATABASE_URL",
        conn_max_age=600,
    )
