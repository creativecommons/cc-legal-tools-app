# Standard library
from dataclasses import dataclass
import re
import textwrap

# Third-party
from bs4 import NavigableString, Tag

# First-party/Local
from legal_tools.link_utils import display_link_label_url, display_link_url
from legal_tools.render_utils import (
    BLOCK_TAGS,
    HEADING_TAGS,
    IGNORED_TAGS,
    LIST_TAGS,
    TEXT_LINE_LENGTH,
    clean_inline_spacing,
    direct_children,
    has_class,
    has_direct_block_child,
    is_ignorable,
    is_tag,
    legal_code_root,
    non_ignorable_children,
)

PLAIN_TEXT_LINE_LENGTH = TEXT_LINE_LENGTH
PLAIN_TEXT_SEPARATOR = "=" * PLAIN_TEXT_LINE_LENGTH
LIST_MIN_PREFIX_WIDTH = 5
NOTICE_ASIDE_INDENT = 5
EN_DASH_PLACEHOLDER = "\ue000\ue001"
_SECTION_REFERENCE_RE = re.compile(
    r"^(\d+)((?:\([A-Za-z0-9]+\))+)(-(?:\([A-Za-z0-9]+\))+)?"
    r"([.,;:!?]*)$"
)
_SECTION_REFERENCE_PART_RE = re.compile(r"\([A-Za-z0-9]+\)")
_IGNORED_TAGS = IGNORED_TAGS | {"hr"}
_LIST_CHUNK_TEXT = "text"
_LIST_CHUNK_RENDERED = "rendered"
_NOTICE_ASIDE_CLASSES = {"level", "is-vcentered", "b-header"}
_SKIPPED_NOTICE_HEADING_PARENT_IDS = {
    "notice-about-licenses-and-cc",
    "notice-about-cc-and-trademark",
}


class PlainTextRenderError(ValueError):
    pass


@dataclass(frozen=True)
class _PlainTextRenderContext:
    list_prefix_width: int


class _PlainTextWrapper(textwrap.TextWrapper):
    def _split(self, text):
        chunks = super()._split(text)
        return [
            part
            for chunk in chunks
            for part in _split_section_reference_chunk(chunk)
        ]


def legal_code_html_to_plain_text(html):
    """
    Convert rendered legalcode document/body HTML to plain text.

    The converter is legalcode-focused. It uses the same document regions that
    HTML/CSS use for visual separation, and it renders ordered-list markers
    explicitly because plain text has no list semantics.
    """
    root = legal_code_root(html)
    context = _build_render_context(root)
    if isinstance(root, Tag) and root.get("id") == "legal-code-document":
        plain_text = _render_document(root, context).strip("\n")
    else:
        plain_text = _render_block(root, context).strip("\n")
    if not plain_text:
        return ""
    plain_text = _restore_plain_text_tokens(plain_text)
    return f"{plain_text}\n"


def _build_render_context(root):
    longest_marker = 0
    for list_tag in root.find_all("ol"):
        list_items = direct_children(list_tag, "li")
        start = _get_start(list_tag, len(list_items))
        for offset, _list_item in enumerate(list_items):
            number = (
                start - offset if _is_reversed(list_tag) else start + offset
            )
            marker = _get_list_marker(list_tag, number)
            longest_marker = max(longest_marker, len(marker))
    return _PlainTextRenderContext(
        list_prefix_width=max(LIST_MIN_PREFIX_WIDTH, longest_marker + 2)
    )


def _render_document(document, context):
    sections = []
    current_region = None
    current_chunks = []

    def flush_region():
        nonlocal current_region, current_chunks
        rendered = "\n\n".join(chunk for chunk in current_chunks if chunk)
        if rendered:
            sections.append(rendered)
        current_region = None
        current_chunks = []

    for child in non_ignorable_children(document):
        region = _document_region(child)
        rendered = _render_block(child, context)
        if _preserves_trailing_spacing(child):
            rendered = rendered.lstrip("\n")
        else:
            rendered = rendered.strip("\n")
        if not rendered.strip():
            continue
        if current_region is not None and region != current_region:
            flush_region()
        current_region = region
        current_chunks.append(rendered)
    flush_region()
    return f"\n\n{PLAIN_TEXT_SEPARATOR}\n\n".join(sections)


def _document_region(node):
    if isinstance(node, Tag):
        tag_name = node.name.lower()
        if tag_name == "h1":
            return "title"
        if has_class(node, "notice-top"):
            return "preface"
        if node.get("id") == "legal-code-body":
            return "body"
        if has_class(node, "notice-bottom"):
            return "footer"
    return "other"


