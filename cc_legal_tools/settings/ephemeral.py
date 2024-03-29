# Use **ONLY** for ephemeral deployments (ex. GitHub Actions).

# Third-party
from django.core.management.utils import get_random_secret_key

# First-party/Local
from cc_legal_tools.settings.base import *  # noqa: F403

ALLOWED_HOSTS = ["127.0.0.1", "localhost"]

#: Don't send emails, just print them on stdout
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

#: Run celery tasks synchronously
CELERY_ALWAYS_EAGER = True

#: Tell us when a synchronous celery task fails
CELERY_EAGER_PROPAGATES_EXCEPTIONS = True

DEBUG = True

INTERNAL_IPS = ("127.0.0.1",)

SECRET_KEY = get_random_secret_key()

# Make it obvious if there are unresolved variables in templates
new_value = "INVALID_VARIABLE(%s)"
TEMPLATES[0]["OPTIONS"]["string_if_invalid"] = new_value  # noqa: F405
