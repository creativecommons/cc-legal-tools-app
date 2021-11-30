# Standard library
import os.path
import re
from operator import itemgetter
from typing import Iterable

# Third-party
import git
import yaml
from bs4 import BeautifulSoup
from django.conf import settings
from django.core.cache import caches
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, render
from django.template.loader import render_to_string
from django.utils import translation

# First-party/Local
from i18n.utils import (
    active_translation,
    get_default_language_for_jurisdiction,
    get_jurisdiction_name,
    load_deeds_ux_translations,
    map_django_to_transifex_language_code,
)
from legal_tools.models import (
    UNITS_LICENSES,
    UNITS_PUBLIC_DOMAIN,
    LegalCode,
    Tool,
    TranslationBranch,
)

NUM_COMMITS = 3

# For removing the deed.foo section of a deed url
REMOVE_DEED_URL_RE = re.compile(r"^(.*?/)(?:deed)?(?:\..*)?$")


def get_category_and_category_title(category=None, tool=None):
    # category
    if not category:
        if tool:
            category = tool.category
        else:
            category = "licenses"
    # category_title
    if category == "publicdomain":
        category_title = "Public Domain"
    else:
        category_title = category.title()
    return category, category_title


def get_languages_and_links_for_deeds_ux(request_path, selected_language_code):
    languages_and_links = []

    for language_code in settings.LANGUAGES_MOSTLY_TRANSLATED:
        language_info = translation.get_language_info(language_code)
        link = request_path.replace(
            f".{selected_language_code}",
            f".{language_code}",
        )
        languages_and_links.append(
            {
                "cc_language_code": language_code,
                "name_local": language_info["name_local"],
                "name_for_sorting": language_info["name_local"].lower(),
                "link": link,
                "selected": selected_language_code == language_code,
            }
        )
    languages_and_links.sort(key=itemgetter("name_for_sorting"))
    return languages_and_links


def get_legal_code_rel_path(
    legal_code_url,
    path_start,
    language_code,
    language_default,
    legal_code_languages,
):
    legal_code_rel_path = os.path.relpath(legal_code_url, path_start)
    if language_code not in legal_code_languages:
        legal_code_rel_path = legal_code_rel_path.replace(
            f"legalcode.{language_code}",
            f"legalcode.{language_default}",
        )

    return legal_code_rel_path


def get_languages_and_links_for_legal_codes(
    path_start,
    legal_codes: Iterable[LegalCode],
    selected_language_code: str,
):
    """
    legal_code_or_deed should be "deed" or "legal code", controlling which kind
    of page we link to.

    selected_language_code is a Django language code (lowercase IETF language
    tag)
    """
    languages_and_links = [
        {
            "cc_language_code": legal_code.language_code,
            # name_local: name of language in its own language
            "name_local": name_local(legal_code),
            "name_for_sorting": name_local(legal_code).lower(),
            "link": os.path.relpath(
                legal_code.legal_code_url, start=path_start
            ),
            "selected": selected_language_code == legal_code.language_code,
        }
        for legal_code in legal_codes
    ]
    languages_and_links.sort(key=itemgetter("name_for_sorting"))
    if len(languages_and_links) < 2:
        # Return an empty list if there are not multiple languages available
        # (this will result in the language dropdown not being shown with a
        # single currently active language)
        languages_and_links = None
    return languages_and_links


def get_deed_rel_path(
    deed_url,
    path_start,
    language_code,
    language_default,
):
    deed_rel_path = os.path.relpath(deed_url, path_start)
    if language_code not in settings.LANGUAGES_MOSTLY_TRANSLATED:
        if language_default in settings.LANGUAGES_MOSTLY_TRANSLATED:
            # Translation incomplete, use region default language
            deed_rel_path = deed_rel_path.replace(
                f"deed.{language_code}", f"deed.{language_default}"
            )
        else:
            # Translation incomplete, use Englishi
            deed_rel_path = deed_rel_path.replace(
                f"deed.{language_code}", f"deed.{settings.LANGUAGE_CODE}"
            )
    return deed_rel_path


def name_local(legal_code):
    return translation.get_language_info(legal_code.language_code)[
        "name_local"
    ]


def normalize_path_and_lang(request_path, jurisdiction, language_code):
    if not language_code:
        language_code = get_default_language_for_jurisdiction(
            jurisdiction, settings.LANGUAGE_CODE
        )
    if not request_path.endswith(f".{language_code}"):
        request_path = f"{request_path}.{language_code}"
    return request_path, language_code


