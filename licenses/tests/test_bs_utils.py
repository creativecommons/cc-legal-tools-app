# Third-party
from bs4 import BeautifulSoup
from django.test import TestCase

# First-party/Local
from licenses.bs_utils import (
    direct_children_with_tag,
    inner_html,
    name_and_text,
    nested_text,
    text_up_to,
)


class TestBSUtils(TestCase):
    def test_inner_html(self):
        text = """<div id="foo"><strong><p>Foo</p></strong></div>"""
        soup = BeautifulSoup(text, "lxml")
        self.assertEqual(
            "<strong><p>Foo</p></strong>", inner_html(soup.find(id="foo"))
        )

    def test_nested_text(self):
        text = """<div id="foo"><strong><p>Foo</p></strong></div>"""
        soup = BeautifulSoup(text, "lxml")
        self.assertEqual("Foo", nested_text(soup.find(id="foo")))

        nav_string = soup.find(id="foo").strong.p.string
        self.assertEqual("Foo", nested_text(nav_string))

        # Deeper
        text = """<div id="foo"><h1><strong><p>Foo</p></strong></h1></div>"""
        soup = BeautifulSoup(text, "lxml")
        self.assertEqual("Foo", nested_text(soup.find(id="foo")))

        # Multiple children
        text = """<div id="test"><p>1</p><p>2</p></div>"""
        soup = BeautifulSoup(text, "lxml")
        self.assertEqual("<p>1</p><p>2</p>", nested_text(soup.find(id="test")))

    def test_text_up_to(self):
        """
        Given a tag, return the text of the immediate children up to,
        but not including the first child whose tagname is 'tagname'.
        """
        text = (
            '<div id="top"><p>Child 1</p><p>Child 2</p><span>Foo</span>'
            "<p>Child 4</p> </div>"
        )
        soup = BeautifulSoup(text, "lxml")
        self.assertEqual(
            "<p>Child 1</p><p>Child 2</p>",
            text_up_to(soup.find(id="top"), "span"),
        )
        # Simpler - only one child before the 'up to'
        text = """
        <div id="top"><p>Child 1</p><span>Foo</span><p>Child 4</p> </div>
        """
        soup = BeautifulSoup(text, "lxml")
        self.assertEqual(
            "<p>Child 1</p>", text_up_to(soup.find(id="top"), "span")
        )

    def test_name_and_text(self):
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
        text = (
            '<div id="test"><strong>Truck</strong> is a <strong>heavy</strong>'
            " vehicle.</div>"
        )
        soup = BeautifulSoup(text, "lxml")
        self.assertEqual(
            {"name": "Truck", "text": "is a <strong>heavy</strong> vehicle."},
            name_and_text(soup.find(id="test")),
        )

    def test_direct_children_with_tag(self):
        text = """
        <div id="top">
           <div id="child1"></div>
           <span id="child2">
               <div id="grandchild2.1"></div>
           </span>
           <div id="child3">
                <span id="grandchild3.1"></span>
            </div>
        </div>
        """
        soup = BeautifulSoup(text, "lxml")
        element = soup.find(id="top")
        result = direct_children_with_tag(element, "div")
        self.assertEqual(2, len(result))
        self.assertEqual(result[0]["id"], "child1")
        self.assertEqual(result[1]["id"], "child3")
        result = direct_children_with_tag(element, "span")
        self.assertEqual(1, len(result))
        self.assertEqual("child2", result[0]["id"])
