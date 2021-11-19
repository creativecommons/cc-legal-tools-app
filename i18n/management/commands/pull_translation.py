# Standard library
import logging
from argparse import ArgumentParser

# Third-party
from django.conf.locale import LANG_INFO
from django.core.management import BaseCommand, CommandError
from git.exc import GitCommandError, RepositoryDirtyError
from requests.exceptions import HTTPError

# First-party/Local
from i18n.transifex import TransifexHelper

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
            help="dry run: do not make any changes",
        )
        parser.add_argument(
            "-d",
            "--domain",
            action="store",
            required=True,
            help="limit translation domain to specified domain",
        )
        parser.add_argument(
            "-l",
            "--language",
            action="store",
            required=True,
            help="limit translation language to specified Language Code",
        )

    def main(self, **options):
        if options["language"] not in LANG_INFO:
            raise CommandError(f"Invalid language code: {options['language']}")
        LOG.setLevel(LOG_LEVELS[int(options["verbosity"])])
        transifex = TransifexHelper(dryrun=options["dryrun"], logger=LOG)
        transifex.pull_translation(options["domain"], options["language"])

    def handle(self, **options):
        try:
            self.main(**options)
        except GitCommandError as e:
            raise CommandError(f"GitCommandError: {e}")
        except HTTPError as e:
            raise CommandError(f"HTTPError: {e}")
        except RepositoryDirtyError as e:
            raise CommandError(f"RepositoryDirtyError: {e}")
