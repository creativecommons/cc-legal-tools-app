# We used to use this migration to read the data from index.rdf
# into the database. We don't do that anymore.
# Third-party
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("licenses", "0001_initial"),
    ]

    operations = []
