# Standard library
import logging
import os
import posixpath

# Third-party
from bs4 import NavigableString
from colorlog.escape_codes import escape_codes
from django.conf import settings
from django.core.cache import cache
from django.urls import get_resolver
from django.utils import translation

# First-party/Local
import legal_tools.models
from i18n import UNIT_NAMES
from i18n.utils import (
    active_translation,
    get_default_language_for_jurisdiction_legal_code,
    get_jurisdiction_name,
    get_translation_object,
    map_legacy_to_django_language_code,
)

LOG = logging.getLogger(__name__)


class MockRequest:
    method = "GET"
    META = {}
    GET = {"distilling": 1}

    def __init__(self, path):
        self.path = path


def init_utils_logger(logger: logging.Logger = None):
    global LOG
    if logger is None:
        LOG = logging.getLogger(__name__)
    else:
        LOG = logger


def save_bytes_to_file(filebytes, output_filename):
    dirname = os.path.dirname(output_filename)
    if os.path.isfile(dirname):
        os.remove(dirname)
    os.makedirs(dirname, mode=0o755, exist_ok=True)
    with open(output_filename, "wb") as f:
        f.write(filebytes)


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


def save_redirect(output_dir, redirect_file, redirect_content):
    path, filename = os.path.split(redirect_file)
    padding = " " * (len(os.path.dirname(path)) + 8)
    LOG.debug(f"{padding}*{filename}")
    output_filename = os.path.join(output_dir, redirect_file)
    save_bytes_to_file(redirect_content, output_filename)


