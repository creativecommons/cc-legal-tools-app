import re
from operator import itemgetter
from typing import Iterable

import git
from django.conf import settings
from django.core.cache import caches
from django.shortcuts import get_object_or_404, render
from django.utils.translation import get_language_info

from i18n import DEFAULT_LANGUAGE_CODE
from i18n.utils import active_translation, get_language_for_jurisdiction
from licenses.constants import INCLUDED_LICENSE_VERSIONS
from licenses.git_utils import setup_local_branch
from licenses.models import LegalCode, License, TranslationBranch

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


def home(request):
    # Get the list of license codes and languages that occur among the licenses
    # to let the template iterate over them as it likes.
    versions = reversed(sorted(INCLUDED_LICENSE_VERSIONS))
    licenses_by_version = []
    for version in versions:
        codes = (
            License.objects.filter(version=version)
            .order_by("license_code")
            .distinct("license_code")
            .values_list("license_code", flat=True)
        )
        languages = (
            LegalCode.objects.filter(license__version=version)
            .order_by("language_code")
            .distinct("language_code")
            .values_list("language_code", flat=True)
        )
        licenses_by_version.append((version, codes, languages))

    context = {
        "licenses_by_version": licenses_by_version,
        # "licenses_by_code": licenses_by_code,
        "legalcodes": LegalCode.objects.filter(license__version__in=versions).order_by(
            "license__license_code", "language_code"
        ),
    }
    return render(request, "home.html", context)


def get_languages_and_links_for_legalcodes(
    legalcodes: Iterable[LegalCode], selected_language_code: str, license_or_deed: str
):
    """
    license_or_deed should be "license" or "deed", controlling which kind of page we link to.
    """
    languages_and_links = [
        {
            "language_code": legal_code.language_code,
            # name_local: name of language in its own language
            "name_local": get_language_info(legal_code.language_code)["name_local"],
            "name_for_sorting": get_language_info(legal_code.language_code)[
                "name_local"
            ].lower(),
            "link": legal_code.license_url()
            if license_or_deed == "license"
            else legal_code.deed_url(),
            "selected": selected_language_code == legal_code.language_code,
        }
        for legal_code in legalcodes
    ]
    languages_and_links.sort(key=itemgetter("name_for_sorting"))
    return languages_and_links


def view_license(request, license_code, version, jurisdiction=None, language_code=None):
    if language_code is None and jurisdiction:
        language_code = get_language_for_jurisdiction(jurisdiction)
    language_code = language_code or DEFAULT_LANGUAGE_CODE

    legalcode = get_object_or_404(
        LegalCode,
        license__license_code=license_code,
        license__version=version,
        license__jurisdiction_code=jurisdiction or "",
        language_code=language_code,
    )

    languages_and_links = get_languages_and_links_for_legalcodes(
        legalcode.license.legal_codes.all(), language_code, "license"
    )

    translation = legalcode.get_translation_object()
    with active_translation(translation):
        return render(
            request,
            "legalcode_40_page.html",  # FIXME: Can we rename this to license.html or something?
            {
                "fat_code": legalcode.license.fat_code(),
                "languages_and_links": languages_and_links,
                "legalcode": legalcode,
                "license": legalcode.license,
            },
        )


def view_deed(request, license_code, version, jurisdiction=None, language_code=None):
    if language_code is None and jurisdiction:
        language_code = get_language_for_jurisdiction(jurisdiction)
    language_code = language_code or DEFAULT_LANGUAGE_CODE

    legalcode = get_object_or_404(
        LegalCode,
        license__license_code=license_code,
        license__version=version,
        license__jurisdiction_code=jurisdiction or "",
        language_code=language_code,
    )
    license = legalcode.license
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
    # repo.remotes.origin.fetch()  # Make sure we know about all the upstream branches
    # heads = repo.remotes.origin.refs
    # branches = [head.name[len("origin/") :] for head in heads]

    branches = TranslationBranch.objects.exclude(complete=True)
    return render(request, "licenses/translation_status.html", {"branches": branches})


def branch_status_helper(repo, translation_branch):
    """
    Returns some of the context for the branch_status view.
    Mostly separated to help with test so we can readily
    mock the repo.
    """
    branch_name = translation_branch.branch_name
    setup_local_branch(repo, branch_name, settings.OFFICIAL_GIT_BRANCH)

    # Put the commit data in a format that's easy for the template to use
    # Start by getting data about the last N + 1 commits
    last_n_commits = list(repo.iter_commits(branch_name, max_count=1 + NUM_COMMITS))

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
        "last_commit": commits_for_template[0] if commits_for_template else None,
    }


# using cache_page seems to break django-distill (weird error about invalid
# host "testserver"). Do our caching more directly.
# @cache_page(timeout=5 * 60, cache="branchstatuscache")
def branch_status(request, id):
    translation_branch = get_object_or_404(TranslationBranch, id=id)
    cache = caches["branchstatuscache"]
    cachekey = (
        f"{settings.TRANSLATION_REPOSITORY_DIRECTORY}-{translation_branch.branch_name}"
    )
    result = cache.get(cachekey)
    if result is None:
        with git.Repo(settings.TRANSLATION_REPOSITORY_DIRECTORY) as repo:
            context = branch_status_helper(repo, translation_branch)
            result = render(request, "licenses/branch_status.html", context,)
        cache.set(cachekey, result, 5 * 60)
    return result
