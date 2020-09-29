from django.core.management import BaseCommand

from licenses.transifex import transifex_helper

TOP_BRANCH = "develop"

branch_name = "test_branch"


class Command(BaseCommand):
    def handle(self, **options):
        transifex_helper.check_for_translation_updates()
