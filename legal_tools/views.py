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
from i18n import UNIT_NAMES
from i18n.utils import (
    active_translation,
    get_default_language_for_jurisdiction,
    get_jurisdiction_name,
    load_deeds_ux_translations,
    map_django_to_transifex_language_code,
)
from legal_tools.models import (
    UNITS_LICENSES,
    LegalCode,
    Tool,
    TranslationBranch,
)
from .rdf_generator import generate_rdf_triples

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
        category_title = translation.gettext("Public Domain")
    else:
        category_title = translation.gettext("Licenses")
    return category, category_title


def get_tool_title(tool):
    tool_name = UNIT_NAMES.get(tool.unit, "UNIMPLEMENTED")
    jurisdiction_name = get_jurisdiction_name(
        tool.category, tool.unit, tool.version, tool.jurisdiction_code
    )
    tool_title = f"{tool_name} {tool.version} {jurisdiction_name}"
    return tool_title


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
            # Translation incomplete, use English
            deed_rel_path = deed_rel_path.replace(
                f"deed.{language_code}", f"deed.{settings.LANGUAGE_CODE}"
            )
    return deed_rel_path


def get_legal_code_replaced_rel_path(
    tool,
    path_start,
    language_code,
    language_default,
):
    if not tool:
        return None, None, None
    try:
        # Same language
        legal_code = LegalCode.objects.valid().get(
            tool=tool,
            language_code=language_code,
        )
    except LegalCode.DoesNotExist:
        try:
            # Jurisdiction default language
            legal_code = LegalCode.objects.valid().get(
                tool=tool,
                language_code=language_default,
            )
        except LegalCode.DoesNotExist:
            # Global default language
            legal_code = LegalCode.objects.valid().get(
                tool=tool,
                language_code=settings.LANGUAGE_CODE,
            )
    replaced_title = legal_code.title
    replaced_deed_path = get_deed_rel_path(
        legal_code.deed_url,
        path_start,
        language_code,
        language_default,
    )
    replaced_legal_code_path = os.path.relpath(
        legal_code.legal_code_url, path_start
    )
    return replaced_title, replaced_deed_path, replaced_legal_code_path


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


def view_dev_index(request):
    # with git.Repo(settings.DATA_REPOSITORY_DIR) as repo:
    # # Make sure we know about all the upstream branches
    # repo.remotes.origin.fetch()
    # heads = repo.remotes.origin.refs
    # branches = [head.name[len("origin/") :] for head in heads]

    # Serve CC navigation header menu
    # Path: /?rest_route=/ccnavigation-header/menu
    if request.GET.get("rest_route"):  # pragma: no cover
        # Standard library
        import json

        ccnavigation_header_menu = [
            {
                "ID": 1,
                "url": "#",
                "title": "Who we are",
                "child_items": [
                    {"ID": 1, "url": "#", "title": "Item 1"},
                    {"ID": 2, "url": "#", "title": "Item 2"},
                    {"ID": 3, "url": "#", "title": "Item 3"},
                    {"ID": 4, "url": "#", "title": "Item 4"},
                    {"ID": 5, "url": "#", "title": "Item 5"},
                    {"ID": 6, "url": "#", "title": "Item 6"},
                    {"ID": 7, "url": "#", "title": "Item 7"},
                    {"ID": 8, "url": "#", "title": "Item 8"},
                    {"ID": 9, "url": "#", "title": "Item 9"},
                ],
            },
            {"ID": 2, "url": "#", "title": "What we do"},
            {
                "ID": 3,
                "url": "#",
                "title": "Licenses and tools",
                "child_items": [
                    {
                        "ID": 1,
                        "url": "/licenses/list",
                        "title": "Licenses List",
                    },
                    {
                        "ID": 2,
                        "url": "/publicdomain/list",
                        "title": "Public Domain List",
                    },
                ],
            },
            {"ID": 4, "url": "#", "title": "News"},
            {"ID": 4, "url": "#", "title": "Support Us"},
        ]

        return HttpResponse(
            json.dumps(ccnavigation_header_menu),
            content_type="application/json",
        )

    translation.activate(settings.LANGUAGE_CODE)
    distilling = request.GET.get("distilling", False)

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

    count_exceed = 0
    count_under = 0
    count_zero = 0
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
        if language_data["percent_translated"] == 0:  # pragma: no cover
            count_zero += 1
        elif (
            language_data["percent_translated"]
            < settings.TRANSLATION_THRESHOLD
        ):
            count_under += 1
        else:
            count_exceed += 1

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
        template_name="dev/index.html",
        context={
            "branches": branches,
            "category": "dev",
            "category_title": "Dev",
            "distilling": distilling,
            "deed_ux": deed_ux_translation_info,
            "threshold": settings.TRANSLATION_THRESHOLD,
            "count_exceed": count_exceed,
            "count_under": count_under,
            "count_zero": count_zero,
        },
    )

    html_response.content = bytes(
        BeautifulSoup(html_response.content, features="lxml").prettify(),
        "utf-8",
    )
    return html_response


