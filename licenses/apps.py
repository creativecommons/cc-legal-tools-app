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

    # Determine languages that have met or exceed display threshold
    LANGUAGES_WITH_PO_FILE = []
    LANGUAGES_MOSTLY_TRANSLATED = []
    locale_dir = os.path.join(settings.DATA_REPOSITORY_DIR, "locale")
    locale_dir = os.path.abspath(os.path.realpath(locale_dir))
    for language_code in os.listdir(locale_dir):
        pofile_path = os.path.join(
            locale_dir,
            language_code,
            "LC_MESSAGES",
            f"{settings.DEEDS_UX_RESOURCE_SLUG}.po",
        )
        if not os.path.isfile(pofile_path):
            continue
        pofile_obj = polib.pofile(pofile_path)
        LANGUAGES_WITH_PO_FILE.append(language_code)
        if pofile_obj.percent_translated() < 80:
            continue
        LANGUAGES_MOSTLY_TRANSLATED.append(language_code)
    settings.LANGUAGES_WITH_PO_FILE = sorted(list(set(LANGUAGES_WITH_PO_FILE)))
    settings.LANGUAGES_MOSTLY_TRANSLATED = sorted(
        list(set(LANGUAGES_MOSTLY_TRANSLATED))
    )

    def ready(self):
        setup_to_call_git()
