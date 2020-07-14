from django.test import TestCase

from licenses.utils import get_code_from_jurisdiction_url


class GetJurisdictionCodeTest(TestCase):
    def test_get_code_from_jurisdiction_url(self):
        # Just returns the last portion of the path
        self.assertEqual("foo", get_code_from_jurisdiction_url("http://example.com/bar/foo/"))
        self.assertEqual("foo", get_code_from_jurisdiction_url("http://example.com/bar/foo"))
        self.assertEqual("", get_code_from_jurisdiction_url("http://example.com"))
