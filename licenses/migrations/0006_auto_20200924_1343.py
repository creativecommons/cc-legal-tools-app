# flake8: noqa: E501
# Third-party
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("licenses", "0005_auto_20200916_1047"),
    ]

    operations = [
        migrations.AddField(
            model_name="legalcode",
            name="translation_last_update",
            field=models.DateTimeField(
                default=None,
                help_text="The last_updated field from Transifex for this"
                " translation",
                null=True,
            ),
        ),
        migrations.CreateModel(
            name="TranslationBranch",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("branch_name", models.CharField(max_length=40)),
                (
                    "version",
                    models.CharField(
                        blank=True,
                        default="",
                        help_text="E.g. '4.0'. Not required.",
                        max_length=3,
                    ),
                ),
                (
                    "language_code",
                    models.CharField(
                        help_text="E.g. 'en', 'en-ca', 'sr-Latn', or 'x-i18n'."
                        " Case-sensitive?",
                        max_length=8,
                    ),
                ),
                (
                    "last_transifex_update",
                    models.DateTimeField(
                        blank=True,
                        null=True,
                        verbose_name="Time when last updated on Transifex.",
                    ),
                ),
                (
                    "complete",
                    models.BooleanField(
                        default=False,
                        verbose_name="Only one incomplete per branch",
                    ),
                ),
                (
                    "legalcodes",
                    models.ManyToManyField(to="licenses.LegalCode"),
                ),
            ],
        ),
    ]
