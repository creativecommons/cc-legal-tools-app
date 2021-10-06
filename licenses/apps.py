# Third-party
from django.apps import AppConfig
from django.conf import settings

# First-party/Local
from i18n.utils import load_deeds_ux_translations
from licenses.git_utils import setup_to_call_git


class LicensesConfig(AppConfig):
    # required: must be the Full dotted path to the app
    name = settings.APP_NAME
    # optional: app label, must be unique in Django project
    label = settings.APP_LABEL
    # optional: verbose name
    verbose_name = settings.APP_VERBOSE_NAME

    def ready(self):
        setup_to_call_git()
        load_deeds_ux_translations()
