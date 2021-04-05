# Standard library
import os
from argparse import ArgumentParser

# Third-party
from django.core.management import BaseCommand

# First-party/Local
from i18n import DEFAULT_LANGUAGE_CODE
from licenses.models import LegalCode, License
from licenses.utils import (
    get_license_url_from_legalcode_url,
    parse_legalcode_filename,
)


class Command(BaseCommand):
    """
    Management command that reads all the HTML license files in the specified
    directories and populates the "raw_html" field of the corresponding
    LegalCode objects.

    It doesn't try to parse the HTML. It just stores it for later use.
    """

    def add_arguments(self, parser: ArgumentParser):
        parser.add_argument("input_directory")

    def handle(self, *args, **options):
        # License HTML files are in
        # https://github.com/creativecommons/creativecommons.org/tree/master/docroot/legalcode  # noqa: E501
        # Let's just assume we've downloaded them somewhere, and pass the input
        # directory.
        # PER
        # https://creativecommons.slack.com/archives/C014SUAT8Q2/p1594919397011700?thread_ts=1594817395.003200&cid=C014SUAT8Q2  # noqa: E501
        # "the docroot/legalcode files are the primary source of truth"
        # (these are the HTML files with the legal license text).
        input_directory = options["input_directory"]
        html_filenames = sorted(
            [f for f in os.listdir(input_directory) if f.endswith(".html")]
        )

        LegalCode.objects.filter(url="").delete()

        for html_filename in html_filenames:
            data = parse_legalcode_filename(html_filename)

            if data["version"] == "1.0.br":
                # This is a bad license file. There's another one for this
                # license/jurisdiction, so we can just ignore this one.
                continue

            # print(f"{html_filename} {data}")
            url = data["url"]
            # print(f"Getting LegalCode(url={url})")
            try:
                legal_code = LegalCode.objects.get(url=url)
            except LegalCode.DoesNotExist:
                print(
                    f"NO LegalCode objects for {html_filename} {url}, looking"
                    " for another for the same license"
                    " code/version/jurisdiction."
                )
                try:
                    license = License.objects.get(
                        license_code=data["license_code"],
                        version=data["version"],
                        jurisdiction_code=data["jurisdiction_code"],
                    )
                except License.DoesNotExist:
                    print(
                        "Did not find any license with the same"
                        " code/version/jurisdiction. Will look for another"
                        " with that code and copy it to make a new one."
                    )
                    # Try to gen one up
                    # Copy one with the same license_code so all the
                    # permissions are correct.
                    # print(
                    #     "Looking for license with license code"
                    #     f" {data['license_code']}"
                    # )
                    license = License.objects.filter(
                        license_code=data["license_code"]
                    ).first()
                    if license is None:
                        print(f"{html_filename} {data}")
                        raise Exception(
                            f"There is no license for {data}, and no license"
                            f" for license code {data['license_code']} to make"
                            " one up from. Something needs to be fixed."
                        )
                    license.pk = None
                    license.jurisdiction_code = data["jurisdiction_code"]
                    license.version = data["version"]
                    license.source = (
                        license.is_replaced_by
                    ) = license.is_based_on = license.deprecated_on = None
                    license.about = get_license_url_from_legalcode_url(url)
                    license.save()
                legal_code = LegalCode.objects.create(
                    url=url,
                    license=license,
                    language_code=data["language_code"]
                    or DEFAULT_LANGUAGE_CODE,
                )

            if legal_code.raw_html:
                # Got it already
                continue

            # print(f"{html_filename} {url}")
            html_path = os.path.join(input_directory, html_filename)
            legal_code.raw_html = open(html_path, "r", encoding="utf-8").read()
            legal_code.save()
