from django.core.management import BaseCommand

from licenses.models import LegalCode, License


class Command(BaseCommand):
    def handle(self, **options):
        LegalCode.objects.all().delete()
        License.objects.all().delete()
