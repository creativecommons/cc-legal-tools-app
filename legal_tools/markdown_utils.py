# Standard library
import textwrap
from html import escape

# Third-party
from bs4 import NavigableString, Tag

# First-party/Local
from legal_tools.link_utils import absolute_link_url, markdown_link
from legal_tools.render_utils import (
    BLOCK_TAGS,
    HEADING_TAGS,
    IGNORED_TAGS,
    LIST_TAGS,
    TEXT_LINE_LENGTH,
    clean_inline_spacing,
    direct_children,
    has_direct_block_child,
    is_ignorable,
    legal_code_root,
)

MARKDOWN_LINE_LENGTH = TEXT_LINE_LENGTH
HTML_LIST_INDENT = 2


def legal_code_html_to_markdown(html):
    """
    Convert rendered legalcode document/body HTML to Markdown.

    The converter is intentionally small and legalcode-focused. It emits lists
    as native Markdown when Markdown can preserve the list semantics, and as
    raw HTML when attributes such as alpha or roman markers require it.
    """
    root = legal_code_root(html)
    markdown = _render_block(root).strip()
    if not markdown:
        return ""
    return f"{markdown}\n"


def _render_block(node, indent=0):
    if is_ignorable(node):
        return ""
    if isinstance(node, NavigableString):
        return _wrap_markdown_text(
            clean_inline_spacing(str(node)), indent=indent
        )
    if not isinstance(node, Tag):
        return ""

    tag_name = node.name.lower()
    if tag_name in IGNORED_TAGS:
        return ""
    if tag_name in HEADING_TAGS:
        level = int(tag_name[1])
        content = _render_inline_children(node)
        if content:
            return f"{' ' * indent}{'#' * level} {content}"
        return ""
    if tag_name == "p":
        return _wrap_markdown_text(_render_inline_children(node), indent=indent)
    if tag_name in LIST_TAGS:
        return _render_list(node, indent=indent)
    if has_direct_block_child(node):
        return _render_block_children(node, indent=indent)
    return _wrap_markdown_text(_render_inline_children(node), indent=indent)


def _render_block_children(node, indent=0):
    chunks = []
    for child in node.children:
        rendered = _strip_rendered(_render_block(child, indent=indent))
        if rendered:
            chunks.append(rendered)
    return "\n\n".join(chunks)


def _render_list(list_tag, indent=0, html_context=False):
    if html_context or _requires_html_list(list_tag):
        return _render_html_list(list_tag, indent=indent)
    return _render_markdown_list(list_tag, indent=indent)


def _render_markdown_list(list_tag, indent=0):
    lines = []
    is_ordered = list_tag.name.lower() == "ol"
    start = _get_ordered_list_start(list_tag) if is_ordered else None
    for offset, list_item in enumerate(direct_children(list_tag, "li")):
        marker = f"{start + offset}." if is_ordered else "-"
        prefix = f"{' ' * indent}{marker} "
        content_indent = indent + len(marker) + 1
        chunks = _render_markdown_list_item_chunks(
            list_item, indent=content_indent
        )
        if not chunks:
            lines.append(prefix.rstrip())
        else:
            lines.extend(
                _render_markdown_list_item(prefix, content_indent, chunks)
            )
    return "\n".join(lines)


def _render_markdown_list_item(prefix, content_indent, chunks):
    lines = []
    for index, (kind, content) in enumerate(chunks):
        if kind == "text":
            if index == 0:
                rendered = _wrap_markdown_text(
                    content,
                    initial_indent=prefix,
                    subsequent_indent=" " * content_indent,
                )
            else:
                rendered = _wrap_markdown_text(
                    content, indent=content_indent
                )
            lines.extend(rendered.splitlines())
        elif kind == "rendered":
            if index == 0:
                lines.append(prefix.rstrip())
            lines.extend(content.splitlines())
        else:
            raise ValueError(f"Unknown Markdown list item chunk kind: {kind}")
    return lines


