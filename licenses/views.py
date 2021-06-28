# Standard library
import re
from operator import itemgetter
from typing import Iterable

# Third-party
import git
import yaml
from django.conf import settings
from django.core.cache import caches
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render
from django.utils.translation import get_language_info

# First-party/Local
from i18n import DEFAULT_LANGUAGE_CODE, JURISDICTION_NAMES
from i18n.utils import (
    active_translation,
    cc_to_django_language_code,
    get_default_language_for_jurisdiction,
)
from licenses.models import (
    UNITS_LICENSES,
    UNITS_PUBLIC_DOMAIN,
    LegalCode,
    License,
    TranslationBranch,
)

# DEED_TEMPLATE_MAPPING is currently only used by tests
DEED_TEMPLATE_MAPPING = {
    # unit : template name
    "sampling": "licenses/sampling_deed.html",  # ......... DISABLED
    "sampling+": "licenses/sampling_deed.html",  # ........ DISABLED
    "nc-sampling+": "licenses/sampling_deed.html",  # ..... DISABLED
    "devnations": "licenses/devnations_deed.html",  # ..... DISABLED
    "CC0": "licenses/zero_deed.html",  # .................. DISABLED
    "mark": "licenses/pdmark_deed.html",  # ............... DISABLED
    "publicdomain": "licenses/publicdomain_deed.html",  # . DISABLED
    # others use "licenses/standard_deed.html",  # ........ DISABLED
}

NUM_COMMITS = 3

# For removing the deed.foo section of a deed url
REMOVE_DEED_URL_RE = re.compile(r"^(.*?/)(?:deed)?(?:\..*)?$")


def get_category_and_category_title(category=None, license=None):
    # category
    if not category:
        if license:
            category = license.category
        else:
            category = "licenses"
    # category_title
    if category == "publicdomain":
        category_title = "Public Domain"
    else:
        category_title = category.title()
    return category, category_title


