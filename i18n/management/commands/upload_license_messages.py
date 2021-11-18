# Standard library
import logging

# Third-party
from django.core.management import BaseCommand

# First-party/Local
from licenses.models import License

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
        for license in License.objects.filter(
            version="4.0", unit__startswith="by"
        ):
            license.tx_upload_messages()
