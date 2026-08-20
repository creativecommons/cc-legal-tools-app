# Third-party
from django.test import SimpleTestCase

# First-party/Local
from legal_tools.link_utils import (
    absolute_link_url,
    display_link_label_url,
    display_link_url,
    markdown_link,
    markdown_link_destination,
)


class LinkUtilsTest(SimpleTestCase):
    def test_absolute_link_url(self):
        self.assertEqual("#s1", absolute_link_url("#s1"))
        self.assertEqual(
            "https://creativecommons.org/policies/",
            absolute_link_url("/policies/"),
        )
        self.assertEqual(
            "https://creativecommons.org/compatiblelicenses",
            absolute_link_url("//creativecommons.org/compatiblelicenses"),
        )
        self.assertEqual(
            "https://example.test/path?x=1#part",
            absolute_link_url("example.test/path?x=1#part"),
        )
        self.assertEqual(
            "mailto:info@creativecommons.org",
            absolute_link_url("mailto:info@creativecommons.org"),
        )

    def test_display_link_url(self):
        self.assertEqual("", display_link_url("#s1"))
        self.assertEqual(
            "creativecommons.org/policies",
            display_link_url("/policies/?x=1#license"),
        )
        self.assertEqual(
            "creativecommons.org",
            display_link_url("//creativecommons.org/"),
        )
        self.assertEqual(
            "info@creativecommons.org",
            display_link_url("mailto:info@creativecommons.org?subject=Hi"),
        )

    def test_display_link_label_url(self):
        self.assertEqual(
            "creativecommons.org/policies",
            display_link_label_url("creativecommons.org/policies."),
        )
        self.assertEqual("", display_link_label_url("More information"))

    def test_markdown_link_destination(self):
        self.assertEqual("#s1", markdown_link_destination("#s1"))
        self.assertEqual(
            "<https://creativecommons.org/policies/some path(1)>",
            markdown_link_destination("/policies/some path(1)"),
        )
        self.assertEqual(
            "https://example.test/path?x=1#part",
            markdown_link_destination("https://example.test/path?x=1#part"),
        )
        self.assertEqual(
            "<https://example.test/a%3Cb%3E>",
            markdown_link_destination("https://example.test/a<b>"),
        )

    def test_markdown_link_escapes_label(self):
        self.assertEqual(
            "[Policy \\[draft\\]](https://creativecommons.org/policies/)",
            markdown_link("Policy [draft]", "/policies/"),
        )
