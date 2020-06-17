"""
WSGI config for cc_licenses project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/1.11/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application

from . import load_env

load_env.load_env()
if 'DATABASE_URL' in os.environ:
    # Dokku or similar
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "cc_licenses.settings.deploy")
else:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "cc_licenses.settings")

application = get_wsgi_application()

try:
    from whitenoise.django import DjangoWhiteNoise
except ImportError:
    pass
else:
    application = DjangoWhiteNoise(application)
