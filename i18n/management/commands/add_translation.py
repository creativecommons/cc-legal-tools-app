# Standard library
import logging
from argparse import ArgumentParser

# Third-party
from django.conf import settings
from django.core.management import BaseCommand, CommandError

# First-party/Local
from legal_tools.models import LegalCode, Tool

LOG = logging.getLogger(__name__)
LOG_LEVELS = {
    0: logging.ERROR,
    1: logging.WARNING,
    2: logging.INFO,
    3: logging.DEBUG,
}


class Command(BaseCommand):
    """
    Create new Licenses 4.0 or CC Zero 1.0 LegalCode objects for a given
    language.
    """

    def add_arguments(self, parser: ArgumentParser):
        domains = parser.add_mutually_exclusive_group(required=True)
        domains.add_argument(
            "--licenses",
            action="store_const",
            const="licenses",
            help="Add licenses 4.0 translations",
            dest="domains",
        )
        domains.add_argument(
            "--zero",
            action="store_const",
            const="zero",
            help="Add CC0 1.0 translation",
            dest="domains",
        )
        parser.add_argument(
            "-l",
            "--language",
            action="store",
            required=True,
            help="limit translation language to specified Language Code",
        )
        parser.add_argument(
            "-n",
            "--dryrun",
            action="store_true",
            help="dry run: do not make any changes",
        )

    def add_legal_code(self, options, category, version, unit=None):
        tool_parameters = {"category": category, "version": version}
        if unit is not None:
            tool_parameters["unit"] = unit
        tools = Tool.objects.filter(**tool_parameters).order_by("unit")
        for tool in tools:
            title = f"{tool.unit} {tool.version} {options['language']}"
            legal_code_parameters = {
                "tool": tool,
                "language_code": options["language"],
            }
            if LegalCode.objects.filter(**legal_code_parameters).exists():
                LOG.warn(f"LegalCode object already exists: {title}")
            else:
                LOG.info(f"Creating LeglCode object: {title}")
                if not options["dryrun"]:
                    _ = LegalCode.objects.create(**legal_code_parameters)

    def handle(self, **options):
        LOG.setLevel(LOG_LEVELS[int(options["verbosity"])])
        if options["language"] not in settings.LANG_INFO:
            raise CommandError(f"Invalid language code: {options['language']}")
        if options["domains"] == "licenses":
            self.add_legal_code(options, "licenses", "4.0")
        elif options["domains"] == "zero":
            self.add_legal_code(options, "publicdomain", "1.0", "zero")
