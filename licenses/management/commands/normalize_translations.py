# Standard library
import logging
from argparse import ArgumentParser

# Third-party
from django.conf.locale import LANG_INFO
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
            help="dry run: do not make any changes",
        )
        limit_domain = parser.add_mutually_exclusive_group()
        limit_domain.add_argument(
            "--deeds-ux",
            "--deedsux",
            action="store_true",
            help="limit translation domain normalization to Deeds & UX",
        )
        limit_domain.add_argument(
            "--legal-code",
            "--legalcode",
            action="store_true",
            help="limit translation domain normalization to Legal Codes",
        )
        parser.add_argument(
            "-l",
            "--language",
            action="store",
            help="limit translation language to specified Language Code",
        )

    def main(self, **options):
        if options["deeds_ux"]:
            limit_domain = "deeds_ux"
        elif options["legal_code"]:
            limit_domain = "legal_code"
        else:
            limit_domain = None
        limit_language = options["language"]
        if limit_language is not None and limit_language not in LANG_INFO:
            raise CommandError(f"Invalid language code: {limit_language}")
        LOG.setLevel(LOG_LEVELS[int(options["verbosity"])])
        transifex = TransifexHelper(dryrun=options["dryrun"], logger=LOG)
        transifex.normalize_translations(limit_domain, limit_language)

    def handle(self, **options):
        try:
            self.main(**options)
        except GitCommandError as e:
            raise CommandError(f"GitCommandError: {e}")
        except HTTPError as e:
            raise CommandError(f"HTTPError: {e}")
        except RepositoryDirtyError as e:
            raise CommandError(f"RepositoryDirtyError: {e}")
