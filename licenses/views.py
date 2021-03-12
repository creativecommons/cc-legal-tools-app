# Standard library
import re
import subprocess
import tempfile
from operator import itemgetter
from typing import Iterable

# Third-party
import git
import yaml
from bs4 import BeautifulSoup
from django.conf import settings
from django.core.cache import caches
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render
from django.template.loader import render_to_string
from django.utils.translation import get_language_info

# First-party/Local
from i18n import JURISDICTION_NAMES
from i18n.utils import active_translation, cc_to_django_language_code
from licenses.models import (
    BY_LICENSE_CODES,
    LegalCode,
    License,
    TranslationBranch,
)

DEED_TEMPLATE_MAPPING = {  # CURRENTLY UNUSED
    # license_code : template name
    "sampling": "licenses/sampling_deed.html",
    "sampling+": "licenses/sampling_deed.html",
    "nc-sampling+": "licenses/sampling_deed.html",
    "devnations": "licenses/devnations_deed.html",
    "CC0": "licenses/zero_deed.html",
    "mark": "licenses/pdmark_deed.html",
    "publicdomain": "licenses/publicdomain_deed.html",
    # others use "licenses/standard_deed.html"
}

NUM_COMMITS = 3

# For removing the deed.foo section of a deed url
REMOVE_DEED_URL_RE = re.compile(r"^(.*?/)(?:deed)?(?:\..*)?$")


def all_licenses(request):
    """
    For test purposes, this displays all the available deeds and licenses in
    tables.  This is not intended for public use and should not be included in
    the generation of static files.
    """

    # Get the list of license codes and languages that occur among the licenses
    # to let the template iterate over them as it likes.
    legalcode_objects = (
        LegalCode.objects.valid()
        .select_related("license")
        .order_by(
            "-license__version",
            "license__jurisdiction_code",
            "language_code",
            "license__license_code",
        )
    )
    legalcodes = [
        dict(
            version=lc.license.version,
            jurisdiction=JURISDICTION_NAMES.get(
                lc.license.jurisdiction_code, lc.license.jurisdiction_code
            ),
            license_code=lc.license.license_code,
            language_code=lc.language_code,
            deed_url=lc.deed_url,
            license_url=lc.license_url,
        )
        for lc in legalcode_objects
    ]
    return render(
        request,
        "all_licenses.html",
        {"legalcodes": legalcodes, "license_codes": sorted(BY_LICENSE_CODES)},
    )


def name_local(legal_code):
    return get_language_info(
        cc_to_django_language_code(legal_code.language_code)
    )["name_local"]


def get_languages_and_links_for_legalcodes(
    legalcodes: Iterable[LegalCode],
    selected_language_code: str,
    license_or_deed: str,
):
    """
    license_or_deed should be "license" or "deed", controlling which kind of
    page we link to.
    selected_language_code is a CC language code
    """
    languages_and_links = [
        {
            "cc_language_code": legal_code.language_code,
            # name_local: name of language in its own language
            "name_local": name_local(legal_code),
            "name_for_sorting": name_local(legal_code).lower(),
            "link": legal_code.license_url
            if license_or_deed == "license"
            else legal_code.deed_url,
            "selected": selected_language_code == legal_code.language_code,
        }
        for legal_code in legalcodes
    ]
    languages_and_links.sort(key=itemgetter("name_for_sorting"))
    return languages_and_links


def view_license(
    request,
    license_code,
    version,
    jurisdiction=None,
    language_code=None,  # CC language code
    is_plain_text=False,
):
    if is_plain_text:
        legalcode = get_object_or_404(
            LegalCode,
            plain_text_url=request.path,
        )
    else:
        legalcode = get_object_or_404(
            LegalCode,
            license_url=request.path,
        )

    language_code = legalcode.language_code  # CC language code
    languages_and_links = get_languages_and_links_for_legalcodes(
        legalcode.license.legal_codes.all(), language_code, "license"
    )

    kwargs = dict(
        template_name="legalcode_page.html",
        context={
            "fat_code": legalcode.license.fat_code(),
            "languages_and_links": languages_and_links,
            "legalcode": legalcode,
            "license": legalcode.license,
        },
    )

    translation = legalcode.get_translation_object()
    with active_translation(translation):
        if is_plain_text:
            response = HttpResponse(content_type='text/plain; charset="utf-8"')
            html = render_to_string(**kwargs)
            soup = BeautifulSoup(html, "lxml")
            plain_text_soup = soup.find(id="plain-text-marker")
            # FIXME: prune the "img" tags from this before saving again.
            with tempfile.NamedTemporaryFile(mode="w+b") as temp:
                temp.write(plain_text_soup.encode("utf-8"))
                output = subprocess.run(
                    [
                        "pandoc",
                        "-f",
                        "html",
                        temp.name,
                        "-t",
                        "plain",
                    ],
                    encoding="utf-8",
                    capture_output=True,
                )
                response.write(output.stdout)
                return response

        return render(request, **kwargs)


