import posixpath
import re
import urllib

from .models import License
from i18n import LANGUAGE_CODE_REGEX


def get_code_from_jurisdiction_url(url):
    pieces = urllib.parse.urlsplit(url).path.strip("/").split("/")
    try:
        code = pieces[1]
    except IndexError:
        code = ""
    return code


def get_license_url_from_legalcode_url(legalcode_url):
    """
    Return the URL of the license that this legalcode url is for.
    Legalcode URLs are like
    http://creativecommons.org/licenses/by/4.0/legalcode
    http://creativecommons.org/licenses/by/4.0/legalcode.es
    http://opensource.org/licenses/bsd-license.php

    License URLs are like
    http://creativecommons.org/licenses/by-nc-nd/4.0/
    http://creativecommons.org/licenses/BSD/
    """
    if legalcode_url == "http://opensource.org/licenses/bsd-license.php":
        return "http://creativecommons.org/licenses/BSD/"
    if legalcode_url == "http://opensource.org/licenses/mit-license.php":
        return "http://creativecommons.org/licenses/MIT/"

    regex = re.compile(r"^(.*)legalcode(\.%s)?" % LANGUAGE_CODE_REGEX)
    m = regex.match(legalcode_url)
    if m:
        return m.group(1)
    raise ValueError(f"regex did not match {legalcode_url}")


def parse_legalcode_filename(filename):
    """
    Given the filename where the HTML text of a license is stored,
    return a dictionary with the metadata we can figure out from it.

    The filename should not include any path. A trailing .html is okay.

    COPIED FROM
    https://github.com/creativecommons/cc-link-checker/blob/6bb2eae4151c5f7949b73f8d066c309f2413c4a5/link_checker.py#L231
    and modified a great deal.
    """

    basename = filename
    if basename.endswith(".html"):
        basename = basename[:-5]

    parts = basename.split("_")

    license = parts.pop(0)
    if license == "samplingplus":
        license = "sampling+"
    elif license == "nc-samplingplus":
        license = "nc-sampling+"

    license_code_for_url = license

    version = parts.pop(0)

    jurisdiction = None
    language = None
    if license.startswith("zero"):
        license_code_to_return = "CC0"
        path_base = "publicdomain"
    else:
        license_code_to_return = license
        path_base = "licenses"
        if parts and float(version) < 4.0:
            jurisdiction = parts.pop(0)

    if parts:
        language = parts.pop(0)

    if language:
        legalcode = f"legalcode.{language}"
    else:
        legalcode = False

    url = posixpath.join("http://creativecommons.org", path_base)
    url = posixpath.join(url, license_code_for_url)
    url = posixpath.join(url, version)

    if jurisdiction:
        url = posixpath.join(url, jurisdiction)

    if legalcode:
        url = posixpath.join(url, legalcode)
    else:
        url = f"{url}/"

    data = dict(
        license_code=license_code_to_return,
        version=version,
        jurisdiction_code=jurisdiction or "",
        language_code=language or "",
        url=url,
    )

    return data


# Django Distill Utility Functions


def get_licenses_code_and_version():
    """Returns an iterable of license dictionaries
    dictionary keys:
        - license_code
        - version
    """
    for license in License.objects.all():
        yield {
            "license_code": license.license_code,
            "version": license.version,
        }


def get_licenses_code_version_lang():
    """Returns an iterable of license dictionaries
    dictionary keys:
        - license_code
        - version
        - target_lang (
            value is a translated license's
            language_code
        )
    """
    for license in License.objects.all():
        for translated_license in license.names.all():
            yield {
                "license_code": license.license_code,
                "version": license.version,
                "target_lang": translated_license.language_code,
            }


def get_licenses_code_version_jurisdiction():
    """Returns an iterable of license dictionaries
    dictionary keys:
        - license_code
        - version
        - jurisdiction
    """
    for license in License.objects.all():
        yield {
            "license_code": license.license_code,
            "version": license.version,
            "jurisdiction": license.jurisdiction_code,
        }


def get_licenses_code_version_jurisdiction_lang():
    """Returns an iterable of license dictionaries
    dictionary keys:
        - license_code
        - version
        - jurisdiction
        - target_lang (
            value is a translated license's
            language_code
        )
    """
    for license in License.objects.all():
        for translated_license in license.names.all():
            yield {
                "license_code": license.license_code,
                "version": license.version,
                "jurisdiction": license.jurisdiction_code,
                "target_lang": translated_license.language_code,
            }
