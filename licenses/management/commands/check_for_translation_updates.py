# Standard library
import logging

# Third-party
from django.core.management import BaseCommand, CommandError, call_command
from git.exc import GitCommandError, RepositoryDirtyError

# First-party/Local
from licenses.transifex import TransifexHelper

LOG = logging.getLogger(__name__)
LOG_LEVELS = {
    0: logging.ERROR,
    1: logging.WARNING,
    2: logging.INFO,
    3: logging.DEBUG,
}


class Command(BaseCommand):
    def handle(self, **options):
        LOG.setLevel(LOG_LEVELS[int(options["verbosity"])])
        try:
            branches_updated = TransifexHelper(
                verbosity=options["verbosity"]
            ).check_for_translation_updates()
        except GitCommandError as e:
            raise CommandError(f"GitCommandError: {e}")
        except RepositoryDirtyError as e:
            raise CommandError(f"RepositoryDirtyError: {e}")

        # run collectstatic if we're going to publish
        if branches_updated:
            call_command("collectstatic", interactive=False)
            self.stdout.write("Ran collectstatic")

            for branch_name in branches_updated:
                # Update the HTML files, commit, and push
                call_command("publish", branch_name=branch_name)
                self.stdout.write(
                    f"Updated HTML files for {branch_name}, updated branch,"
                    " and pushed if needed"
                )
