# Standard library
import re
from urllib.parse import urlsplit

LEGAL_CODE_LINK_BASE_URL = "https://creativecommons.org"

_DOMAIN_LIKE_URL_RE = re.compile(
    r"^[A-Za-z0-9.-]+\.[A-Za-z]{2,}(?::\d+)?(?=[/?#]|$)"
)
_EMAIL_LIKE_URL_RE = re.compile(
    r"^[^\s@]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$"
)
_MARKDOWN_LINK_DESTINATION_RE = re.compile(r"[\s()<>]")


def absolute_link_url(href, base_url=LEGAL_CODE_LINK_BASE_URL):
    href = (href or "").strip()
    if not href or href.startswith("#"):
        return href
    if href.startswith("//"):
        return f"{_base_scheme(base_url)}:{href}"
    if _DOMAIN_LIKE_URL_RE.match(href):
        return f"{_base_scheme(base_url)}://{href}"

    parts = urlsplit(href)
    if parts.scheme:
        return href
    if href.startswith("/"):
        return f"{_base_origin(base_url)}{href}"
    return f"{_base_origin(base_url)}/{href}"


def display_link_url(href):
    href = (href or "").strip()
    if not href or href.startswith("#"):
        return ""
    return display_url(href)


def display_link_label_url(label):
    label = label.strip().rstrip(".!?")
    if not looks_like_url(label):
        return ""
    return display_url(label)


def display_url(value):
    value = value.strip()
    if not value:
        return ""
    if value.lower().startswith("mailto:"):
        return _strip_mailto_url(value)
    if _EMAIL_LIKE_URL_RE.match(value):
        return value

    normalized = absolute_link_url(value)
    parts = urlsplit(normalized)
    if parts.scheme.lower() not in {"http", "https"} or not parts.netloc:
        return _strip_url_parts(value)

    path = parts.path or ""
    display_value = f"{parts.netloc}{path}"
    return display_value.rstrip("/") or parts.netloc


def looks_like_url(value):
    return (
        value.startswith(("http://", "https://", "//", "/", "mailto:"))
        or bool(_DOMAIN_LIKE_URL_RE.match(value))
        or bool(_EMAIL_LIKE_URL_RE.match(value))
    )


def markdown_link(label, href):
    label = _escape_markdown_link_label(label)
    destination = markdown_link_destination(href)
    return f"[{label}]({destination})"


def markdown_link_destination(href):
    destination = absolute_link_url(href)
    if _MARKDOWN_LINK_DESTINATION_RE.search(destination):
        destination = destination.replace("\\", "%5C")
        destination = destination.replace("<", "%3C")
        destination = destination.replace(">", "%3E")
        destination = destination.replace("\n", "%0A")
        return f"<{destination}>"
    return destination


def _base_scheme(base_url):
    return urlsplit(base_url).scheme or "https"


def _base_origin(base_url):
    parts = urlsplit(base_url)
    return f"{parts.scheme}://{parts.netloc}"


def _escape_markdown_link_label(label):
    label = label.replace("\\", "\\\\")
    label = label.replace("[", "\\[")
    return label.replace("]", "\\]")


def _strip_mailto_url(value):
    return value[7:].split("?", 1)[0].split("#", 1)[0].strip()


def _strip_url_parts(value):
    return value.split("?", 1)[0].split("#", 1)[0]
