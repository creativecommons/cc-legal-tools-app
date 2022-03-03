# Standard library
# import os

# First-party/Local
from cc_legal_tools.settings.dev import *  # noqa: F401, F403

DEBUG = True

# Override settings here

# TRANSIFEX["API_TOKEN"] = "TRANSIFEX_API_TOKEN"  # noqa: F405
# TRANSLATION_REPOSITORY_DEPLOY_KEY = os.path.join(
#     os.path.expanduser("~"), ".ssh", "PRIVATE_KEY_NAME",
# )

# Enable tools like Firefox Web Developer: View Responsive Layouts
MIDDLEWARE.remove(  # noqa: F405
    "django.middleware.clickjacking.XFrameOptionsMiddleware"
)