def parse_legal_code_filename(filename):
    """
    Given the filename where the HTML text of a legal code is stored,
    return a dictionary with the metadata we can figure out from it.

    The filename should not include any path. A trailing .html is okay.
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
    if unit in legal_tools.models.UNITS_DEED_ONLY:
        deed_only = True
    deprecated_on = None
    if unit in legal_tools.models.UNITS_DEPRECATED:
        deprecated_on = legal_tools.models.UNITS_DEPRECATED[unit]
    unit_to_return = unit
    if unit in legal_tools.models.UNITS_PUBLIC_DOMAIN or unit == "zero":
        category = "publicdomain"
        if unit == "certification":
            jurisdiction = "us"
    elif unit in legal_tools.models.UNITS_LICENSES:
        category = "licenses"
        if parts and float(version) < 4.0:
            jurisdiction = parts.pop(0)
    else:
        return None

    # Set and validate language_code
    if parts:
        language_code = map_legacy_to_django_language_code(parts.pop(0))
    if jurisdiction:
        language_code = (
            language_code
            or get_default_language_for_jurisdiction_legal_code(jurisdiction)
        )
    else:
        language_code = language_code or settings.LANGUAGE_CODE

    # Valid Django language_codes are extended in settings with the
    # defaults in:
    # https://github.com/django/django/blob/main/django/conf/global_settings.py
    if language_code not in settings.LANG_INFO:
        raise ValueError(f"{filename}: Invalid language_code={language_code}")

    base_url = compute_base_url(category, unit, version, jurisdiction)

    data = dict(
        category=category,
        unit=unit_to_return,
        version=version,
        jurisdiction_code=jurisdiction or "",
        language_code=language_code,
        base_url=base_url,
        deprecated_on=deprecated_on,
        deed_only=deed_only,
    )

    return data


def compute_base_url(category, unit, version, jurisdiction_code):
    """
    Compute the unique base URL for a legal tool with the given attributes.
    Note that a "Tool" can have a jurisdiction, but is language-independent
    (unlike a "LegalCode", which is associated with a language).

    Examples:

    https://creativecommons.org/licenses/by-nc-nd/3.0/br/
    https://creativecommons.org/licenses/by-nc-nd/4.0/
    https://creativecommons.org/licenses/by/2.0/
    https://creativecommons.org/licenses/by/3.0/nl/
    https://creativecommons.org/licenses/by/4.0/
    https://creativecommons.org/licenses/devnations/2.0/
    https://creativecommons.org/licenses/nc-sampling+/1.0/
    https://creativecommons.org/licenses/publicdomain/
    https://creativecommons.org/publicdomain/mark/1.0/
    https://creativecommons.org/publicdomain/zero/1.0/
    """
    base_url = posixpath.join(
        settings.CANONICAL_SITE,
        category,
        unit,
        version,
    )
    if jurisdiction_code:
        base_url = posixpath.join(base_url, jurisdiction_code)
    base_url = posixpath.join(base_url, "")
    return base_url


def validate_list_is_all_text(list_):
    """
    Just for sanity, make sure all the elements of a list are types that
    we expect to be in there.  Convert it all to str and return the
    result.
    """
    newlist = []
    for i, value in enumerate(list_):
        if isinstance(value, NavigableString):
            newlist.append(str(value))
            continue
        elif not isinstance(value, (str, list, dict)):
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
    for key, value in d.items():
        assert isinstance(key, str)
        if isinstance(value, NavigableString):
            newdict[key] = str(value)
            continue
        elif not isinstance(value, (str, dict, list)):
            raise ValueError(f"Not a str: key={key} {type(value)}: {value}")
        if isinstance(value, dict):
            newdict[key] = validate_dictionary_is_all_text(value)
        elif isinstance(value, list):
            newdict[key] = validate_list_is_all_text(value)
        else:
            newdict[key] = value
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


def get_tool_title(unit, version, category, jurisdiction, language_code):
    """
    Determine tool title:
    1. If English, use English
    2. Attempt to pull translated title from DB
    3. Translate title using Deeds & UX translation domain
    """
    prefix = f"{unit}-{version}-{jurisdiction}-{language_code}-"
    tool_title = cache.get(f"{prefix}title", "")
    if tool_title:
        return tool_title

    # English is easy given it is the default
    tool_title_en = get_tool_title_en(unit, version, category, jurisdiction)
    if language_code == "en":
        tool_title = tool_title_en  # already applied clean_string()
        cache.add(f"{prefix}title", tool_title)
        return tool_title

    # Use the legal code title, if it exists
    try:
        legal_code = legal_tools.models.LegalCode.objects.get(
            tool__category=category,
            tool__version=version,
            tool__unit=unit,
            tool__jurisdiction_code=jurisdiction,
            language_code=language_code,
        )
    except legal_tools.models.LegalCode.DoesNotExist:
        legal_code = False
    if legal_code:
        tool_title_db = clean_string(legal_code.title)
        if tool_title_db and tool_title_db != tool_title_en:
            tool_title = tool_title_db
            cache.add(f"{prefix}title", tool_title)
            return tool_title

    # Translate title using Deeds & UX translation domain
    with translation.override(language_code):
        tool_name = UNIT_NAMES.get(unit, "UNIMPLEMENTED")
        jurisdiction_name = get_jurisdiction_name(
            category, unit, version, jurisdiction
        )
        tool_title = clean_string(f"{tool_name} {version} {jurisdiction_name}")

    cache.add(f"{prefix}title", tool_title)
    return tool_title


def get_tool_title_en(unit, version, category, jurisdiction):
    prefix = f"{unit}-{version}-{jurisdiction}-en-"
    tool_title_en = cache.get(f"{prefix}title", "")
    if tool_title_en:
        return tool_title_en

    # Retrieve title parts untranslated (English)
    with translation.override(None):
        tool_name = str(UNIT_NAMES.get(unit, "UNIMPLEMENTED"))
        jurisdiction_name = str(
            get_jurisdiction_name(category, unit, version, jurisdiction)
        )
    # Licenses before 4.0 use "NoDerivs" instead of "NoDerivatives"
    if version not in ("1.0", "2.0", "2.1", "2.5", "3.0"):
        tool_name = tool_name.replace("NoDerivs", "NoDerivatives")
    tool_title_en = f"{tool_name} {version} {jurisdiction_name}"
    tool_title_en = tool_title_en.replace(
        " Intergovernmental Organization", " IGO"
    )
    tool_title_en = clean_string(tool_title_en)

    cache.add(f"{prefix}title", tool_title_en)
    return tool_title_en


def update_is_replaced_by():
    """
    Update the is_replaced_by property of all licenses by doing simple unit
    and version comparisons.

    Since version 4.0, the licenses are international, so no jurisdiction
    comparison is made.
    """
    tool_objects = (
        legal_tools.models.Tool.objects.all()
        .filter(category="licenses")
        .order_by(
            # The code below breaks if not sorted by version decending
            "-version",
            "unit",
            "jurisdiction_code",
        )
    )
    version_latest = None
    for tool in tool_objects:
        if not version_latest:
            version_latest = tool.version
            continue
        if tool.version == version_latest:
            continue
        try:
            latest = legal_tools.models.Tool.objects.get(
                category="licenses",
                version=version_latest,
                unit=tool.unit,
            )
        except legal_tools.models.Tool.DoesNotExist:
            latest = False
        if latest:
            if tool.is_replaced_by == latest:
                LOG.debug(
                    f"{tool.resource_name} is_replaced_by already set to"
                    " correct value"
                )
                continue
            LOG.info(
                f"{tool.resource_name} is_replaced_by {latest.resource_name}"
            )
            tool.is_replaced_by = latest
            tool.save()


def update_source():
    """
    Update the source property of all licenses by doing simple unit
    and version comparisons.
    """
    versions = sorted(legal_tools.models.TOOLS_VERSIONS, reverse=True)
    tool_objects = legal_tools.models.Tool.objects.all()

    for tool in tool_objects:
        version_index = versions.index(tool.version)
        source = None

        # exlude earliest versions which can't have a source
        if tool.version != "1.0":
            # loop through the versions defined in TOOLS_VERSIONS starting with
            # the same version as the current tool
            for version in versions[version_index:]:
                if version == tool.version and not tool.jurisdiction_code:
                    # only ported legal tools might have a source with the same
                    # versions as the tool itself
                    continue

                try:
                    source = legal_tools.models.Tool.objects.get(
                        unit=tool.unit,
                        version=version,
                        jurisdiction_code="",
                    )
                    break
                except legal_tools.models.Tool.DoesNotExist:
                    continue

        if tool.source == source:
            if source:
                source_value = source.resource_name
            else:
                source_value = source
            LOG.debug(f"No-op: {tool.resource_name} source: {source_value}")
        elif source:
            tool.source = source
            tool.save()
            LOG.info(
                f"Set {tool.resource_name} source: {source.resource_name}"
            )
        else:
            LOG.info(f"Remove {tool.resource_name} source: '{tool.source}'")
            tool.source = None
            tool.save()


def update_title(options):
    """
    Update the title property of all legal tools by normalizing legacy titles
    and normalizing translated titles for current legal tools (Licenses 4.0 and
    CC0 1.0).
    """
    bold = escape_codes["bold"]
    green = escape_codes["green"]
    red = escape_codes["red"]
    reset = escape_codes["reset"]
    pad = " " * 14

    results = {"records_updated": 0, "records_requiring_update": 0}
    if options["dryrun"]:
        message = "requires update (dryrun)"
    else:
        message = "changed"

    LOG.info("Updating legal code object titles in database")
    legal_code_objects = legal_tools.models.LegalCode.objects.all()
    for legal_code in legal_code_objects:
        tool = legal_code.tool
        category = tool.category
        version = tool.version
        unit = tool.unit
        jurisdiction = tool.jurisdiction_code
        language_code = legal_code.language_code
        language_name = translation.get_language_info(language_code)["name"]
        full_identifier = f"{bold}{tool.identifier()} {language_name}{reset}"
        old_title = legal_code.title
        new_title = None

        # English is easy given it is the default
        tool_title_en = get_tool_title_en(
            unit, version, category, jurisdiction
        )
        if language_code == "en":
            new_title = tool_title_en  # already applied clean_string()
        else:
            if (
                category == "licenses"
                and version in ("1.0", "2.0", "2.1", "2.5", "3.0")
            ) and unit != "zero":
                # Query database for title extracted from legacy HTML and clean
                # it
                new_title_db = clean_string(old_title)
                if new_title_db and new_title_db != tool_title_en:
                    new_title = new_title_db
            else:
                # Translate title using legal code translation domain for legal
                # code that is in Transifex (ex. CC0, Licenses 4.0)
                slug = f"{unit}_{version}".replace(".", "")
                language_default = get_default_language_for_jurisdiction_legal_code(
                    jurisdiction
                )
                current_translation = get_translation_object(
                    slug, language_code, language_default
                )
                tool_title_lc = ""
                with active_translation(current_translation):
                    tool_title_lc = clean_string(
                        translation.gettext(tool_title_en)
                    )
                # Only use legal code translation domain version if translation
                # was successful (does not match English). There are deed
                # translations in languages for which we do not yet have legal
                # code translations.
                if tool_title_lc != tool_title_en:
                    new_title = tool_title_lc
            if not new_title:
                # Translate title using Deeds & UX translation domain
                with translation.override(language_code):
                    tool_name = UNIT_NAMES.get(unit, "UNIMPLEMENTED")
                    jurisdiction_name = get_jurisdiction_name(
                        category, unit, version, jurisdiction
                    )
                    new_title = clean_string(
                        f"{tool_name} {version} {jurisdiction_name}"
                    )

        if old_title == new_title:
            LOG.debug(f'{full_identifier} title unchanged: "{old_title}"')
        else:
            if options["dryrun"]:
                results["records_requiring_update"] += 1
            else:
                legal_code.title = new_title
                legal_code.save()
                results["records_updated"] += 1
            LOG.info(
                f"{full_identifier} title {message}:"
                f'\n{pad}{red}- "{reset}{old_title}{red}"{reset}'
                f'\n{pad}{green}+ "{reset}{new_title}{green}"{reset}'
            )

    if options["dryrun"]:
        count = results["records_requiring_update"]
        LOG.info(f"legal code object titles requiring an update: {count}")
    else:
        count = results["records_updated"]
        LOG.info(f"legal code object titles updated: {count}")

    return results
