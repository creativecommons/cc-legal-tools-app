# Third-party
import dj_database_url

# First-party/Local
from cc_licenses.settings.dev import *  # noqa: F401, F403

# Override settings here
# TRANSLATION_REPOSITORY_DEPLOY_KEY = "/path/to/ssh/private/key"

# DATABASE_URL environment variable must be set
DATABASES["default"] = dj_database_url.config(conn_max_age=600)  # noqa: F405
