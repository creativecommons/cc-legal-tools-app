# Standard library
import logging
import os
import posixpath

# Third-party
from bs4 import NavigableString
from django.conf import settings
from django.urls import get_resolver

# First-party/Local
import licenses.models
from i18n.utils import (
    get_default_language_for_jurisdiction,
    map_legacy_to_django_language_code,
)
from licenses.views import render_redirect

LOG = logging.getLogger(__name__)


def init_utils_logger(logger: logging.Logger = None):
    global LOG
    if logger is None:
        LOG = logging.getLogger(__name__)
    else:
        LOG = logger


def save_bytes_to_file(bytes, output_filename):
    dirname = os.path.dirname(output_filename)
    if os.path.isfile(dirname):
        os.remove(dirname)
    os.makedirs(dirname, mode=0o755, exist_ok=True)
    with open(output_filename, "wb") as f:
        f.write(bytes)  # Bytes


class MockRequest:
    method = "GET"
    META = {}

    def __init__(self, path):
        self.path = path


def save_url_as_static_file(output_dir, url, relpath):
    """
    Get the output from the URL and save it in an appropriate file
    under output_dir. For making static files from a site.

    Pass in open_func just for testing, not in regular use.
    """
    # Was using test Client, but it runs middleware and fails at runtime
    # because the request host wasn't in the ALLOWED_HOSTS. So, resolve the URL
    # and call the view directly.
    LOG.debug(f"    {relpath}")
    resolver = get_resolver()
    match = resolver.resolve(url)  # ResolverMatch
    rsp = match.func(request=MockRequest(url), *match.args, **match.kwargs)
    if rsp.status_code != 200:
        raise ValueError(f"ERROR: Status {rsp.status_code} for url {url}")
    output_filename = os.path.join(output_dir, relpath)
    save_bytes_to_file(rsp.content, output_filename)


def relative_symlink(src1, src2, dst):
    padding = " " * len(os.path.dirname(src2))
    src = os.path.abspath(os.path.join(src1, src2))
    dir_path, src_file = os.path.split(src)
    # Handle ../symlinks for xu jurisdiction
    if dst.startswith("../"):
        __, dst = os.path.split(dst)
        os.path.split(src2)
        dir_path, subdir = os.path.split(dir_path)
        src_file = os.path.join(subdir, src_file)
        padding = padding[:-3]
    dir_fd = os.open(dir_path, os.O_RDONLY)
    try:
        os.symlink(src_file, dst, dir_fd=dir_fd)
        LOG.debug(f"    {padding}^{dst}")
    finally:
        os.close(dir_fd)


def save_redirect(output_dir, redirect_data):
    relpath = redirect_data["redirect_file"]
    content = render_redirect(
        title=redirect_data["title"],
        destination=redirect_data["destination"],
        language_code=redirect_data["language_code"],
    )
    path, filename = os.path.split(relpath)
    padding = " " * (len(os.path.dirname(path)) + 8)
    LOG.debug(f"{padding}*{filename}")
    output_filename = os.path.join(output_dir, relpath)
    save_bytes_to_file(content, output_filename)


def parse_legal_code_filename(filename):
    """
    Given the filename where the HTML text of a license is stored,
    return a dictionary with the metadata we can figure out from it.

    The filename should not include any path. A trailing .html is okay.

    Partially based on:
    https://github.com/creativecommons/cc-link-checker/blob/a255d2b5d72df31b3e750b34dac2ac6effe7c792/link_checker/utils.py#L419-L469  # noqa: E501
    """

    basename = filename
    if basename.endswith(".html"):
        basename = basename[:-5]

    parts = basename.split("_")

    unit = parts.pop(0)
    if unit == "samplingplus":
        unit = "sampling+"
    elif unit == "nc-samplingplus":
        unit = "nc-sampling+"

    version = parts.pop(0)

    jurisdiction = None
    language_code = None
    deed_only = False
    if unit in licenses.models.UNITS_DEED_ONLY:
        deed_only = True
    deprecated_on = None
    if unit in licenses.models.UNITS_DEPRECATED:
        deprecated_on = licenses.models.UNITS_DEPRECATED[unit]
    unit_to_return = unit
    if unit in licenses.models.UNITS_PUBLIC_DOMAIN or unit == "zero":
        category = "publicdomain"
        if unit == "certification":
            jurisdiction = "us"
    elif unit in licenses.models.UNITS_LICENSES:
        category = "licenses"
        if parts and float(version) < 4.0:
            jurisdiction = parts.pop(0)
    else:
        return None

    # Set and validate language_code
    if parts:
        language_code = map_legacy_to_django_language_code(parts.pop(0))
    if jurisdiction:
        language_code = language_code or get_default_language_for_jurisdiction(
            jurisdiction, ""
        )
    else:
        language_code = language_code or settings.LANGUAGE_CODE
    if not language_code:
        raise ValueError(f"What language? filename={filename}")
    if language_code not in settings.LANG_INFO:
        # Valid Django language_codes are extended in settings with the
        # defaults in:
        # https://github.com/django/django/blob/main/django/conf/global_settings.py
        raise ValueError(f"{filename}: Invalid language_code={language_code}")

    canonical_url = compute_canonical_url(
        category, unit, version, jurisdiction
    )

    data = dict(
        category=category,
        unit=unit_to_return,
        version=version,
        jurisdiction_code=jurisdiction or "",
        language_code=language_code,
        canonical_url=canonical_url,
        deprecated_on=deprecated_on,
        deed_only=deed_only,
    )

    return data


