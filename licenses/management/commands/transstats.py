"""
Statistics on the translations of this file.

The CSV written will be in the format of:
  lang,num_messages,num_trans,num_fuzzy,percent_trans
"""

# Standard library
import csv
import logging
import os

# Third-party
import polib
from django.conf import settings
from django.core.management import BaseCommand

# First-party/Local
from i18n import CSV_HEADERS, DEFAULT_CSV_FILE, DEFAULT_INPUT_DIR
from i18n.utils import map_django_to_transifex_language_code

LOG = logging.getLogger(__name__)
LOG_LEVELS = {
    0: logging.ERROR,
    1: logging.WARNING,
    2: logging.INFO,
    3: logging.DEBUG,
}


def gen_statistics(input_dir, output_file):
    """
    Generate statistics on languages for how translated they are.

    Keyword arguments:
    - input_dir: The directory of languages we'll iterate through
    - output_file: Path to the CSV file that will be written to
    """
    output_file = open(output_file, "w")

    input_dir = os.path.abspath(os.path.realpath(input_dir))
    lang_dirs = os.listdir(input_dir)

    # Create CSV writer
    writer = csv.DictWriter(output_file, CSV_HEADERS, dialect="unix")
    writer.writeheader()

    # iterate through all the languages
    for language_code in sorted(lang_dirs):
        transifex_code = map_django_to_transifex_language_code(language_code)
        trans_dir = os.path.join(input_dir, language_code, "LC_MESSAGES")
        if os.path.isdir(trans_dir):
            trans_file = os.path.join(
                trans_dir,
                f"{settings.DEEDS_UX_RESOURCE_SLUG}.po",
            )

            LOG.info(f"Reading {trans_file}")

            # load .po file
            pofile_obj = polib.pofile(trans_file)

            fuzzies = 0
            translated = 0

            for entry in pofile_obj:
                if entry.msgstr:
                    if entry.fuzzy:
                        fuzzies += 1
                    else:
                        translated += 1

            writer.writerow(
                {
                    "lang_ietf": language_code,
                    "lang_locale": transifex_code,
                    "num_messages": len(pofile_obj),
                    "num_trans": translated,
                    "num_fuzzy": fuzzies,
                    "percent_trans": int(
                        (float(translated) / len(pofile_obj)) * 100
                    ),
                }
            )

    output_file.close()


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument(
            "-i",
            "--input_dir",
            dest="input_dir",
            help="Directory to search for .po files to generate statistics"
            " on.",
            default=DEFAULT_INPUT_DIR,
        )
        parser.add_argument(
            "-o",
            "--output_file",
            dest="output_file",
            help="CSV file we'll write our statistics to.",
            default=DEFAULT_CSV_FILE,
        )

    def handle(self, *args, input_dir, output_file, **options):
        LOG.setLevel(LOG_LEVELS[int(options["verbosity"])])
        if os.path.exists(output_file):
            os.remove(output_file)
        gen_statistics(input_dir, output_file)
