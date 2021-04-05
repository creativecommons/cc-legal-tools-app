# Third-party
from django.core.management import BaseCommand

# First-party/Local
from licenses.models import License


class Command(BaseCommand):
    def handle(self, **options):
        for license in License.objects.filter(
            version="4.0", license_code__startswith="by"
        ):
            license.tx_upload_messages()
