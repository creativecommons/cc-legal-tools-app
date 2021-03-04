# Third-party
from django.core.management import BaseCommand, call_command

# First-party/Local
from licenses.transifex import TransifexHelper

TOP_BRANCH = "main"

branch_name = "test_branch"


class Command(BaseCommand):
    def handle(self, **options):
        branches_updated = TransifexHelper(
            verbosity=options["verbosity"]
        ).check_for_translation_updates()

        # run collectstatic if we're going to publish
        if branches_updated:
            call_command("collectstatic", interactive=False)
            print("Ran collectstatic")

            for branch_name in branches_updated:
                # Update the HTML files, commit, and push
                call_command("publish", branch_name=branch_name)
                print(
                    f"Updated HTML files for {branch_name}, updated branch,"
                    " and pushed if needed"
                )
