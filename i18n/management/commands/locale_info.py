# Standard library
import logging
from argparse import ArgumentParser

# Third-party
from babel import Locale
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


class Command(BaseCommand):
    def add_arguments(self, parser: ArgumentParser):
        parser.add_argument("language_tag", metavar="LANGUAGE_TAG")

    def main(self, **options):
        LOG.setLevel(LOG_LEVELS[int(options["verbosity"])])
        language_tag = options["language_tag"]

        locale_name = translation.to_locale(language_tag)
        lang_info = settings.LANG_INFO[language_tag]
        print()
        # Django
        print(
            f"      LANGUAGE_TAG: {language_tag}",
            "",
            "Django (including settings)",
            f"      locale: {locale_name}",
            f"        name: {lang_info['name']}",
            f"  name_local: {lang_info['name_local']}",
            f"        bidi: {lang_info['bidi']}",
            sep="\n",
        )
        # Babel
        locale = Locale.parse(locale_name)
        name = locale.get_display_name("en")
        name_local = locale.get_display_name(locale_name)
        character_order = ORDER_TO_BIDI[locale.character_order]
        print(
            "\nBabel / CLDR",
            f"      locale: {locale}",
            f"        name: {name}",
            f"  name_local: {name_local}",
            f"        bidi: {character_order}",
            sep="\n",
        )
        print()

    def handle(self, **options):
        self.main(**options)
