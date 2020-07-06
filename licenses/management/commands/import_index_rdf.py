from django.core.management.base import LabelCommand

from licenses.import_metadata_from_rdf import MetadataImporter


class Command(LabelCommand):
    def handle_label(self, label, *args, **options):
        filename = label
        print(f"Populating database with license data from {filename}")
        MetadataImporter().import_metadata(open(filename, "rb"))