def _render_block(node, context, indent=0):
    if is_ignorable(node):
        return ""
    if isinstance(node, NavigableString):
        return _wrap_text(_clean_inline(str(node)), indent=indent)
    if not isinstance(node, Tag):
        return ""

    tag_name = node.name.lower()
    if tag_name in _IGNORED_TAGS:
        return ""
    if _is_skipped_notice_heading(node):
        return ""
    if tag_name in HEADING_TAGS:
        return _wrap_text(_render_inline_children(node), indent=indent)
    if tag_name == "p":
        return _wrap_text(_render_inline_children(node), indent=indent)
    if tag_name in LIST_TAGS:
        return _render_list(node, context, indent=indent)
    if node.get("id") == "legal-code-body":
        return _render_legal_code_body(node, context, indent=indent)
    if node.get("id") == "about-cc-and-license":
        return _render_about_cc_and_license(node, context, indent=indent)
    if has_direct_block_child(node):
        return _render_block_children(node, context, indent=indent)
    return _wrap_text(_render_inline_children(node), indent=indent)


def _render_block_children(node, context, indent=0):
    return _render_block_nodes(node.children, context, indent=indent)


def _render_block_nodes(nodes, context, indent=0):
    chunks = []
    for child in nodes:
        _append_rendered(chunks, _render_block(child, context, indent=indent))
    return "\n\n".join(chunks)


def _append_rendered(chunks, rendered):
    rendered = _strip_rendered(rendered)
    if rendered.strip():
        chunks.append(rendered)


def _strip_rendered(rendered):
    return rendered.strip("\n")


def _render_legal_code_body(node, context, indent=0):
    chunks = []
    for is_section, group in _legal_code_body_groups(node):
        rendered = _strip_rendered(
            _render_block_nodes(group, context, indent=indent)
        )
        if not rendered.strip():
            continue
        if is_section:
            rendered = f"{rendered}\n"
        chunks.append(rendered)
    return "\n\n".join(chunks)


def _legal_code_body_groups(node):
    groups = []
    current_group = []
    current_is_section = False

    def flush_group():
        nonlocal current_group
        if current_group:
            groups.append((current_is_section, current_group))
            current_group = []

    for child in non_ignorable_children(node):
        if _is_legal_section_heading(child):
            flush_group()
            current_group = [child]
            current_is_section = True
        else:
            current_group.append(child)
    flush_group()
    return groups


def _render_about_cc_and_license(node, context, indent=0):
    chunks = []
    ordinary_nodes = []
    children = non_ignorable_children(node)
    index = 0

    def flush_ordinary_nodes():
        if not ordinary_nodes:
            return
        rendered = _render_block_nodes(
            ordinary_nodes, context, indent=indent
        )
        _append_rendered(chunks, rendered)
        ordinary_nodes.clear()

    while index < len(children):
        child = children[index]
        if _is_notice_aside_heading(child):
            flush_ordinary_nodes()
            notice_nodes = [child]
            index += 1
            while index < len(children) and not _is_notice_aside_terminator(
                children[index]
            ):
                notice_nodes.append(children[index])
                index += 1
            rendered = _render_notice_aside(
                notice_nodes, context, indent=indent
            )
            _append_rendered(chunks, rendered)
            continue
        if not _is_divider(child):
            ordinary_nodes.append(child)
        index += 1

    flush_ordinary_nodes()
    return "\n\n".join(chunks)


def _is_notice_aside_heading(node):
    return (
        is_tag(node, "h3")
        and _NOTICE_ASIDE_CLASSES.issubset(set(node.get("class", [])))
    )


def _is_notice_aside_terminator(node):
    return _is_divider(node) or _is_heading_at_or_above(node, level=3)


def _is_heading_at_or_above(node, level):
    if not isinstance(node, Tag):
        return False
    match = re.fullmatch(r"h([1-6])", node.name.lower())
    return bool(match and int(match.group(1)) <= level)


def _render_notice_aside(nodes, context, indent=0):
    heading = _render_inline_children(nodes[0])
    if not heading:
        return _render_block_nodes(nodes[1:], context, indent=indent)

    prefix = heading if heading.endswith(":") else f"{heading}:"
    content = " ".join(
        part
        for part in (
            _render_notice_aside_text(node, context) for node in nodes[1:]
        )
        if part
    )
    value = f"{prefix} {content}" if content else prefix
    aside_indent = " " * (indent + NOTICE_ASIDE_INDENT)
    return _wrap_text(
        value,
        initial_indent=aside_indent,
        subsequent_indent=aside_indent,
        width=PLAIN_TEXT_LINE_LENGTH - NOTICE_ASIDE_INDENT,
    )


