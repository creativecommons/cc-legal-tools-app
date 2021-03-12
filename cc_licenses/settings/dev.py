# Standard library
import os
import sys

# First-party/Local
from cc_licenses.settings.base import *  # noqa: F403

DEBUG = True

INSTALLED_APPS += [  # noqa: F405
    "debug_toolbar",
]
MIDDLEWARE += (  # noqa: F405
    "debug_toolbar.middleware.DebugToolbarMiddleware",
)

INTERNAL_IPS = ("127.0.0.1",)

#: Don't send emails, just print them on stdout
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

#: Run celery tasks synchronously
CELERY_ALWAYS_EAGER = True

#: Tell us when a synchronous celery task fails
CELERY_EAGER_PROPAGATES_EXCEPTIONS = True

SECRET_KEY = os.environ.get(
    "SECRET_KEY", "_+sc$rvjx-ycj9rkgo4ls81!@clmdjrr=39-#ed7k6cqrq$19f"
)

# Special test settings
if "test" in sys.argv:
    PASSWORD_HASHERS = (
        "django.contrib.auth.hashers.SHA1PasswordHasher",
        "django.contrib.auth.hashers.MD5PasswordHasher",
    )

    LOGGING["root"]["handlers"] = []  # noqa: F405

# Make it obvious if there are unresolved variables in templates
new_value = "INVALID_VARIABLE(%s)"
TEMPLATES[0]["OPTIONS"]["string_if_invalid"] = new_value  # noqa: F405