def compute_canonical_url(category, unit, version, jurisdiction_code):
    """
    Compute the unique canonical URL for a license with the given
    attributes. Note that a "License" is language-independent, unlike a
    "LegalCode" but it can have a jurisdiction.

    E.g.

    https://creativecommons.org/licenses/BSD/
    https://creativecommons.org/licenses/GPL/2.0/
    https://creativecommons.org/licenses/LGPL/2.1/
    https://creativecommons.org/licenses/MIT/
    https://creativecommons.org/licenses/by/2.0/
    https://creativecommons.org/licenses/publicdomain/
    https://creativecommons.org/publicdomain/zero/1.0/
    https://creativecommons.org/publicdomain/mark/1.0/
    https://creativecommons.org/licenses/nc-sampling+/1.0/
    https://creativecommons.org/licenses/devnations/2.0/
    https://creativecommons.org/licenses/by/3.0/nl/
    https://creativecommons.org/licenses/by-nc-nd/3.0/br/
    https://creativecommons.org/licenses/by/4.0/
    https://creativecommons.org/licenses/by-nc-nd/4.0/
    """
    base = "https://creativecommons.org"

    if unit in ["BSD", "MIT"]:
        canonical_url = posixpath.join(
            base,
            category,
            unit,
        )
    else:
        canonical_url = posixpath.join(
            base,
            category,
            unit,
            version,
        )
    if jurisdiction_code:
        canonical_url = posixpath.join(canonical_url, jurisdiction_code)
    canonical_url = posixpath.join(canonical_url, "")
    return canonical_url


def validate_list_is_all_text(list_):
    """
    Just for sanity, make sure all the elements of a list are types that
    we expect to be in there.  Convert it all to str and return the
    result.
    """
    newlist = []
    for i, value in enumerate(list_):
        if type(value) == NavigableString:
            newlist.append(str(value))
            continue
        elif type(value) not in (str, list, dict):
            raise ValueError(
                f"Not a str, list, or dict: {type(value)}: {value}"
            )
        if isinstance(value, list):
            newlist.append(validate_list_is_all_text(value))
        elif isinstance(value, dict):
            newlist.append(validate_dictionary_is_all_text(value))
        else:
            newlist.append(value)
    return newlist


def validate_dictionary_is_all_text(d):
    """
    Just for sanity, make sure all the keys and values of a dictionary are
    types that we expect to be in there.
    """
    newdict = dict()
    for k, v in d.items():
        assert isinstance(k, str)
        if type(v) == NavigableString:
            newdict[k] = str(v)
            continue
        elif type(v) not in (str, dict, list):
            raise ValueError(f"Not a str: k={k} {type(v)}: {v}")
        if isinstance(v, dict):
            newdict[k] = validate_dictionary_is_all_text(v)
        elif isinstance(v, list):
            newdict[k] = validate_list_is_all_text(v)
        else:
            newdict[k] = v
    return newdict


def cleanup_current_branch_output(branch_list: list) -> list:
    """cleanups the way git outputs the current branch

    for example: git branch --list
        some-branch
        * main

        branch-list = ['some-branch', '* main']

    The asterisks is attached to the current branch, and we want to remove
    this:
        branch-list = ['some-branch' 'main']

    Arguments:
        branch-list (list) list of git branches.
    """
    cleaned_list = []
    for branch in branch_list:
        if "*" in branch:
            cleaned_branch = branch.replace("* ", "")
            cleaned_list.append(cleaned_branch)
        else:
            cleaned_list.append(branch)
    return cleaned_list


def clean_string(s):
    """
    Get a string into a canonical form - no whitespace at either end,
    no newlines, no double-spaces.
    """
    s = s.strip().replace("\n", " ").replace("  ", " ")
    while "  " in s:
        # If there were longer strings of spaces, need to iterate to replace...
        # I guess.
        s = s.replace("  ", " ")
    return s