def _render_notice_aside_text(node, context):
    if is_ignorable(node):
        return ""
    if isinstance(node, NavigableString):
        return _clean_inline(str(node))
    if not isinstance(node, Tag):
        return ""

    tag_name = node.name.lower()
    if tag_name in _IGNORED_TAGS:
        return ""
    if not has_direct_block_child(node):
        return _render_inline_children(node)
    return _clean_inline(_render_block(node, context))


def _render_list(list_tag, context, indent=0):
    rendered_items = []
    is_ordered = list_tag.name.lower() == "ol"
    list_items = direct_children(list_tag, "li")
    start = _get_start(list_tag, len(list_items))
    for offset, list_item in enumerate(list_items):
        if is_ordered:
            number = (
                start - offset if _is_reversed(list_tag) else start + offset
            )
            marker = _get_list_marker(list_tag, number)
            prefix = f"{' ' * indent}{_format_marker(marker, context)}"
        else:
            prefix = f"{' ' * indent}{_format_unordered_marker(context)}"
        content_indent = indent + context.list_prefix_width
        chunks = _render_list_item_chunks(list_item, context, content_indent)
        if not chunks:
            rendered_items.append(prefix.rstrip())
        else:
            rendered_items.append(
                "\n".join(_render_list_item(prefix, content_indent, chunks))
            )
    return "\n\n".join(rendered_items)


def _render_list_item(prefix, content_indent, chunks):
    lines = []
    for index, (kind, content) in enumerate(chunks):
        if index > 0 and lines and lines[-1] != "":
            lines.append("")
        if kind == _LIST_CHUNK_TEXT:
            if index == 0:
                rendered = _wrap_text(
                    content,
                    initial_indent=prefix,
                    subsequent_indent=" " * content_indent,
                )
            else:
                rendered = _wrap_text(content, indent=content_indent)
            lines.extend(rendered.splitlines())
        elif kind == _LIST_CHUNK_RENDERED:
            if index == 0:
                lines.append(prefix.rstrip())
            lines.extend(content.splitlines())
        else:
            raise PlainTextRenderError(f"Unknown list item chunk kind: {kind}")
    return lines


def _render_list_item_chunks(list_item, context, content_indent):
    chunks = []
    inline_nodes = []

    def flush_inline_nodes():
        if not inline_nodes:
            return
        content = _render_inline_nodes(inline_nodes)
        inline_nodes.clear()
        if content:
            chunks.append((_LIST_CHUNK_TEXT, content))

    for child in non_ignorable_children(list_item):
        if isinstance(child, Tag) and child.name.lower() == "div":
            flush_inline_nodes()
            chunks.extend(
                _render_list_item_chunks(child, context, content_indent)
            )
        elif isinstance(child, Tag) and child.name.lower() in LIST_TAGS:
            flush_inline_nodes()
            rendered = _strip_rendered(
                _render_list(child, context, indent=content_indent)
            )
            if rendered.strip():
                chunks.append((_LIST_CHUNK_RENDERED, rendered))
        elif isinstance(child, Tag) and child.name.lower() in BLOCK_TAGS:
            flush_inline_nodes()
            if child.name.lower() == "p" and not has_direct_block_child(
                child
            ):
                rendered = _render_inline_children(child)
                if rendered:
                    chunks.append((_LIST_CHUNK_TEXT, rendered))
            else:
                rendered = _strip_rendered(
                    _render_block(child, context, indent=content_indent)
                )
                if rendered.strip():
                    chunks.append((_LIST_CHUNK_RENDERED, rendered))
        else:
            inline_nodes.append(child)
    flush_inline_nodes()
    if _has_bold_font_weight(list_item):
        chunks = [(kind, content.upper()) for kind, content in chunks]
    return chunks


def _format_marker(marker, context):
    marker = marker.rjust(context.list_prefix_width - 2)
    return f"{marker}. "


def _format_unordered_marker(context):
    return f"{'-'.rjust(context.list_prefix_width - 1)} "


def _get_start(list_tag, list_length):
    if _is_reversed(list_tag):
        default = list_length
    else:
        default = 1
    try:
        return int(list_tag.get("start", default))
    except ValueError:
        return default


def _is_reversed(list_tag):
    return list_tag.name.lower() == "ol" and list_tag.has_attr("reversed")


