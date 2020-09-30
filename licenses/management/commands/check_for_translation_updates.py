from django.core.management import BaseCommand

from licenses.transifex import TransifexHelper

TOP_BRANCH = "develop"

branch_name = "test_branch"


class Command(BaseCommand):
    def handle(self, **options):
        TransifexHelper().check_for_translation_updates()