def view_list(request, category, language_code=None):
    """
    Display all the available deeds and legal code for the given category.
    """
    request.path, language_code = normalize_path_and_lang(
        request.path, None, language_code
    )
    if language_code not in settings.LANGUAGES_MOSTLY_TRANSLATED:
        raise Http404(f"invalid language: {language_code}")
    translation.activate(language_code)
    # Get the list of units and languages that occur among the tools
    # to let the template iterate over them as it likes.
    legal_code_objects = (
        LegalCode.objects.valid()
        .filter(tool__category=category)
        .select_related("tool")
        .order_by(
            "-tool__version",
            "tool__jurisdiction_code",
            "language_code",
            "tool__unit",
        )
    )
    tools = []
    path_start = os.path.dirname(request.path)
    for lc in legal_code_objects:
        lc_category = lc.tool.category
        lc_unit = lc.tool.unit
        lc_version = lc.tool.version
        lc_identifier = lc.tool.identifier()
        lc_language_default = get_default_language_for_jurisdiction(
            lc.tool.jurisdiction_code,
        )
        lc_lang_code = lc.language_code
        jurisdiction_name = get_jurisdiction_name(
            lc_category,
            lc_unit,
            lc_version,
            lc.tool.jurisdiction_code,
        )
        jurisdiction_sort = (  # ensure unported is first
            "" if not lc.tool.jurisdiction_code else jurisdiction_name
        )
        deed_rel_path = get_deed_rel_path(
            lc.deed_url,
            path_start,
            lc.language_code,
            lc_language_default,
        )
        deed_translated = deed_rel_path.endswith(f".{lc_lang_code}")
        language_name = translation.get_language_info(lc_lang_code)[
            "name_local"
        ]

        data = dict(
            version=lc_version,
            jurisdiction_name=jurisdiction_name,
            jurisdiction_sort=jurisdiction_sort,
            unit=lc_unit,
            language_code=lc_lang_code,
            language_name=language_name,
            language_sort=language_name.lower(),
            deed_only=lc.tool.deed_only,
            deed_translated=deed_translated,
            deed_url=deed_rel_path,
            legal_code_url=os.path.relpath(
                lc.legal_code_url, start=path_start
            ),
            identifier=lc_identifier,
        )
        tools.append(data)
    category, category_title = get_category_and_category_title(
        category,
        None,
    )
    if category == "licenses":
        category_list = translation.gettext("Licenses List")
    else:
        category_list = translation.gettext("Public Domain List")

    languages_and_links = get_languages_and_links_for_deeds_ux(
        request_path=request.path,
        selected_language_code=language_code,
    )
    html_response = render(
        request,
        template_name=f"list-{category}.html",
        context={
            "canonical_url": f"{settings.CANONICAL_SITE}{request.path}",
            "category": category,
            "category_title": category_title,
            "category_list": category_list,
            "languages_and_links": languages_and_links,
            "tools": tools,
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
    translation.activate(language_code)

    path_start = os.path.dirname(request.path)
    language_default = get_default_language_for_jurisdiction(jurisdiction)

    try:
        # Try to load legal code with specified language
        legal_code = LegalCode.objects.filter(
            tool__unit=unit,
            tool__version=version,
            tool__jurisdiction_code=jurisdiction,
            language_code=language_code,
        )[0]
    except IndexError:
        # Else load legal code with default language
        legal_code = LegalCode.objects.filter(
            tool__unit=unit,
            tool__version=version,
            tool__jurisdiction_code=jurisdiction,
            language_code=language_default,
        )[0]
    legal_code_rel_path = os.path.relpath(
        legal_code.legal_code_url, path_start
    )

    tool = legal_code.tool
    tool_title = get_tool_title(tool)

    category, category_title = get_category_and_category_title(
        category,
        tool,
    )
    languages_and_links = get_languages_and_links_for_deeds_ux(
        request_path=request.path,
        selected_language_code=language_code,
    )

    replaced_title, replaced_path, _ = get_legal_code_replaced_rel_path(
        tool.is_replaced_by,
        path_start,
        language_code,
        language_default,
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

    html_response = render(
        request,
        template_name="deed.html",
        context={
            "additional_classes": "",
            "body_template": body_template,
            "canonical_url": f"{settings.CANONICAL_SITE}{request.path}",
            "category": category,
            "category_title": category_title,
            "identifier": tool.identifier(),
            "languages_and_links": languages_and_links,
            "legal_code_rel_path": legal_code_rel_path,
            "replaced_path": replaced_path,
            "replaced_title": replaced_title,
            "tool": tool,
            "tool_title": tool_title,
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
    language_default = get_default_language_for_jurisdiction(jurisdiction)

    path_start = os.path.dirname(request.path)

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

    # Use Deeds & UX translations for title instead of Legal Code
    if language_code in settings.LANGUAGES_MOSTLY_TRANSLATED:
        translation.activate(language_code)
    elif language_default in settings.LANGUAGES_MOSTLY_TRANSLATED:
        translation.activate(language_default)
    else:
        translation.activate(settings.LANGUAGE_CODE)
    tool = legal_code.tool
    tool_title = get_tool_title(tool)

    # Activate Legal Code translation
    current_translation = legal_code.get_translation_object()
    with active_translation(current_translation):
        category, category_title = get_category_and_category_title(
            category,
            tool,
        )

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

        replaced_title, _, replaced_path = get_legal_code_replaced_rel_path(
            tool.is_replaced_by,
            path_start,
            language_code,
            language_default,
        )

        kwargs = dict(
            template_name="legalcode.html",
            context={
                "canonical_url": f"{settings.CANONICAL_SITE}{request.path}",
                "category": category,
                "category_title": category_title,
                "deed_rel_path": deed_rel_path,
                "identifier": tool.identifier(),
                "languages_and_links": languages_and_links,
                "legal_code": legal_code,
                "replaced_path": replaced_path,
                "replaced_title": replaced_title,
                "tool": tool,
                "tool_title": tool_title,
            },
        )

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


def view_page_not_found(request, exception, template_name="dev/404.html"):
    return render(
        request,
        template_name=template_name,
        context={
            "category": "error_404",
            "category_title": "Error",
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


def view_generate_rdf(request, unit, version, jurisdiction=None):
    rdf_content = generate_rdf_triples(unit, version, jurisdiction)
    serialized_rdf_content = rdf_content.serialize(format="pretty-xml").strip(
        "utf-8"
    )

    response = HttpResponse(
        serialized_rdf_content, content_type="application/rdf+xml"
    )
    return response
