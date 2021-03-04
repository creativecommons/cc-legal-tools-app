"""
Statistics on the translations of this file.

The CSV written will be in the format of:
  lang,num_messages,num_trans,num_fuzzy,percent_trans
"""

# Standard library
import csv
import os

# Third-party
import polib
from django.core.management import BaseCommand

# First-party/Local
from i18n import CSV_HEADERS, DEFAULT_CSV_FILE, DEFAULT_INPUT_DIR


def gen_statistics(input_dir, output_file):
    """
    Generate statistics on languages for how translated they are.

    Keyword arguments:
    - input_dir: The directory of languages we'll iterate through
    - output_file: Path to the CSV file that will be written to
    """
    output_file = open(output_file, "w")

    input_dir = os.path.abspath(input_dir)
    lang_dirs = os.listdir(input_dir)

    # Create CSV writer
    writer = csv.DictWriter(output_file, CSV_HEADERS)

    # iterate through all the languages
    for locale_identifier in sorted(lang_dirs):
        trans_dir = os.path.join(input_dir, locale_identifier, "LC_MESSAGES")
        if os.path.isdir(trans_dir):
            trans_file = os.path.join(trans_dir, "django.po")

            print(trans_file)

            # load .po file
            pofile = polib.pofile(trans_file)

            fuzzies = 0
            translated = 0

            for entry in pofile:
                if entry.msgstr:
                    if entry.fuzzy:
                        fuzzies += 1
                    else:
                        translated += 1

            writer.writerow(
                {
                    "lang": locale_identifier,
                    "num_messages": len(pofile),
                    "num_trans": translated,
                    "num_fuzzy": fuzzies,
                    "percent_trans": int(
                        (float(translated) / len(pofile)) * 100
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
        if os.path.exists(output_file):
            os.remove(output_file)
        gen_statistics(input_dir, output_file)