def view_deed(
    request, license_code, version, jurisdiction=None, language_code=None
):
    legalcode = get_object_or_404(
        LegalCode,
        deed_url=request.path,
    )
    license = legalcode.license
    language_code = legalcode.language_code  # CC language code
    languages_and_links = get_languages_and_links_for_legalcodes(
        license.legal_codes.all(), language_code, "deed"
    )

    if license.license_code == "CC0":
        body_template = "includes/deed_cc0_body.html"
    elif license.version == "4.0":
        body_template = "includes/deed_40_body.html"
    else:
        # Default to 4.0 - or maybe we should just fail?
        body_template = "includes/deed_40_body.html"

    translation = legalcode.get_translation_object()
    with active_translation(translation):
        return render(
            request,
            "deed.html",
            {
                "additional_classes": "",
                "body_template": body_template,
                "fat_code": legalcode.license.fat_code(),
                "languages_and_links": languages_and_links,
                "legalcode": legalcode,
                "license": legalcode.license,
            },
        )


def translation_status(request):
    # with git.Repo(settings.TRANSLATION_REPOSITORY_DIRECTORY) as repo:
    # # Make sure we know about all the upstream branches
    # repo.remotes.origin.fetch()
    # heads = repo.remotes.origin.refs
    # branches = [head.name[len("origin/") :] for head in heads]

    branches = TranslationBranch.objects.exclude(complete=True)
    return render(
        request, "licenses/translation_status.html", {"branches": branches}
    )


def branch_status_helper(repo, translation_branch):
    """
    Returns some of the context for the branch_status view.
    Mostly separated to help with test so we can readily
    mock the repo.
    """
    repo.remotes.origin.fetch()
    branch_name = translation_branch.branch_name

    # Put the commit data in a format that's easy for the template to use
    # Start by getting data about the last N + 1 commits
    last_n_commits = list(
        repo.iter_commits(f"origin/{branch_name}", max_count=1 + NUM_COMMITS)
    )

    # Copy the data we need into a list of dictionaries
    commits_for_template = [
        {
            "shorthash": c.hexsha[:7],
            "hexsha": c.hexsha,
            "message": c.message,
            "committed_datetime": c.committed_datetime,
            "committer": c.committer,
        }
        for c in last_n_commits
    ]

    # Add a little more data to most of them.
    for i, c in enumerate(commits_for_template):
        if i < NUM_COMMITS and (i + 1) < len(commits_for_template):
            c["previous"] = commits_for_template[i + 1]
    return {
        "official_git_branch": settings.OFFICIAL_GIT_BRANCH,
        "branch": translation_branch,
        "commits": commits_for_template[:NUM_COMMITS],
        "last_commit": commits_for_template[0]
        if commits_for_template
        else None,
    }


# using cache_page seems to break django-distill (weird error about invalid
# host "testserver"). Do our caching more directly.
# @cache_page(timeout=5 * 60, cache="branchstatuscache")
def branch_status(request, id):
    translation_branch = get_object_or_404(TranslationBranch, id=id)
    cache = caches["branchstatuscache"]
    cachekey = (
        f"{settings.TRANSLATION_REPOSITORY_DIRECTORY}-"
        f"{translation_branch.branch_name}"
    )
    result = cache.get(cachekey)
    if result is None:
        with git.Repo(settings.TRANSLATION_REPOSITORY_DIRECTORY) as repo:
            context = branch_status_helper(repo, translation_branch)
            result = render(
                request,
                "licenses/branch_status.html",
                context,
            )
        cache.set(cachekey, result, 5 * 60)
    return result


def metadata_view(request):
    data = [license.get_metadata() for license in License.objects.all()]
    yaml_bytes = yaml.dump(
        data, default_flow_style=False, encoding="utf-8", allow_unicode=True
    )
    return HttpResponse(
        yaml_bytes,
        content_type="text/yaml; charset=utf-8",
    )
