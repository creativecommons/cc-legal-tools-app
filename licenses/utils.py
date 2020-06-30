import os

from django.conf import settings


def get_locale_dir(locale_name):
    localedir = settings.LOCALE_PATHS[0]
    return os.path.join(localedir, locale_name, "LC_MESSAGES")


def locales_with_directories():
    """
    Return list of locale names under our locale dir.
    """
    dir = settings.LOCALE_PATHS[0]
    return [
        item
        for item in os.listdir(dir)
        if os.path.isdir(os.path.join(dir, item))
    ]