def _get_list_marker(list_tag, number):
    list_type = list_tag.get("type", "1")
    if list_type in {"1", ""}:
        return str(number)
    if list_type == "a":
        return _alpha(number).lower()
    if list_type == "A":
        return _alpha(number).upper()
    if list_type == "i":
        return _roman(number).lower()
    if list_type == "I":
        return _roman(number).upper()
    return str(number)


def _alpha(number):
    if number < 1:
        raise PlainTextRenderError(
            f"Alpha list marker requires positive number: {number}"
        )
    chars = []
    while number > 0:
        number -= 1
        number, remainder = divmod(number, 26)
        chars.append(chr(ord("a") + remainder))
    return "".join(reversed(chars))


def _roman(number):
    if number < 1:
        raise PlainTextRenderError(
            f"Roman list marker requires positive number: {number}"
        )
    numerals = [
        (1000, "M"),
        (900, "CM"),
        (500, "D"),
        (400, "CD"),
        (100, "C"),
        (90, "XC"),
        (50, "L"),
        (40, "XL"),
        (10, "X"),
        (9, "IX"),
        (5, "V"),
        (4, "IV"),
        (1, "I"),
    ]
    result = []
    for value, symbol in numerals:
        while number >= value:
            result.append(symbol)
            number -= value
    return "".join(result)


def _render_inline_nodes(nodes):
    return _clean_inline("".join(_render_inline(node) for node in nodes))


def _render_inline(node):
    if is_ignorable(node):
        return ""
    if isinstance(node, NavigableString):
        return str(node)
    if not isinstance(node, Tag):
        return ""

    tag_name = node.name.lower()
    if tag_name == "br":
        return "\n"

    content = _render_inline_children(node)
    if not content:
        return ""
    if _has_bold_font_weight(node):
        content = content.upper()

    if tag_name == "a":
        href = node.get("href")
        display_url = display_link_url(href)
        if display_url:
            label_url = display_link_label_url(content)
            if label_url == display_url:
                return display_url
            label = content.rstrip(".!?")
            if label.endswith(":"):
                return f"{label} {display_url}"
            return f"{label}: {display_url}"
        return content
    return content


def _render_inline_children(node):
    return _render_inline_nodes(node.children)


def _wrap_text(
    value,
    indent=0,
    initial_indent=None,
    subsequent_indent=None,
    width=PLAIN_TEXT_LINE_LENGTH,
):
    if not value:
        return ""
    if initial_indent is None:
        initial_indent = " " * indent
    if subsequent_indent is None:
        subsequent_indent = " " * indent
    wrapper = _PlainTextWrapper(
        width=width,
        initial_indent=initial_indent,
        subsequent_indent=subsequent_indent,
        break_long_words=False,
        break_on_hyphens=True,
    )
    return wrapper.fill(value)


def _split_section_reference_chunk(chunk):
    match = _SECTION_REFERENCE_RE.fullmatch(chunk)
    if not match:
        return [chunk]

    section, parenthetical_refs, range_refs, trailing_punctuation = (
        match.groups()
    )
    parts = [
        section,
        *_SECTION_REFERENCE_PART_RE.findall(parenthetical_refs),
    ]
    if range_refs:
        parts[-1] = f"{parts[-1]}-"
        parts.extend(_SECTION_REFERENCE_PART_RE.findall(range_refs))
    if trailing_punctuation:
        parts[-1] = f"{parts[-1]}{trailing_punctuation}"
    return parts


def _clean_inline(value):
    value = value.replace("\u2013", EN_DASH_PLACEHOLDER)
    value = value.replace("\u2019", "'")
    value = value.replace("\u201c", '"')
    value = value.replace("\u201d", '"')
    return clean_inline_spacing(value)


def _restore_plain_text_tokens(value):
    return value.replace(EN_DASH_PLACEHOLDER, "--")


def _is_divider(node):
    return is_tag(node, "hr") and has_class(node, "divider")


def _is_legal_section_heading(node):
    return is_tag(node, "h3") and re.fullmatch(r"s\d+", node.get("id", ""))


def _is_skipped_notice_heading(node):
    if not is_tag(node, "h2"):
        return False
    parent = node.parent
    return (
        isinstance(parent, Tag)
        and parent.get("id") in _SKIPPED_NOTICE_HEADING_PARENT_IDS
    )


def _has_bold_font_weight(node):
    if not isinstance(node, Tag):
        return False
    style = node.get("style", "")
    return bool(
        re.search(r"(?:^|;)\s*font-weight\s*:\s*bold\s*(?:;|$)", style, re.I)
    )


def _preserves_trailing_spacing(node):
    return isinstance(node, Tag) and node.get("id") == "legal-code-body"
