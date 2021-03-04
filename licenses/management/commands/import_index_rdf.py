# Third-party
from django.core.management.base import LabelCommand

# First-party/Local
from licenses.import_metadata_from_rdf import MetadataImporter
from licenses.models import (
    LegalCode,
    License,
    LicenseLogo,
    TranslatedLicenseName,
)


class Command(LabelCommand):
    def handle_label(self, label, *args, **options):
        filename = label
        print(f"Populating database with license data from {filename}")
        MetadataImporter(
            LegalCode, License, LicenseLogo, TranslatedLicenseName
        ).import_metadata(open(filename, "rb"))
