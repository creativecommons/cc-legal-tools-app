# Third-party
from django.core.management import BaseCommand

# First-party/Local
from licenses.models import LegalCode, License


class Command(BaseCommand):
    def handle(self, **options):
        LegalCode.objects.all().delete()
        License.objects.all().delete()
