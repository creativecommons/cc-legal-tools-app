# Standard library
import os
import subprocess
from operator import itemgetter
from typing import Iterable

# Third-party
import requests
from bs4 import BeautifulSoup
from django.conf import settings
from django.core.cache import cache
from django.utils import translation

# First-party/Local
from i18n.utils import (
    get_default_language_for_jurisdiction_deed,
    get_default_language_for_jurisdiction_naive,
)
from legal_tools.models import LegalCode
from legal_tools.utils import get_tool_title


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
            # Translation incomplete, use app default language (English)
            deed_rel_path = deed_rel_path.replace(
                f"deed.{language_code}", f"deed.{settings.LANGUAGE_CODE}"
            )
    return deed_rel_path


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
            "name_local": get_name_local(legal_code),
            "name_for_sorting": get_name_local(legal_code).lower(),
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


def get_list_paths(language_code, language_default):
    paths = [
        f"/licenses/list.{language_code}",
        f"/publicdomain/list.{language_code}",
    ]
    for index, path in enumerate(paths):
        if language_code not in settings.LANGUAGES_MOSTLY_TRANSLATED:
            if language_default in settings.LANGUAGES_MOSTLY_TRANSLATED:
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


def get_name_local(legal_code):
    return translation.get_language_info(legal_code.language_code)[
        "name_local"
    ]


def normalize_path_and_lang(request_path, jurisdiction, language_code):
    if not language_code:
        if "legalcode" in request_path:
            language_code = get_default_language_for_jurisdiction_naive(
                jurisdiction
            )
        else:
            language_code = get_default_language_for_jurisdiction_deed(
                jurisdiction
            )
    if not request_path.endswith(f".{language_code}"):
        request_path = f"{request_path}.{language_code}"
    return request_path, language_code


def pretty_html_bytes(path, html_bytes):  # pragma: no cover
    """
    1. Clean-up HTML using BeautifulSoup4
    2. Format HTML using Prettier
    """
    if not isinstance(html_bytes, bytes):
        html_bytes = html_bytes.encode("utf-8")
    data = BeautifulSoup(html_bytes, features="lxml").encode()
    if settings.PRETTIER_SLOW:
        # This logic path should only used by GitHub Actions
        # (The multiple Prettier container model, below, is about 25% faster)
        cmd = "prettier --parser html".split()
        completed = subprocess.run(cmd, input=data, capture_output=True)
        return completed.stdout
    else:
        url = "http://prettier:3000"
        headers = {"Content-Type": "text/html"}
        timeout = 5
        response = requests.post(
            url,
            data=data,
            headers=headers,
            timeout=timeout,
        )
        response.raise_for_status()
        return response.content
    # This function is currently expected to complete without error. The
    # primary downside is that HTML syntax errors are not currently exposed. A
    # new function and command line should be created to test validity of HTML
    # independent of publishing.
    #
    # except requests.HTTPError as e:
    #     LOG.warning(f"{path}: {e.response.text}")