def view_dev_home(request, category=None):
    """
    For test purposes, this displays all the available deeds and licenses in
    tables. This is not intended for public use and should not be included in
    the generation of static files.
    """

    # Get the list of units and languages that occur among the licenses
    # to let the template iterate over them as it likes.
    legalcode_objects = (
        LegalCode.objects.valid()
        .select_related("license")
        .order_by(
            "-license__version",
            "license__jurisdiction_code",
            "language_code",
            "license__unit",
        )
    )
    licenses = []
    publicdomain = []
    for lc in legalcode_objects:
        lc_category = lc.license.category
        version = lc.license.version
        jurisdiction = JURISDICTION_NAMES.get(
            lc.license.jurisdiction_code, lc.license.jurisdiction_code
        )
        # For details on nomenclature for unported licenses, see:
        # https://wiki.creativecommons.org/wiki/License_Versions
        if lc.license.unit == "CC0":
            jurisdiction = "Universal"
        elif lc_category == "licenses" and jurisdiction.lower() == "unported":
            if version == "4.0":
                jurisdiction = "International"
            elif version == "3.0":
                jurisdiction = "International (unported)"
            else:
                jurisdiction = "Generic (unported)"
        data = dict(
            version=version,
            jurisdiction=jurisdiction,
            unit=lc.license.unit,
            language_code=lc.language_code,
            deed_url=lc.deed_url,
            license_url=lc.license_url,
        )
        if lc_category == "licenses":
            licenses.append(data)
        else:
            publicdomain.append(data)

    return render(
        request,
        "dev_home.html",
        {
            "category": "dev",
            "category_title": "Dev",
            "units": sorted(UNITS_PUBLIC_DOMAIN + UNITS_LICENSES),
            "licenses": licenses,
            "publicdomain": publicdomain,
        },
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

    selected_language_code is a CC language code (RFC 5646 language tag)
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


def normalize_path_and_lang(request_path, jurisdiction, language_code):
    if not language_code:
        language_code = get_default_language_for_jurisdiction(
            jurisdiction, DEFAULT_LANGUAGE_CODE
        )
    if not request_path.endswith(f".{language_code}"):
        request_path = f"{request_path}.{language_code}"
    return request_path, language_code


def view_license(
    request,
    unit,
    version,
    category=None,
    jurisdiction=None,
    language_code=None,  # CC language code
    is_plain_text=False,
):
    request.path, language_code = normalize_path_and_lang(
        request.path, jurisdiction, language_code
    )
    # Plaintext disabled
    # if is_plain_text:
    #     legalcode = get_object_or_404(
    #         LegalCode,
    #         plain_text_url=request.path,
    #     )
    # else:
    #     legalcode = get_object_or_404(
    #         LegalCode,
    #         license_url=request.path,
    #     )
    legalcode = get_object_or_404(
        LegalCode,
        license_url=request.path,
    )

    license = legalcode.license
    category, category_title = get_category_and_category_title(
        category,
        license,
    )

    language_code = legalcode.language_code  # CC language code
    languages_and_links = get_languages_and_links_for_legalcodes(
        legalcode.license.legal_codes.all(), language_code, "license"
    )

    kwargs = dict(
        template_name="legalcode_page.html",
        context={
            "category": category,
            "category_title": category_title,
            "fat_code": legalcode.license.fat_code(),
            "languages_and_links": languages_and_links,
            "legalcode": legalcode,
            "license": license,
        },
    )

    translation = legalcode.get_translation_object()
    with active_translation(translation):
        # if is_plain_text:
        #     response = HttpResponse(
        #         content_type='text/plain; charset="utf-8"'
        #     )
        #     html = render_to_string(**kwargs)
        #     soup = BeautifulSoup(html, "lxml")
        #     plain_text_soup = soup.find(id="plain-text-marker")
        #     # FIXME: prune the "img" tags from this before saving again.
        #     with tempfile.NamedTemporaryFile(mode="w+b") as temp:
        #         temp.write(plain_text_soup.encode("utf-8"))
        #         output = subprocess.run(
        #             [
        #                 "pandoc",
        #                 "-f",
        #                 "html",
        #                 temp.name,
        #                 "-t",
        #                 "plain",
        #             ],
        #             encoding="utf-8",
        #             capture_output=True,
        #         )
        #         response.write(output.stdout)
        #         return response

        return render(request, **kwargs)


def view_deed(
    request,
    unit,
    version,
    category=None,
    jurisdiction=None,
    language_code=None,
):
    request.path, language_code = normalize_path_and_lang(
        request.path, jurisdiction, language_code
    )
    legalcode = get_object_or_404(
        LegalCode,
        deed_url=request.path,
    )
    license = legalcode.license
    category, category_title = get_category_and_category_title(
        category,
        license,
    )
    language_code = legalcode.language_code  # CC language code
    languages_and_links = get_languages_and_links_for_legalcodes(
        license.legal_codes.all(), language_code, "deed"
    )

    if license.unit == "CC0":
        body_template = "includes/deed_cc0_body.html"
    elif license.unit in UNITS_LICENSES and license.version == "4.0":
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
                "category": category,
                "category_title": category_title,
                "fat_code": license.fat_code(),
                "languages_and_links": languages_and_links,
                "legalcode": legalcode,
                "license": license,
            },
        )


def view_translation_status(request):
    # with git.Repo(settings.DATA_REPOSITORY_DIR) as repo:
    # # Make sure we know about all the upstream branches
    # repo.remotes.origin.fetch()
    # heads = repo.remotes.origin.refs
    # branches = [head.name[len("origin/") :] for head in heads]

    branches = TranslationBranch.objects.exclude(complete=True)
    return render(
        request,
        template_name="licenses/translation_status.html",
        context={
            "category": "dev",
            "category_title": "Dev",
            "branches": branches,
        },
    )


def branch_status_helper(repo, translation_branch):
    """
    Returns some of the context for the branch_status view. Mostly separated
    to help with test so we can readily mock the repo.
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
def view_branch_status(request, id):
    translation_branch = get_object_or_404(TranslationBranch, id=id)
    cache = caches["branchstatuscache"]
    cachekey = (
        f"{settings.DATA_REPOSITORY_DIR}-{translation_branch.branch_name}"
    )
    result = cache.get(cachekey)
    if result is None:
        with git.Repo(settings.DATA_REPOSITORY_DIR) as repo:
            context = branch_status_helper(repo, translation_branch)
            result = render(
                request,
                "licenses/branch_status.html",
                context,
            )
        cache.set(cachekey, result, 5 * 60)
    return result


def view_metadata(request):
    data = [license.get_metadata() for license in License.objects.all()]
    yaml_bytes = yaml.dump(
        data, default_flow_style=False, encoding="utf-8", allow_unicode=True
    )
    return HttpResponse(
        yaml_bytes,
        content_type="text/yaml; charset=utf-8",
    )


def view_page_not_found(request, exception, template_name="404.html"):
    return render(
        request,
        template_name=template_name,
        context={
            "category": "dev",
            "category_title": "Dev",
        },
        status=404,
    )