def view_dev_home(request, category=None):
    """
    For test purposes, this displays all the available deeds and legal code in
    tables. This is not intended for public use and should not be included in
    the generation of static files.
    """
    # Get the list of units and languages that occur among the tools
    # to let the template iterate over them as it likes.
    legal_code_objects = (
        LegalCode.objects.valid()
        .select_related("tool")
        .order_by(
            "-tool__version",
            "tool__jurisdiction_code",
            "language_code",
            "tool__unit",
        )
    )
    licenses = []
    publicdomain = []
    path_start = os.path.dirname(request.path)
    for lc in legal_code_objects:
        lc_category = lc.tool.category
        lc_unit = lc.tool.unit
        lc_version = lc.tool.version
        lc_language_default = get_default_language_for_jurisdiction(
            lc.tool.jurisdiction_code,
        )
        jurisdiction_name = get_jurisdiction_name(
            lc_category,
            lc_unit,
            lc_version,
            lc.tool.jurisdiction_code,
        )
        deed_rel_path = get_deed_rel_path(
            lc.deed_url,
            path_start,
            lc.language_code,
            lc_language_default,
        )
        deed_translated = deed_rel_path.endswith(f".{lc.language_code}")
        data = dict(
            version=lc_version,
            jurisdiction_name=jurisdiction_name,
            unit=lc_unit,
            language_code=lc.language_code,
            deed_only=lc.tool.deed_only,
            deed_translated=deed_translated,
            deed_url=deed_rel_path,
            legal_code_url=os.path.relpath(
                lc.legal_code_url, start=path_start
            ),
            identifier=lc.tool.identifier(),
        )
        if lc_category == "licenses":
            licenses.append(data)
        else:
            publicdomain.append(data)
    licenses = sorted(licenses, reverse=True, key=itemgetter("version"))
    publicdomain = sorted(publicdomain, key=itemgetter("identifier"))

    html_response = render(
        request,
        template_name="dev/home.html",
        context={
            "category": "dev",
            "category_title": "Dev",
            "licenses": licenses,
            "publicdomain": publicdomain,
            "units": sorted(UNITS_PUBLIC_DOMAIN + UNITS_LICENSES),
        },
    )
    html_response.content = bytes(
        BeautifulSoup(html_response.content, features="lxml").prettify(),
        "utf-8",
    )
    return html_response


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
    if language_code not in settings.LANGUAGES_MOSTLY_TRANSLATED:
        raise Http404(f"invalid language: {language_code}")

    path_start = os.path.dirname(request.path)
    language_default = get_default_language_for_jurisdiction(jurisdiction)

    # The Legal Code translations are specific.
    #
    # The Deed translations are generic: all of the Deeds of a given unit share
    # the same text. Therefore, for the purpose of displaying the Deed, we do
    # not care about the language of the associated Legal Code. Instead we care
    # only about the languages that have been mostly (>TRANSLATION_THRESHOLD)
    # translated.
    #
    # Initially set legal_code based on language_default.
    legal_code = LegalCode.objects.filter(
        tool__unit=unit,
        tool__version=version,
        tool__jurisdiction_code=jurisdiction,
        language_code=language_default,
    )[0]
    legal_code_languages = []
    for possible_legal_code in LegalCode.objects.filter(
        tool__unit=unit,
        tool__version=version,
        tool__jurisdiction_code=jurisdiction,
    ):
        legal_code_languages.append(possible_legal_code.language_code)
    if (
        language_code != language_default
        and language_code in legal_code_languages
    ):
        legal_code = LegalCode.objects.filter(
            tool__unit=unit,
            tool__version=version,
            tool__jurisdiction_code=jurisdiction,
            language_code=language_code,
        )[0]

    tool = legal_code.tool
    category, category_title = get_category_and_category_title(
        category,
        tool,
    )
    languages_and_links = get_languages_and_links_for_deeds_ux(
        request_path=request.path,
        selected_language_code=language_code,
    )

    legal_code_rel_path = get_legal_code_rel_path(
        legal_code.legal_code_url,
        path_start,
        language_code,
        language_default,
        legal_code_languages,
    )

    if tool.unit in UNITS_LICENSES:
        body_template = "includes/deed_body_licenses.html"
    elif tool.unit == "zero":
        body_template = "includes/deed_body_zero.html"
    elif tool.unit == "mark":
        body_template = "includes/deed_body_mark.html"
    elif tool.unit == "certification":
        body_template = "includes/deed_body_certification.html"
    else:
        body_template = "includes/deed_body_unimplemented.html"

    translation.activate(language_code)
    html_response = render(
        request,
        template_name="deed.html",
        context={
            "additional_classes": "",
            "body_template": body_template,
            "category": category,
            "category_title": category_title,
            "identifier": tool.identifier(),
            "languages_and_links": languages_and_links,
            "legal_code": legal_code,
            "legal_code_rel_path": legal_code_rel_path,
            "tool": tool,
        },
    )
    html_response.content = bytes(
        BeautifulSoup(html_response.content, features="lxml").prettify(),
        "utf-8",
    )
    return html_response


