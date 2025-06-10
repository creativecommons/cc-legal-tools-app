# Standard library
import os
import re
from operator import itemgetter
from typing import Iterable

# Third-party
import yaml
from bs4 import BeautifulSoup
from bs4.dammit import EntitySubstitution
from bs4.formatter import HTMLFormatter
from django.conf import settings
from django.core.cache import cache
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, render
from django.template.loader import render_to_string
from django.utils import translation

# First-party/Local
from i18n.utils import (
    active_translation,
    get_default_language_for_jurisdiction_deed_ux,
    get_default_language_for_jurisdiction_legal_code,
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
from legal_tools.rdf_utils import (
    generate_images_rdf,
    generate_legal_code_rdf,
    order_rdf_xml,
)
from legal_tools.utils import get_tool_title

NUM_COMMITS = 3
PLAIN_TEXT_TOOL_IDENTIFIERS = [
    "CC BY 3.0",
    "CC BY-NC 3.0",
    "CC BY-NC-ND 3.0",
    "CC BY-NC-SA 3.0",
    "CC BY-ND 3.0",
    "CC BY-SA 3.0",
    "CC BY 4.0",
    "CC BY-NC 4.0",
    "CC BY-NC-ND 4.0",
    "CC BY-NC-SA 4.0",
    "CC BY-ND 4.0",
    "CC BY-SA 4.0",
    "CC0 1.0",
]

# For removing the deed.foo section of a deed url
REMOVE_DEED_URL_RE = re.compile(r"^(.*?/)(?:deed)?(?:\..*)?$")
# Register a custom BeatifulSoup HTML Formatter
HTMLFormatter.REGISTRY["html5ish"] = HTMLFormatter(
    # The html5 formatter replaces accented characters with entities, which
    # significantly alters translations and breaks tests. This custom
    # formatter uses the same EntitySubstitution as the minimal formatter
    # and the html5 values for the other parameters.
    entity_substitution=EntitySubstitution.substitute_xml,
    void_element_close_prefix=None,
    empty_attributes_are_booleans=True,
)


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


def get_languages_and_links_for_deeds_ux(request_path, selected_language_code):
    languages_and_links = []

    for language_code in settings.LANGUAGES_AVAILABLE_DEEDS_UX:
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
    if language_code not in settings.LANGUAGES_AVAILABLE_DEEDS_UX:
        if language_default in settings.LANGUAGES_AVAILABLE_DEEDS_UX:
            # Translation incomplete, use region default language
            deed_rel_path = deed_rel_path.replace(
                f"deed.{language_code}", f"deed.{language_default}"
            )
        else:
            # Translation incomplete, use app default language (English)
            deed_rel_path = deed_rel_path.replace(
                f"deed.{language_code}", f"deed.{settings.LANGUAGE_CODE}"
            )
    return deed_rel_path


def get_list_paths(language_code, language_default):
    paths = [
        f"/licenses/list.{language_code}",
        f"/publicdomain/list.{language_code}",
    ]
    for index, path in enumerate(paths):
        if language_code not in settings.LANGUAGES_AVAILABLE_DEEDS_UX:
            if language_default in settings.LANGUAGES_AVAILABLE_DEEDS_UX:
                # Translation incomplete, use region default language
                paths[index] = path.replace(
                    f"/list.{language_code}", f"/list.{language_default}"
                )
            else:
                # Translation incomplete, use app default language (English)
                paths[index] = path.replace(
                    f"/list.{language_code}", f"/list.{settings.LANGUAGE_CODE}"
                )
    return paths


def get_legal_code_replaced_rel_path(
    tool,
    path_start,
    language_code,
    language_default,
):
    if not tool:
        return None, None, None, None
    try:
        # Same language
        legal_code = LegalCode.objects.valid().get(
            tool=tool, language_code=language_code
        )
    except LegalCode.DoesNotExist:
        try:
            # Jurisdiction default language
            legal_code = LegalCode.objects.valid().get(
                tool=tool, language_code=language_default
            )
        except LegalCode.DoesNotExist:
            # Global default language
            legal_code = LegalCode.objects.valid().get(
                tool=tool, language_code=settings.LANGUAGE_CODE
            )
    title = get_tool_title(
        tool.unit,
        tool.version,
        tool.category,
        tool.jurisdiction_code,
        legal_code.language_code,
    )
    prefix = (
        f"{tool.unit}-{tool.version}-"
        f"{tool.jurisdiction_code}-{legal_code.language_code}-"
    )
    replaced_deed_title = cache.get(f"{prefix}replaced_deed_title", "")
    if not replaced_deed_title:
        with translation.override(legal_code.language_code):
            deed_str = translation.gettext("Deed")
        replaced_deed_title = f"{deed_str} - {title}"
        cache.add(f"{prefix}replaced_deed_title", replaced_deed_title)
    replaced_deed_path = get_deed_rel_path(
        legal_code.deed_url,
        path_start,
        language_code,
        language_default,
    )
    replaced_legal_code_title = cache.get(
        f"{prefix}replaced_legal_code_title", ""
    )
    if not replaced_legal_code_title:
        with translation.override(legal_code.language_code):
            legal_code_str = translation.gettext("Legal Code")
        replaced_legal_code_title = f"{legal_code_str} - {title}"
        cache.add(
            f"{prefix}replaced_legal_code_title", replaced_legal_code_title
        )
    replaced_legal_code_path = os.path.relpath(
        legal_code.legal_code_url, path_start
    )
    return (
        replaced_deed_title,
        replaced_deed_path,
        replaced_legal_code_title,
        replaced_legal_code_path,
    )


def name_local(legal_code):
    return translation.get_language_info(legal_code.language_code)[
        "name_local"
    ]


def normalize_path_and_lang(request_path, jurisdiction, language_code):
    if not language_code:
        if "legalcode" in request_path:
            language_code = get_default_language_for_jurisdiction_legal_code(
                jurisdiction
            )
        else:
            language_code = get_default_language_for_jurisdiction_legal_code(
                jurisdiction
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
        BeautifulSoup(html_response.content, features="lxml").prettify(
            formatter="html5ish"
        ),
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
    if language_code not in settings.LANGUAGES_AVAILABLE_DEEDS_UX:
        raise Http404(f"invalid language: {language_code}")

    translation.activate(language_code)

    list_licenses, list_publicdomain = get_list_paths(language_code, None)
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
        lc_language_default = get_default_language_for_jurisdiction_legal_code(
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
        list_licenses = None
    else:
        category_list = translation.gettext("Public Domain List")
        list_publicdomain = None

    languages_and_links = get_languages_and_links_for_deeds_ux(
        request_path=request.path,
        selected_language_code=language_code,
    )
    canonical_url_html = os.path.join(
        settings.CANONICAL_SITE, request.path.lstrip(os.sep)
    )
    html_response = render(
        request,
        template_name=f"list-{category}.html",
        context={
            "canonical_url_html": canonical_url_html,
            "category": category,
            "category_title": category_title,
            "category_list": category_list,
            "language_default": settings.LANGUAGE_CODE,
            "languages_and_links": languages_and_links,
            "list_licenses": list_licenses,
            "list_publicdomain": list_publicdomain,
            "tools": tools,
        },
    )
    html_response.content = bytes(
        BeautifulSoup(html_response.content, features="lxml").prettify(
            formatter="html5ish"
        ),
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
    if language_code not in settings.LANGUAGES_AVAILABLE_DEEDS_UX:
        return view_page_not_found(
            request, Http404(f"invalid language: {language_code}")
        )

    path_start = os.path.dirname(request.path)
    language_default = get_default_language_for_jurisdiction_deed_ux(jurisdiction)

    try:
        tool = Tool.objects.get(
            unit=unit, version=version, jurisdiction_code=jurisdiction
        )
    except Tool.DoesNotExist as e:
        translation.activate(language_code)
        return view_page_not_found(request, e)

    try:
        # Try to load legal code with specified language
        legal_code = tool.get_legal_code_for_language_code(language_code)
    except LegalCode.DoesNotExist:
        try:
            # Next, try to load legal code with default language for the
            # jurisdiction
            legal_code = tool.get_legal_code_for_language_code(
                get_default_language_for_jurisdiction_legal_code(jurisdiction)
            )
        except LegalCode.DoesNotExist:
            # Last, load legal code with global default language (English)
            legal_code = tool.get_legal_code_for_language_code(
                settings.LANGUAGE_CODE
            )

    tool_title = get_tool_title(
        unit, version, category, jurisdiction, language_code
    )

    legal_code_rel_path = os.path.relpath(
        legal_code.legal_code_url, path_start
    )

    translation.activate(language_code)

    list_licenses, list_publicdomain = get_list_paths(
        language_code, language_default
    )

    category, category_title = get_category_and_category_title(
        category,
        tool,
    )

    languages_and_links = get_languages_and_links_for_deeds_ux(
        request_path=request.path,
        selected_language_code=language_code,
    )

    replaced_title, replaced_path, _, _ = get_legal_code_replaced_rel_path(
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

    canonical_url_html = os.path.join(
        settings.CANONICAL_SITE, request.path.lstrip(os.sep)
    )
    canonical_url_cc = os.path.join(os.path.dirname(canonical_url_html), "")
    html_response = render(
        request,
        template_name="deed.html",
        context={
            "additional_classes": "",
            "body_template": body_template,
            "canonical_url_cc": canonical_url_cc,
            "canonical_url_html": canonical_url_html,
            "category": category,
            "category_title": category_title,
            "identifier": tool.identifier(),
            "language_default": language_default,
            "languages_and_links": languages_and_links,
            "legal_code_rel_path": legal_code_rel_path,
            "list_licenses": list_licenses,
            "list_publicdomain": list_publicdomain,
            "replaced_path": replaced_path,
            "replaced_title": replaced_title,
            "tool": tool,
            "tool_title": tool_title,
        },
    )
    html_response.content = bytes(
        BeautifulSoup(html_response.content, features="lxml").prettify(
            formatter="html5ish"
        ),
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
    plain_text_url = None
    request.path, language_code = normalize_path_and_lang(
        request.path, jurisdiction, language_code
    )
    language_default = get_default_language_for_jurisdiction_legal_code(
        jurisdiction
    )

    list_licenses, list_publicdomain = get_list_paths(
        language_code, language_default
    )

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
    if language_code in settings.LANGUAGES_AVAILABLE_DEEDS_UX:
        translation.activate(language_code)
    elif language_default in settings.LANGUAGES_AVAILABLE_DEEDS_UX:
        translation.activate(language_default)
    else:
        translation.activate(settings.LANGUAGE_CODE)
    tool = legal_code.tool

    # get_tool_title manipulates the translation domain and, therefore, MUST
    # be called before we Activate Legal Code translation
    tool_title = get_tool_title(
        unit, version, category, jurisdiction, language_code
    )
    # get_legal_code_replaced_rel_path calls get_tool_title, see note above
    _, _, replaced_title, replaced_path = get_legal_code_replaced_rel_path(
        tool.is_replaced_by,
        path_start,
        language_code,
        language_default,
    )

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

        if tool.identifier() in PLAIN_TEXT_TOOL_IDENTIFIERS:
            plain_text_url = "legalcode.txt"

        canonical_url_html = os.path.join(
            settings.CANONICAL_SITE, request.path.lstrip(os.sep)
        )
        canonical_url_cc = os.path.join(
            os.path.dirname(canonical_url_html), ""
        )
        kwargs = dict(
            template_name="legalcode.html",
            context={
                "canonical_url_cc": canonical_url_cc,
                "canonical_url_html": canonical_url_html,
                "category": category,
                "category_title": category_title,
                "deed_rel_path": deed_rel_path,
                "identifier": tool.identifier(),
                "language_default": language_default,
                "languages_and_links": languages_and_links,
                "legal_code": legal_code,
                "list_licenses": list_licenses,
                "list_publicdomain": list_publicdomain,
                "plain_text_url": plain_text_url,
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
            BeautifulSoup(html_response.content, features="lxml").prettify(
                formatter="html5ish"
            ),
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
        "last_commit": (
            commits_for_template[0] if commits_for_template else None
        ),
    }


# TODO: evalute when branch status is re-implemented
# # using cache_page seems to break django-distill (weird error about invalid
# # host "testserver"). Do our caching more directly.
# # @cache_page(timeout=5 * 60, cache="branchstatuscache")
def view_branch_status(request, id):  # pragma: no cover
    # translation_branch = get_object_or_404(TranslationBranch, id=id)
    # cache = caches["branchstatuscache"]
    # cachekey = (
    #     f"{settings.DATA_REPOSITORY_DIR}-{translation_branch.branch_name}"
    # )
    # html_response = cache.get(cachekey)
    # if html_response is None:
    #     with git.Repo(settings.DATA_REPOSITORY_DIR) as repo:
    #         context = branch_status_helper(repo, translation_branch)
    #         html_response = render(
    #             request,
    #             "dev/branch_status.html",
    #             context,
    #         )
    #         html_response.content = bytes(
    #             BeautifulSoup(
    #                 html_response.content, features="lxml"
    #             ).prettify(),
    #             "utf-8",
    #         )
    #     cache.set(cachekey, html_response, 5 * 60)
    # return html_response
    pass


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


def view_ns_html(request):
    return render(request, template_name="ns.html")


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


def view_legal_tool_rdf(
    request, category=None, unit=None, version=None, jurisdiction=None
):
    if category:
        rdf_content = generate_legal_code_rdf(
            category, unit, version, jurisdiction
        )
    else:
        rdf_content = generate_legal_code_rdf(generate_all_licenses=True)

    serialized_rdf_content = rdf_content.serialize(format="pretty-xml")
    serialized_rdf_content = order_rdf_xml(serialized_rdf_content)
    response = HttpResponse(
        serialized_rdf_content, content_type="application/rdf+xml"
    )
    return response


def view_image_rdf(request):
    generated_image_rdf = generate_images_rdf()
    serialized_rdf_content = generated_image_rdf.serialize(format="pretty-xml")
    serialized_rdf_content = order_rdf_xml(serialized_rdf_content)
    response = HttpResponse(
        serialized_rdf_content, content_type="application/rdf+xml"
    )
    return response


def view_legacy_plaintext(
    request,
    unit,
    version,
    category=None,
):
    """
    Display plain text file, if it exists (this view is only used in
    development).
    """
    published_docs_path = os.path.abspath(
        os.path.realpath(os.path.join("..", "cc-legal-tools-data", "docs"))
    )
    plain_text_path = os.path.join(
        published_docs_path, request.path.lstrip(os.sep)
    )
    if os.path.isfile(plain_text_path):
        with open(plain_text_path, "rt") as file_obj:
            content = file_obj.read()
        response = HttpResponse(content, content_type="text/plain")
    else:
        raise Http404("plain text file does not exist")

    return response
