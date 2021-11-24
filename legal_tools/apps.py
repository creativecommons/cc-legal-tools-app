# Third-party
from django.apps import AppConfig
from django.conf import settings

# First-party/Local
from i18n.utils import load_deeds_ux_translations, update_lang_info
from legal_tools.git_utils import setup_to_call_git


class LegalToolsConfig(AppConfig):
    # required: must be the full dotted path to the app
    name = "legal_tools"
    # optional: app label, must be unique in Django project
    label = name
    # optional: verbose name
    verbose_name = name.replace("_", " ").title()

    def ready(self):
        setup_to_call_git()

        # Normalize all currently loaded language information using Babel
        for language_code in settings.LANG_INFO.keys():
            update_lang_info(language_code)

        # Process Deed & UX translations (store information on all and track
        # those that meet or exceed the TRANSLATION_THRESHOLD).
        load_deeds_ux_translations()