def view_legal_code(
    request,
    unit,
    version,
    category=None,
    jurisdiction=None,
    language_code=None,
    is_plain_text=False,
):
    request.path, language_code = normalize_path_and_lang(
        request.path, jurisdiction, language_code
    )
    path_start = os.path.dirname(request.path)
    language_default = get_default_language_for_jurisdiction(jurisdiction)
    # NOTE: plaintext functionality disabled
    # if is_plain_text:
    #     legal_code = get_object_or_404(
    #         LegalCode,
    #         plain_text_url=request.path,
    #     )
    # else:
    #     legal_code = get_object_or_404(
    #         LegalCode,
    #         legal_code_url=request.path,
    #     )
    legal_code = get_object_or_404(
        LegalCode,
        legal_code_url=request.path,
    )

    tool = legal_code.tool
    category, category_title = get_category_and_category_title(
        category,
        tool,
    )

    language_code = legal_code.language_code  # CC language code
    languages_and_links = get_languages_and_links_for_legal_codes(
        path_start=path_start,
        legal_codes=tool.legal_codes.all(),
        selected_language_code=language_code,
    )

    deed_rel_path = get_deed_rel_path(
        legal_code.deed_url,
        path_start,
        language_code,
        language_default,
    )

    kwargs = dict(
        template_name="legalcode.html",
        context={
            "category": category,
            "category_title": category_title,
            "deed_rel_path": deed_rel_path,
            "identifier": tool.identifier(),
            "languages_and_links": languages_and_links,
            "legal_code": legal_code,
            "tool": tool,
        },
    )

    current_translation = legal_code.get_translation_object()
    with active_translation(current_translation):
        # NOTE: plaintext functionality disabled
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
        #
        html_response = render(request, **kwargs)
        html_response.content = bytes(
            BeautifulSoup(html_response.content, features="lxml").prettify(),
            "utf-8",
        )
        return html_response


def view_translation_status(request):
    # with git.Repo(settings.DATA_REPOSITORY_DIR) as repo:
    # # Make sure we know about all the upstream branches
    # repo.remotes.origin.fetch()
    # heads = repo.remotes.origin.refs
    # branches = [head.name[len("origin/") :] for head in heads]

    # ensure translation status is current
    load_deeds_ux_translations()

    branches = TranslationBranch.objects.exclude(complete=True)

    legal_code_objects = (
        LegalCode.objects.valid()
        .select_related("tool")
        .order_by(
            "language_code",
        )
    )
    legal_code_langauge_codes = [lc.language_code for lc in legal_code_objects]
    legal_code_langauge_codes = sorted(list(set(legal_code_langauge_codes)))

    deed_ux_translation_info = {}
    locale_dir = os.path.join(settings.DATA_REPOSITORY_DIR, "locale")
    locale_dir = os.path.abspath(os.path.realpath(locale_dir))

    for language_code, language_data in settings.DEEDS_UX_PO_FILE_INFO.items():
        if language_code == settings.LANGUAGE_CODE:
            continue
        try:
            language_info = translation.get_language_info(language_code)
            bidi = language_info["bidi"]
            name = language_info["name"]
            name_local = language_info["name_local"]
        except KeyError:  # pragma: no cover
            name = '<em style="color:red;">Unknown</em>'
        legal_code = False
        if language_code in legal_code_langauge_codes:
            legal_code = True
        transifex_code = map_django_to_transifex_language_code(language_code)
        date_format = "%Y-%m-%d %H:%M"
        created = ""
        if language_data["creation_date"] is not None:  # pragma: no cover
            created = language_data["creation_date"].strftime(date_format)
        updated = ""
        if language_data["revision_date"] is not None:  # pragma: no cover
            updated = language_data["creation_date"].strftime(date_format)

        deed_ux_translation_info[language_code] = {
            "locale_name": translation.to_locale(language_code),
            "name": name,
            "name_local": name_local,
            "bidi": bidi,
            "percent_translated": language_data["percent_translated"],
            "created": created,
            "updated": updated,
            "legal_code": legal_code,
            "transifex_code": transifex_code,
        }

    html_response = render(
        request,
        template_name="dev/translation_status.html",
        context={
            "branches": branches,
            "category": "dev",
            "category_title": "Dev",
            "deed_ux": deed_ux_translation_info,
            "threshold": settings.TRANSLATION_THRESHOLD,
        },
    )
    html_response.content = bytes(
        BeautifulSoup(html_response.content, features="lxml").prettify(),
        "utf-8",
    )
    return html_response


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
            "committed_datetime": c.committed_datetime,
            "committer": c.committer,
            "hexsha": c.hexsha,
            "message": c.message,
            "shorthash": c.hexsha[:7],
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
    html_response = cache.get(cachekey)
    if html_response is None:
        with git.Repo(settings.DATA_REPOSITORY_DIR) as repo:
            context = branch_status_helper(repo, translation_branch)
            html_response = render(
                request,
                "dev/branch_status.html",
                context,
            )
            html_response.content = bytes(
                BeautifulSoup(
                    html_response.content, features="lxml"
                ).prettify(),
                "utf-8",
            )
        cache.set(cachekey, html_response, 5 * 60)
    return html_response


def view_metadata(request):
    data = {"licenses": [], "publicdomain": []}
    for tool in Tool.objects.all():
        category = tool.category
        data[category].append({f"{tool.resource_slug}": tool.get_metadata()})
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


def render_redirect(title, destination, language_code):
    translation.activate(language_code)
    html_content = render_to_string(
        "redirect.html",
        context={"title": title, "destination": destination},
    )
    html_content = bytes(
        BeautifulSoup(html_content, features="lxml").prettify(),
        "utf-8",
    )
    return html_content
