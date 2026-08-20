# Standard library
import re

# Third-party
from bs4 import BeautifulSoup, NavigableString, Tag
from bs4.element import Comment

TEXT_LINE_LENGTH = 71

BLOCK_TAGS = frozenset(
    {
        "article",
        "blockquote",
        "div",
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "li",
        "ol",
        "p",
        "section",
        "ul",
    }
)
HEADING_TAGS = frozenset({"h1", "h2", "h3", "h4", "h5", "h6"})
IGNORED_TAGS = frozenset({"script", "style"})
LIST_TAGS = frozenset({"ol", "ul"})


def legal_code_root(html):
    soup = BeautifulSoup(html, "lxml")
    return (
        soup.find(id="legal-code-document")
        or soup.find(id="legal-code-body")
        or soup.body
        or soup
    )


def clean_inline_spacing(value):
    value = re.sub(r"\s+", " ", value)
    value = re.sub(r"\s+([,.;:!?%)\]])", r"\1", value)
    value = re.sub(r"([(\[])\s+", r"\1", value)
    return value.strip()


def direct_children(node, tag_name):
    return [
        child
        for child in node.children
        if isinstance(child, Tag) and child.name.lower() == tag_name
    ]


def has_class(node, class_name):
    return class_name in node.get("class", [])


def has_direct_block_child(node, block_tags=BLOCK_TAGS):
    return any(
        isinstance(child, Tag) and child.name.lower() in block_tags
        for child in node.children
    )


def is_ignorable(node):
    if isinstance(node, Comment):
        return True
    if isinstance(node, NavigableString):
        return not str(node).strip()
    return False


def is_tag(node, tag_name):
    return isinstance(node, Tag) and node.name.lower() == tag_name


def non_ignorable_children(node):
    return [child for child in node.children if not is_ignorable(child)]