def _render_markdown_list_item_chunks(list_item, indent=0):
    chunks = []
    inline_nodes = []

    def flush_inline_nodes():
        if not inline_nodes:
            return
        content = _render_inline_nodes(inline_nodes)
        inline_nodes.clear()
        if content:
            chunks.append(("text", content))

    for child in list_item.children:
        if is_ignorable(child):
            continue
        if isinstance(child, Tag) and child.name.lower() == "div":
            flush_inline_nodes()
            chunks.extend(
                _render_markdown_list_item_chunks(child, indent=indent)
            )
        elif isinstance(child, Tag) and child.name.lower() in LIST_TAGS:
            flush_inline_nodes()
            rendered = _strip_rendered(_render_list(child, indent=indent))
            if rendered:
                chunks.append(("rendered", rendered))
        elif isinstance(child, Tag) and child.name.lower() in BLOCK_TAGS:
            flush_inline_nodes()
            if child.name.lower() == "p" and not has_direct_block_child(
                child
            ):
                rendered = _render_inline_children(child)
                if rendered:
                    chunks.append(("text", rendered))
            else:
                rendered = _strip_rendered(_render_block(child, indent=indent))
                if rendered:
                    chunks.append(("rendered", rendered))
        else:
            inline_nodes.append(child)
    flush_inline_nodes()
    return chunks


def _render_html_list(list_tag, indent=0):
    tag_name = list_tag.name.lower()
    attrs = _render_list_attrs(list_tag)
    list_indent = " " * indent
    list_item_indent = " " * (indent + HTML_LIST_INDENT)
    content_indent = indent + (2 * HTML_LIST_INDENT)
    lines = [f"{list_indent}<{tag_name}{attrs}>"]
    for list_item in direct_children(list_tag, "li"):
        content = _render_html_list_item(list_item)
        if not content:
            lines.append(f"{list_item_indent}<li></li>")
        elif (
            "\n" in content
            or len(f"{list_item_indent}<li>{content}</li>")
            > MARKDOWN_LINE_LENGTH
        ):
            content = _render_html_list_item(list_item, indent=content_indent)
            lines.append(f"{list_item_indent}<li>")
            lines.extend(content.splitlines())
            lines.append(f"{list_item_indent}</li>")
        else:
            lines.append(f"{list_item_indent}<li>{content}</li>")
    lines.append(f"{list_indent}</{tag_name}>")
    return "\n".join(lines)


def _requires_html_list(list_tag):
    tag_name = list_tag.name.lower()
    if tag_name == "ul":
        return list_tag.has_attr("type")
    if tag_name != "ol":
        return True
    if list_tag.has_attr("reversed"):
        return True
    list_type = list_tag.get("type", "1")
    if list_type not in {"", "1"}:
        return True
    return _get_ordered_list_start(list_tag) is None


def _get_ordered_list_start(list_tag):
    try:
        return int(list_tag.get("start", 1))
    except ValueError:
        return None


def _render_list_attrs(list_tag):
    allowed_attrs = {
        "ol": ("type", "start", "reversed"),
        "ul": ("type",),
    }
    attrs = []
    for attr in allowed_attrs[list_tag.name.lower()]:
        if attr not in list_tag.attrs:
            continue
        value = list_tag.get(attr)
        if attr == "reversed":
            attrs.append(attr)
        else:
            attrs.append(f'{attr}="{escape(str(value), quote=True)}"')
    if not attrs:
        return ""
    return f" {' '.join(attrs)}"


def _render_html_list_item(list_item, indent=0):
    chunks = []
    inline_nodes = []

    def flush_inline_nodes():
        if not inline_nodes:
            return
        content = _render_html_inline_nodes(inline_nodes)
        inline_nodes.clear()
        if content:
            chunks.append(_wrap_html_text(content, indent=indent))

    for child in list_item.children:
        if is_ignorable(child):
            continue
        if isinstance(child, Tag) and child.name.lower() == "div":
            flush_inline_nodes()
            rendered = _strip_rendered(
                _render_html_container_children(child, indent=indent)
            )
            if rendered:
                chunks.append(rendered)
        elif isinstance(child, Tag) and child.name.lower() in LIST_TAGS:
            flush_inline_nodes()
            rendered = _strip_rendered(_render_list(child, html_context=True))
            if rendered:
                chunks.append(_indent_lines(rendered, indent))
        elif isinstance(child, Tag) and child.name.lower() in BLOCK_TAGS:
            flush_inline_nodes()
            rendered = _strip_rendered(
                _render_html_block(child, indent=indent)
            )
            if rendered:
                chunks.append(rendered)
        else:
            inline_nodes.append(child)
    flush_inline_nodes()
    return "\n".join(chunks)


