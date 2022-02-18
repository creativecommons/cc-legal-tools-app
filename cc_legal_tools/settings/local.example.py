# Standard library
# import os

# First-party/Local
from cc_legal_tools.settings.dev import *  # noqa: F401, F403

DEBUG = True

# Override settings here
ALLOWED_HOSTS = ["*"]
# TRANSIFEX["API_TOKEN"] = "TRANSIFEX_API_TOKEN"  # noqa: F405
# TRANSLATION_REPOSITORY_DEPLOY_KEY = os.path.join(
#     os.path.expanduser("~"), ".ssh", "PRIVATE_KEY_NAME",
# )
