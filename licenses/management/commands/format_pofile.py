# Standard library
import glob
import logging
import os.path
from argparse import ArgumentParser

# Third-party
import polib
from django.conf import settings
from django.core.management import BaseCommand, CommandError

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
            "path",
            action="store",
            help="relative path to PO file or directory containing PO files"
            f" (relative to {settings.DATA_REPOSITORY_DIR})",
            metavar="FILE_OR_DIRECTORY",
        )

    def main(self, **options):
        LOG.setLevel(LOG_LEVELS[int(options["verbosity"])])

        files = []
        target = os.path.abspath(
            os.path.realpath(
                os.path.join(settings.DATA_REPOSITORY_DIR, options["path"])
            )
        )
        if not os.path.exists(target):
            raise CommandError(
                "invalid FIlE_OR_DIRECTORY--resulting path does not exist:"
                f" {target}"
            )
        if os.path.isfile(target):
            files.append(target)
        elif os.path.isdir(target):
            files = glob.glob(f"{target}/**/*.po", recursive=True)
        else:
            raise CommandError(
                "invalid FIlE_OR_DIRECTORY--resulting path is not a file or"
                f" directory: {target}"
            )
        if not files:
            raise CommandError(
                "invalid FIlE_OR_DIRECTORY--resulting path does not contain"
                f" any PO Files: {target}"
            )

        # Open PO File and then save it (so that polib formats it)
        for pofile_path in files:
            print(pofile_path)
            pofile_obj = polib.pofile(
                pofile_path,
                wrapwidth=78,  # Default: 78
                check_for_duplicates=True,  # Default: False
            )
            pofile_obj.save(pofile_path)

    def handle(self, **options):
        self.main(**options)
