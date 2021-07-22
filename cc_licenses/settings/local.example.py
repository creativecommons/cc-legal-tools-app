# Standard library
import os

# Third-party
import dj_database_url

# First-party/Local
from cc_licenses.settings.dev import *  # noqa: F401, F403

# Override settings here
# TRANSIFEX["API_TOKEN"] = "TRANSIFEX_API_TOKEN"  # noqa: F405
# TRANSLATION_REPOSITORY_DEPLOY_KEY = os.path.join(
#     os.path.expanduser("~"), ".ssh", "PRIVATE_KEY_NAME",
# )

# If DEV_DATABASE_URL environment variable is not set, then localhost is
# assumed.  Also see DATABASES variable in settings base.by.
if os.getenv("DEV_DATABASE_URL"):
    DATABASES["default"] = dj_database_url.config(  # noqa: F405
        env="DEV_DATABASE_URL",
        conn_max_age=600,
    )
