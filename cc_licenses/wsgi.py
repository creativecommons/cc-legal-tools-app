"""
WSGI config for cc_licenses project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/1.11/howto/deployment/wsgi/
"""

# Standard library
import os

# Third-party
from django.core.wsgi import get_wsgi_application

if "DATABASE_URL" in os.environ:
    # Dokku or similar
    os.environ.setdefault(
        "DJANGO_SETTINGS_MODULE", "cc_licenses.settings.deploy"
    )
else:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "cc_licenses.settings")

application = get_wsgi_application()

try:
    # Third-party
    from whitenoise.django import DjangoWhiteNoise
except ImportError:
    pass
else:
    application = DjangoWhiteNoise(application)
