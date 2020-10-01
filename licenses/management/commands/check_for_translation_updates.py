from django.core.management import BaseCommand, call_command

from licenses.transifex import TransifexHelper

TOP_BRANCH = "develop"

branch_name = "test_branch"


class Command(BaseCommand):
    def handle(self, **options):
        branches_updated = TransifexHelper().check_for_translation_updates()

        # run collectstatic if we're going to publish
        if branches_updated:
            call_command("collectstatic", interactive=False)

        for branch_name in branches_updated:
            # Update the HTML files, commit, and push
            call_command("publish", branch_name=branch_name)
