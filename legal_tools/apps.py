# Third-party
from django.apps import AppConfig
from django.conf import settings

# First-party/Local
from i18n.utils import load_deeds_ux_translations, update_lang_info
from legal_tools.git_utils import setup_to_call_git


class LicensesConfig(AppConfig):
    # required: must be the Full dotted path to the app
    name = settings.APP_NAME
    # optional: app label, must be unique in Django project
    label = settings.APP_LABEL
    # optional: verbose name
    verbose_name = settings.APP_VERBOSE_NAME

    def ready(self):
        setup_to_call_git()

        # Normalize all currently loaded language information using Babel
        for language_code in settings.LANG_INFO.keys():
            update_lang_info(language_code)

        # Process Deed & UX translations (store information on all and track
        # those that meet or exceed the TRANSLATION_THRESHOLD).
        load_deeds_ux_translations()
