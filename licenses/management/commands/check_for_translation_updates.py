from django.core.management import BaseCommand

from licenses.transifex import check_for_translation_updates


class Command(BaseCommand):
    def handle(self, **options):
        check_for_translation_updates()
