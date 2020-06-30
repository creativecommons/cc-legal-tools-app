"""EXTRACT English messages from all the code and make or update a .po file"""
import os
import subprocess

from django.core.management import BaseCommand

from django.conf import settings

from licenses.utils import get_locale_dir


class Command(BaseCommand):
    def handle(self, *args, **options):
        raise NotImplementedError
        # locale = "en"
        # locale_dir = get_locale_dir(locale)
        # if not os.path.isdir(locale_dir):
        #     os.makedirs(locale_dir)
        # domain = "django"
        # potfile = os.path.join(locale_dir, f"{domain}.pot")
        #
        # mapping_file = os.path.join(settings.ROOT_DIR, "babel_mapping.ini")
        #
        # subprocess.run(
        #     [
        #         "pybabel",
        #         "extract",
        #         "--project",
        #         "cc-licenses",
        #         "--output",
        #         potfile,
        #         "--mapping",
        #         mapping_file,
        #         "--no-location",  # Don't include filename/line in comments, they change too much
        #         ".",
        #     ],
        #     check=True,
        # )
        #
        # pofile = os.path.join(locale_dir, f"{domain}.po")
        # if os.path.exists(pofile):
        #     # MERGE into existing file
        #     command = "update"
        # else:
        #     # CREATE new file
        #     command = "init"
        # subprocess.run(
        #     [
        #         "pybabel",
        #         command,
        #         "--domain",
        #         domain,
        #         "--input-file",
        #         potfile,
        #         "--output-file",
        #         pofile,
        #         "--locale",
        #         locale,
        #     ],
        #     check=True,
        # )
        #
        # os.remove(potfile)
