"""
Little utility methods for use with BeautifulSoup4
"""
# Standard library
from itertools import takewhile

# Third-party
from bs4 import NavigableString, Tag


def inner_html(tag):
    """
    Return all the text/html INSIDE the given tag, but
    not the tag element itself.
    """
    return "".join(str(item) for item in tag)


def nested_text(tag):
    """
    This is for processing parts of the document that might or might
    not have some tags (p, span, strong, ...) wrapping around text,
    to help extract the text - or whatever's inside when we strip
    away all the simply nested tags around it.
    Given a tag. If it's a string, return it. If it's got exactly
    one child, recurse on that child. If you get to something more
    complicated, just return the HTML remaining.
    """
    if isinstance(tag, NavigableString):
        return str(tag)
    if len(tag.contents) == 1:
        child = tag.contents[0]
        if isinstance(child, NavigableString):
            return str(child)
        return nested_text(child)
    return inner_html(tag)


def text_up_to(tag, tagname):
    """
    Given a tag, return the text of the immediate children up to,
    but not including the first child whose tagname is 'tagname'.
    (This includes the tags of the immediate children themselves.
    E.g.
    """
    children = list(
        takewhile(
            lambda item: not hasattr(item, "name") or item.name != tagname,
            tag.contents,
        )
    )
    if len(children) == 1:
        return str(children[0])
    return "".join(str(child) for child in children)


def name_and_text(tag: Tag):
    """
    This is for parsing dictionary-like elements in the license.

    If a tag contains text, where the first part has a tag around it
    for formatting (typically 'strong' or 'span'), extract the part
    inside the first tag as the "name", and the html (markup included)
    of the rest.

    E.g. "<strong>Truck</strong> is a <strong>heavy</strong> vehicle."

    Returns a dictionary:
        {"name": "Truck", "text": "is a <strong>heavy</strong> vehicle."}
    """
    top_level_children = list(tag.children)

    strings_from_top_level_children_after_first = [
        str(i) for i in top_level_children[1:]
    ]
    joined_strings = "".join(strings_from_top_level_children_after_first)
    stripped = joined_strings.strip()
    de_newlined = stripped.replace("\n", " ")

    return {
        "name": str(top_level_children[0].string),
        "text": de_newlined,
    }


def direct_children_with_tag(element: Tag, name: str):
    """
    Return list of the elements that are direct children of the
    given element and have the requested tag name.
    """
    result = [
        child
        for child in list(element)
        if isinstance(child, Tag) and child.name == name
    ]
    return result
