# Third-party
from django.apps import AppConfig

# First-party/Local
from licenses.git_utils import setup_to_call_git


class LicensesConfig(AppConfig):
    name = "licenses"  # required: must be the Full dotted path to the app
    label = "licenses"  # optional: app label, must be unique in Django project
    verbose_name = "Licenses"  # optional

    def ready(self):
        setup_to_call_git()
