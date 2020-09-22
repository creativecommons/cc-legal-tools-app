from django.core.management import BaseCommand

from licenses.models import License


class Command(BaseCommand):
    def handle(self, **options):
        license = License.objects.get(version="4.0", license_code="by-nc-nd")
        license.tx_upload_messages()
