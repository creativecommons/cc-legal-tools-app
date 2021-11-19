"""
WSGI config for cc_legal_tools project.

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
        "DJANGO_SETTINGS_MODULE", "cc_legal_tools.settings.deploy"
    )
else:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "cc_legal_tools.settings")

application = get_wsgi_application()

try:
    # Third-party
    from whitenoise.django import DjangoWhiteNoise
except ImportError:
    pass
else:
    application = DjangoWhiteNoise(application)
