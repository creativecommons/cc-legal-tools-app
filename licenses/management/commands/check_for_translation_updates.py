from django.core.management import BaseCommand

from licenses.transifex import TransifexHelper

TOP_BRANCH = "develop"

branch_name = "test_branch"


class Command(BaseCommand):
    def handle(self, **options):
        # FIXME by default only output errors
        TransifexHelper(  # assign to 'branches_updated' when lower part is uncommented
            verbosity=options["verbosity"]
        ).check_for_translation_updates()

        # TEMPORARILY comment out the publish step so we can commit what we have

        # # run collectstatic if we're going to publish
        # if branches_updated:
        #     call_command("collectstatic", interactive=False)
        #     print("Ran collectstatic")
        #
        # for branch_name in branches_updated:
        #     # Update the HTML files, commit, and push
        #     call_command("publish", branch_name=branch_name)
        #     print(f"Updated HTML files for {branch_name}, updated branch, and pushed")
