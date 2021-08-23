# Standard library
import logging
from argparse import ArgumentParser

# Third-party
from django.core.management import BaseCommand, CommandError
from git.exc import GitCommandError, RepositoryDirtyError
from requests.exceptions import HTTPError

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
    def add_arguments(self, parser: ArgumentParser):
        parser.add_argument(
            "-n",
            "--dryrun",
            action="store_true",
            help="Dry run: do not make any changes.",
        )

    def handle(self, **options):
        LOG.setLevel(LOG_LEVELS[int(options["verbosity"])])
        try:
            transifex = TransifexHelper(dryrun=options["dryrun"], logger=LOG)
            transifex.normalize_translations()
        except GitCommandError as e:
            raise CommandError(f"GitCommandError: {e}")
        except HTTPError as e:
            raise CommandError(f"HTTPError: {e}")
        except RepositoryDirtyError as e:
            raise CommandError(f"RepositoryDirtyError: {e}")
