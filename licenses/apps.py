# Standard library
import os

# Third-party
import polib
from django.apps import AppConfig
from django.conf import settings

# First-party/Local
from licenses.git_utils import setup_to_call_git


class LicensesConfig(AppConfig):
    # required: must be the Full dotted path to the app
    name = settings.APP_NAME
    # optional: app label, must be unique in Django project
    label = settings.APP_LABEL
    # optional: verbose name
    verbose_name = settings.APP_VERBOSE_NAME

    LANGUAGES_TRANSLATED = []
    locale_dir = os.path.join(settings.DATA_REPOSITORY_DIR, "locale")
    locale_dir = os.path.abspath(os.path.realpath(locale_dir))
    for language_code in os.listdir(locale_dir):
        po_file = os.path.join(
            locale_dir,
            language_code,
            "LC_MESSAGES",
            "django.po",
        )
        if not os.path.isfile(po_file):
            continue
        po = polib.pofile(po_file)
        if po.percent_translated() < 80:
            continue
        LANGUAGES_TRANSLATED.append(language_code)
    settings.LANGUAGES_TRANSLATED = sorted(list(set(LANGUAGES_TRANSLATED)))

    def ready(self):
        setup_to_call_git()