def _render_html_block(node, indent=0):
    if is_ignorable(node):
        return ""
    if isinstance(node, NavigableString):
        return _wrap_html_text(
            escape(clean_inline_spacing(str(node)), quote=False),
            indent=indent,
        )
    if not isinstance(node, Tag):
        return ""

    tag_name = node.name.lower()
    if tag_name in IGNORED_TAGS:
        return ""
    if tag_name in LIST_TAGS:
        return _render_list(node, indent=indent, html_context=True)
    if tag_name == "li":
        return _render_html_list_item(node, indent=indent)
    if tag_name == "div":
        return _render_html_container_children(node, indent=indent)

    if has_direct_block_child(node):
        content = "\n".join(
            rendered
            for child in node.children
            if (
                rendered := _strip_rendered(
                    _render_html_block(
                        child, indent=indent + HTML_LIST_INDENT
                    )
                )
            )
        )
        return _wrap_html_tag(
            tag_name, content, indent=indent, content_indented=True
        )
    else:
        content = _render_html_inline_children(node)
    return _wrap_html_tag(tag_name, content, indent=indent)


def _render_html_container_children(node, indent=0):
    return _render_html_list_item(node, indent=indent)


def _wrap_html_tag(tag_name, content, indent=0, content_indented=False):
    line_indent = " " * indent
    tag_content = f"{line_indent}<{tag_name}>{content}</{tag_name}>"
    if "\n" in content or len(tag_content) > MARKDOWN_LINE_LENGTH:
        if not content_indented:
            content = _wrap_html_text(
                content, indent=indent + HTML_LIST_INDENT
            )
        return f"{line_indent}<{tag_name}>\n{content}\n{line_indent}</{tag_name}>"
    return tag_content


def _render_html_inline_nodes(nodes):
    return clean_inline_spacing(
        "".join(_render_html_inline(node) for node in nodes)
    )


def _render_inline_nodes(nodes):
    return clean_inline_spacing("".join(_render_inline(node) for node in nodes))


def _render_html_inline(node):
    if is_ignorable(node):
        return ""
    if isinstance(node, NavigableString):
        return escape(str(node), quote=False)
    if not isinstance(node, Tag):
        return ""

    tag_name = node.name.lower()
    if tag_name == "br":
        return "<br>"

    content = _render_html_inline_children(node)
    if not content:
        return ""

    if tag_name in {"b", "strong"}:
        return f"<strong>{content}</strong>"
    if tag_name in {"em", "i"}:
        return f"<em>{content}</em>"
    if tag_name == "code":
        return f"<code>{content}</code>"
    if tag_name == "a":
        href = node.get("href")
        if href:
            href = escape(absolute_link_url(href), quote=True)
            return f'<a href="{href}">{content}</a>'
        return content
    if tag_name == "u" or _is_underline_span(node):
        return f"<u>{content}</u>"
    if tag_name in {"sub", "sup"}:
        return f"<{tag_name}>{content}</{tag_name}>"
    return content


def _render_html_inline_children(node):
    return _render_html_inline_nodes(node.children)


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

    if tag_name in {"b", "strong"}:
        return f"**{content}**"
    if tag_name in {"em", "i"}:
        return f"*{content}*"
    if tag_name == "code":
        return f"`{content}`"
    if tag_name == "a":
        href = node.get("href")
        if href:
            return markdown_link(content, href)
        return content
    if tag_name == "u" or _is_underline_span(node):
        return f"<u>{content}</u>"
    if tag_name in {"sub", "sup"}:
        return f"<{tag_name}>{content}</{tag_name}>"
    return content


def _render_inline_children(node):
    return clean_inline_spacing(
        "".join(_render_inline(child) for child in node.children)
    )


def _wrap_markdown_text(
    value, indent=0, initial_indent=None, subsequent_indent=None
):
    return _wrap_text(
        value,
        indent=indent,
        initial_indent=initial_indent,
        subsequent_indent=subsequent_indent,
    )


def _wrap_html_text(value, indent=0):
    return _wrap_text(value, indent=indent)


def _wrap_text(value, indent=0, initial_indent=None, subsequent_indent=None):
    if initial_indent is None:
        initial_indent = " " * indent
    if subsequent_indent is None:
        subsequent_indent = " " * indent
    return textwrap.fill(
        value,
        width=MARKDOWN_LINE_LENGTH,
        initial_indent=initial_indent,
        subsequent_indent=subsequent_indent,
        break_long_words=False,
        break_on_hyphens=False,
    )


def _indent_lines(value, indent):
    line_indent = " " * indent
    return "\n".join(f"{line_indent}{line}" for line in value.splitlines())


def _strip_rendered(value):
    value = value.strip("\n")
    if not value.strip():
        return ""
    return value


def _is_underline_span(node):
    if node.name.lower() != "span":
        return False
    style = node.get("style", "").lower().replace(" ", "")
    return "text-decoration:underline" in style
