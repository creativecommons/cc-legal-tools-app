# Standard library
import logging
from argparse import ArgumentParser

# Third-party
from django.core.management import BaseCommand

# First-party/Local
from legal_tools.utils import init_utils_logger, update_title

LOG = logging.getLogger(__name__)
LOG_LEVELS = {
    0: logging.ERROR,
    1: logging.WARNING,
    2: logging.INFO,
    3: logging.DEBUG,
}


class Command(BaseCommand):
    """
    Update the title property of all legal tools by normalizing legalcy titles
    and normalizing translated titles for current legal tools (Licenses 4.0 and
    CC0 1.0).
    """

    def add_arguments(self, parser: ArgumentParser):
        # Python defaults to lowercase starting character for the first
        # character of help text, but Djano appears to use uppercase and so
        # shall we
        parser.description = self.__doc__
        parser._optionals.title = "Django optional arguments"
        parser.add_argument(
            "-n",
            "--dryrun",
            action="store_true",
            help="dry run: do not make any changes",
        )

    def handle(self, **options):
        self.options = options
        LOG.setLevel(LOG_LEVELS[int(options["verbosity"])])
        init_utils_logger(LOG)
        update_title(options)
