# Standard library
import logging

# Third-party
from django.core.management import BaseCommand

# First-party/Local
from legal_tools.utils import init_utils_logger, update_is_replaced_by

LOG = logging.getLogger(__name__)
LOG_LEVELS = {
    0: logging.ERROR,
    1: logging.WARNING,
    2: logging.INFO,
    3: logging.DEBUG,
}


class Command(BaseCommand):
    def handle(self, **options):
        LOG.setLevel(LOG_LEVELS[int(options["verbosity"])])
        init_utils_logger(LOG)
        update_is_replaced_by()
