# Standard library
import logging
from argparse import ArgumentParser

# Third-party
from babel import Locale
from babel.core import UnknownLocaleError
from django.conf import settings
from django.core.management import BaseCommand
from django.utils import translation

LOG = logging.getLogger(__name__)
LOG_LEVELS = {
    0: logging.ERROR,
    1: logging.WARNING,
    2: logging.INFO,
    3: logging.DEBUG,
}
ORDER_TO_BIDI = {
    "left-to-right": False,
    "right-to-left": True,
}
EMPTY = {
    "name": "none",
    "name_local": "none",
    "bidi": "none",
}


class Command(BaseCommand):
    def add_arguments(self, parser: ArgumentParser):
        parser.add_argument("language_tag", metavar="LANGUAGE_TAG")

    def main(self, **options):
        LOG.setLevel(LOG_LEVELS[int(options["verbosity"])])
        language_tag = options["language_tag"]

        # Django
        if language_tag in settings.DJANGO_LANG_INFO:
            lang_info = settings.DJANGO_LANG_INFO[language_tag]
        else:
            lang_info = EMPTY
        django_locale = translation.to_locale(language_tag)
        django_name = lang_info["name"]
        django_name_local = lang_info["name_local"]
        django_bidi = lang_info["bidi"]
        # Babel
        try:
            babel_locale = Locale.parse(django_locale)
            babel_name = babel_locale.get_display_name("en")
            babel_name_local = babel_locale.get_display_name()
            babel_bidi = ORDER_TO_BIDI[babel_locale.character_order]
        except UnknownLocaleError:
            lang_info = EMPTY
            babel_locale = django_locale
            babel_name = lang_info["name"]
            babel_name_local = lang_info["name_local"]
            babel_bidi = lang_info["bidi"]
        # cc-legal-tools-app
        if language_tag in settings.LANG_INFO:
            lang_info = settings.LANG_INFO[language_tag]
        else:
            lang_info = EMPTY
        app_locale = django_locale
        app_name = lang_info["name"]
        app_name_local = lang_info["name_local"]
        app_bidi = lang_info["bidi"]

        self.stdout.write()
        self.stdout.write(f"LANGUAGE_TAG: {language_tag}\n\n")

        # Django
        self.stdout.write(
            f"Django\n"
            f"      locale: {django_locale}\n"
            f"        name: {django_name}\n"
            f"  name_local: {django_name_local}\n"
            f"        bidi: {django_bidi}\n"
        )
        # Babel
        self.stdout.write(
            "\nBabel / CLDR\n"
            f"      locale: {babel_locale}\n"
            f"        name: {babel_name}\n"
            f"  name_local: {babel_name_local}\n"
            f"        bidi: {babel_bidi}\n\n"
        )
        # cc-legal-tools-app
        self.stdout.write(
            "cc-legal-tools-app\n"
            f"      locale: {app_locale}\n"
            f"        name: {app_name}\n"
            f"  name_local: {app_name_local}\n"
            f"        bidi: {app_bidi}\n"
        )
        self.stdout.write()

    def handle(self, **options):
        self.main(**options)
