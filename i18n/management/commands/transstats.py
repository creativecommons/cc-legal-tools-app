"""
Generate translations statistics CSV file.
"""

# Standard library
import logging
import os

# Third-party
from django.core.management import BaseCommand

# First-party/Local
from i18n import DEFAULT_CSV_FILE
from i18n.utils import write_transstats_csv

LOG = logging.getLogger(__name__)
LOG_LEVELS = {
    0: logging.ERROR,
    1: logging.WARNING,
    2: logging.INFO,
    3: logging.DEBUG,
}


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument(
            "-o",
            "--output_file",
            dest="output_file",
            help="CSV file we'll write our statistics to (default:"
            f" {DEFAULT_CSV_FILE})",
            default=DEFAULT_CSV_FILE,
        )

    def handle(self, *args, **options):
        LOG.setLevel(LOG_LEVELS[int(options["verbosity"])])
        output_file = options["output_file"]
        if os.path.exists(output_file):
            os.remove(output_file)
        write_transstats_csv(output_file)
