# Standard library
import datetime
import logging
import os.path
from argparse import ArgumentParser

# Third-party
import polib
from django.conf import settings
from django.core.management import BaseCommand, CommandError, call_command

# First-party/Local
from i18n.utils import (
    map_django_to_transifex_language_code,
    save_pofile_as_pofile_and_mofile,
)
from legal_tools.models import LegalCode, Tool

LOG = logging.getLogger(__name__)
LOG_LEVELS = {
    0: logging.ERROR,
    1: logging.WARNING,
    2: logging.INFO,
    3: logging.DEBUG,
}
NOW = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S+0000")


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

    def write_po_files(
        self,
        legal_code,
        language_code,
    ):
        po_filename = legal_code.translation_filename()
        pofile = polib.POFile()
        transifex_language = map_django_to_transifex_language_code(
            language_code
        )

        # Use the English message text as the message key
        en_pofile_path = legal_code.get_english_pofile_path()
        en_pofile_obj = polib.pofile(en_pofile_path)
        for entry in en_pofile_obj:
            pofile.append(polib.POEntry(msgid=entry.msgid, msgstr=""))

        # noqa: E501
        # https://www.gnu.org/software/gettext/manual/html_node/Header-Entry.html
        pofile.metadata = {
            "Content-Transfer-Encoding": "8bit",
            "Content-Type": "text/plain; charset=utf-8",
            "Language": transifex_language,
            "Language-Django": language_code,
            "Language-Transifex": transifex_language,
            "Language-Team": "https://www.transifex.com/creativecommons/CC/",
            "MIME-Version": "1.0",
            "PO-Revision-Date": NOW,
            "Percent-Translated": pofile.percent_translated(),
            "Project-Id-Version": legal_code.tool.resource_slug,
        }

        directory = os.path.dirname(po_filename)
        if not os.path.isdir(directory):
            os.makedirs(directory)
        # Save mofile ourself. We could call 'compilemessages' but
        # it wants to compile everything, which is both overkill
        # and can fail if the venv or project source is not
        # writable. We know this dir is writable, so just save this
        # pofile and mofile ourselves.
        LOG.info(f"Writing {po_filename.replace('.po', '')}.(mo|po)")
        save_pofile_as_pofile_and_mofile(pofile, po_filename)

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
                    legal_code = LegalCode.objects.create(
                        **legal_code_parameters
                    )
                    self.write_po_files(legal_code, options["language"])

    def handle(self, **options):
        LOG.setLevel(LOG_LEVELS[int(options["verbosity"])])
        if options["language"] not in settings.LANG_INFO:
            raise CommandError(f"Invalid language code: {options['language']}")
        if options["domains"] == "licenses":
            self.add_legal_code(options, "licenses", "4.0")
        elif options["domains"] == "zero":
            self.add_legal_code(options, "publicdomain", "1.0", "zero")
        call_command("update_is_replaced_by", verbosity=options["verbosity"])
        call_command("update_source", verbosity=options["verbosity"])
