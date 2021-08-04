# Standard library
import logging
import os
import tempfile
from io import StringIO
from unittest import mock
from unittest.mock import MagicMock, call

# Third-party
from bs4 import BeautifulSoup
from django.test import TestCase
from django.urls import Resolver404, URLResolver
from polib import POEntry

# First-party/Local
from licenses import utils
from licenses.models import License
from .factories import LegalCodeFactory, LicenseFactory


class LoggingTest(TestCase):
    def test_init_utils_logger(self):
        utils.init_utils_logger(None)
        self.assertEqual("licenses.utils", utils.LOG.name)

        logger = logging.getLogger(__name__)
        utils.init_utils_logger(logger)
        self.assertEqual("licenses.tests.test_utils", utils.LOG.name)


class SaveURLAsStaticFileTest(TestCase):
    def test_save_bytes_to_file(self):
        try:
            tmpdir = tempfile.TemporaryDirectory()
            filename = os.path.join(tmpdir.name, "level1")
            utils.save_bytes_to_file(b"abcxyz", filename)
            with open(filename, "rb") as f:
                contents = f.read()
            self.assertEqual(b"abcxyz", contents)

            filename = os.path.join(tmpdir.name, "level1", "level2")
            utils.save_bytes_to_file(b"abcxyz", filename)
            with open(filename, "rb") as f:
                contents = f.read()
            self.assertEqual(b"abcxyz", contents)
        finally:
            tmpdir.cleanup()

    def test_relative_symlink(self):
        try:
            tmpdir = tempfile.TemporaryDirectory()
            # symlink link1 => source1 and verify by reading link1
            contents1 = b"111"
            source1 = os.path.join(tmpdir.name, "source1")
            with open(source1, "wb") as f:
                f.write(contents1)
            utils.relative_symlink(tmpdir.name, source1, "link1")
            with open(os.path.join(tmpdir.name, "link1"), "rb") as f:
                contents = f.read()
            self.assertEqual(contents1, contents)
            # symlink link2 => xx/source2 and verify by reading link2
            subdir = os.path.join(tmpdir.name, "xx")
            os.makedirs(subdir, mode=0o755)
            contents2 = b"222"
            source2 = os.path.join(subdir, "source1")
            with open(source2, "wb") as f:
                f.write(contents2)
            utils.relative_symlink(tmpdir.name, source2, "../link2")
            with open(os.path.join(tmpdir.name, "link2"), "rb") as f:
                contents = f.read()
            self.assertEqual(contents2, contents)
        finally:
            tmpdir.cleanup()

    def test_save_url_as_static_file_not_200(self):
        output_dir = "/output"
        url = "/some/url/"
        with self.assertRaises(Resolver404):
            utils.save_url_as_static_file(
                output_dir,
                url,
                relpath="",
            )

    def test_save_url_as_static_file_500(self):
        output_dir = "/output"
        url = "/licenses/metadata.yaml"
        file_content = b"xxxxx"

        class MockResponse:
            content = file_content
            status_code = 500

        class MockResolverMatch:
            def __init__(self, func):
                self.func = func
                self.args = []
                self.kwargs = {}

        mock_view_metadata = MagicMock()
        mock_view_metadata.return_value = MockResponse()

        with mock.patch("licenses.utils.save_bytes_to_file"):
            with mock.patch.object(URLResolver, "resolve") as mock_resolve:
                mock_resolve.return_value = MockResolverMatch(
                    func=mock_view_metadata
                )
                with self.assertRaisesMessage(
                    ValueError,
                    "ERROR: Status 500 for url /licenses/metadata.yaml",
                ):
                    with mock.patch("sys.stdout", new=StringIO()):
                        utils.save_url_as_static_file(
                            output_dir,
                            url,
                            relpath="/output/licenses/metadata.yaml",
                        )

    def test_save_url_as_static_file_200_yaml(self):
        output_dir = "/output"
        url = "/licenses/metadata.yaml"
        file_content = b"xxxxx"
        relpath = "licenses/metadata.yaml"

        class MockResponse:
            content = file_content
            status_code = 200

        class MockResolverMatch:
            def __init__(self, func):
                self.func = func
                self.args = []
                self.kwargs = {}

        mock_view_metadata = MagicMock()
        mock_view_metadata.return_value = MockResponse()

        with mock.patch("licenses.utils.save_bytes_to_file") as mock_save:
            with mock.patch.object(URLResolver, "resolve") as mock_resolve:
                mock_resolve.return_value = MockResolverMatch(
                    func=mock_view_metadata
                )
                utils.save_url_as_static_file(output_dir, url, relpath)

        self.assertEqual([call(url)], mock_resolve.call_args_list)
        self.assertEqual(
            [call(request=mock.ANY)], mock_view_metadata.call_args_list
        )
        self.assertEqual(
            [call(file_content, "/output/licenses/metadata.yaml")],
            mock_save.call_args_list,
        )

    def test_save_url_as_static_file_200_html(self):
        output_dir = "/output"
        url = "/licenses/by/4.0/"
        file_content = b"<html><body><p>HI</body></html>"
        relpath = "licenses/by/4.0/deed.en.html"

        class MockResponse:
            content = file_content
            status_code = 200

        class MockResolverMatch:
            def __init__(self, func):
                self.func = func
                self.args = []
                self.kwargs = {}

        mock_view_html = MagicMock()
        mock_view_html.return_value = MockResponse()

        with mock.patch("licenses.utils.save_bytes_to_file") as mock_save:
            with mock.patch.object(URLResolver, "resolve") as mock_resolve:
                mock_resolve.return_value = MockResolverMatch(
                    func=mock_view_html
                )
                utils.save_url_as_static_file(
                    output_dir, url, relpath, html=True
                )

        self.assertEqual([call(url)], mock_resolve.call_args_list)
        self.assertEqual(
            [call(request=mock.ANY)], mock_view_html.call_args_list
        )
        self.assertEqual(
            [
                call(
                    b"<html>\n <body>\n  <p>\n   HI\n  </p>\n </body>\n"
                    b"</html>",
                    "/output/licenses/by/4.0/deed.en.html",
                )
            ],
            mock_save.call_args_list,
        )


class GetJurisdictionCodeTest(TestCase):
    def test_get_code_from_jurisdiction_url(self):
        # Just returns the last portion of the path
        self.assertEqual(
            "foo",
            utils.get_code_from_jurisdiction_url(
                "http://example.com/bar/foo/"
            ),
        )
        self.assertEqual(
            "foo",
            utils.get_code_from_jurisdiction_url("http://example.com/bar/foo"),
        )
        self.assertEqual(
            "", utils.get_code_from_jurisdiction_url("http://example.com")
        )


class ParseLegalcodeFilenameTest(TestCase):
    def test_parse_legal_code_filename(self):
        data = [
            (
                "by_1.0.html",
                {
                    "canonical_url": (
                        "https://creativecommons.org/licenses/by/1.0/"
                    ),
                    "unit": "by",
                    "version": "1.0",
                    "deed_only": False,
                    "deprecated_on": None,
                    "jurisdiction_code": "",
                    "language_code": "en",
                    "category": "licenses",
                },
            ),
            (
                "by_3.0_es_ast",
                {
                    "canonical_url": (
                        "https://creativecommons.org/licenses/by/3.0/es/"
                    ),
                    "unit": "by",
                    "version": "3.0",
                    "deed_only": False,
                    "deprecated_on": None,
                    "jurisdiction_code": "es",
                    "language_code": "ast",
                    "category": "licenses",
                },
            ),
            (
                "by_3.0_rs_sr-Cyrl.html",
                {
                    "canonical_url": (
                        "https://creativecommons.org/licenses/by/3.0/rs/"
                    ),
                    "unit": "by",
                    "version": "3.0",
                    "deed_only": False,
                    "deprecated_on": None,
                    "jurisdiction_code": "rs",
                    "language_code": "sr",
                    "category": "licenses",
                },
            ),
            (
                "devnations_2.0.html",
                {
                    "canonical_url": (
                        "https://creativecommons.org/licenses/devnations/2.0/"
                    ),
                    "unit": "devnations",
                    "version": "2.0",
                    "deed_only": False,
                    "deprecated_on": "2007-06-04",
                    "jurisdiction_code": "",
                    "language_code": "en",
                    "category": "licenses",
                },
            ),
            (
                "LGPL_2.1.html",
                None,
            ),
            (
                "samplingplus_1.0",
                {
                    "canonical_url": (
                        "https://creativecommons.org/licenses/sampling+/1.0/"
                    ),
                    "unit": "sampling+",
                    "version": "1.0",
                    "deed_only": False,
                    "deprecated_on": "2011-09-12",
                    "jurisdiction_code": "",
                    "language_code": "en",
                    "category": "licenses",
                },
            ),
            (
                "zero_1.0_fi.html",
                {
                    "canonical_url": (
                        "https://creativecommons.org/publicdomain/zero/1.0/"
                    ),
                    "unit": "zero",
                    "version": "1.0",
                    "deed_only": False,
                    "deprecated_on": None,
                    "jurisdiction_code": "",
                    "language_code": "fi",
                    "category": "publicdomain",
                },
            ),
            (
                "nc-samplingplus_1.0.html",
                {
                    "canonical_url": (
                        "https://creativecommons.org/licenses/nc-sampling+/"
                        "1.0/"
                    ),
                    "unit": "nc-sampling+",
                    "version": "1.0",
                    "deed_only": False,
                    "deprecated_on": "2011-09-12",
                    "jurisdiction_code": "",
                    "language_code": "en",
                    "category": "licenses",
                },
            ),
            (
                "publicdomain_1.0.html",
                {
                    "canonical_url": (
                        "https://creativecommons.org/publicdomain/"
                        "publicdomain/1.0/us/"
                    ),
                    "unit": "publicdomain",
                    "version": "1.0",
                    "deed_only": True,
                    "deprecated_on": "2010-10-11",
                    "jurisdiction_code": "us",
                    "language_code": "en",
                    "category": "publicdomain",
                },
            ),
        ]
        for filename, expected_result in data:
            with self.subTest(filename):
                result = utils.parse_legal_code_filename(filename)
                self.assertEqual(expected_result, result)
        with self.assertRaisesMessage(ValueError, "Invalid language_code="):
            utils.parse_legal_code_filename("by_3.0_es_aaa")
        with self.assertRaisesMessage(ValueError, "What language? "):
            utils.parse_legal_code_filename("by_3.0_zz")


class GetLicenseUtilityTest(TestCase):
    """Test django-distill utility functions for
    generating an iterable of license dictionaries
    """

    def setUp(self):
        self.license1 = LicenseFactory(unit="by", version="4.0")
        self.license2 = LicenseFactory(unit="by-nc", version="4.0")
        self.license3 = LicenseFactory(
            unit="by-nd", version="3.0", jurisdiction_code="hk"
        )
        self.license4 = LicenseFactory(
            unit="by-nc-sa", version="3.0", jurisdiction_code="us"
        )
        self.license5 = LicenseFactory(
            unit="by-na", version="3.0", jurisdiction_code="nl"
        )
        self.license6 = LicenseFactory(unit="by", version="")  # zero
        self.license7 = LicenseFactory(unit="by", version="2.5")
        self.license8 = LicenseFactory(unit="by", version="2.0")
        self.license9 = LicenseFactory(unit="by", version="2.1")

        for license in License.objects.all():
            LegalCodeFactory(license=license, language_code="en")
            LegalCodeFactory(license=license, language_code="fr")


class TestComputeCanonicalURL(TestCase):
    def test_by_nc_40(self):
        self.assertEqual(
            "https://creativecommons.org/licenses/by-nc/4.0/",
            utils.compute_canonical_url(
                category="licenses",
                unit="by-nc",
                version="4.0",
                jurisdiction_code="",
            ),
        )

    def test_bsd(self):
        self.assertEqual(
            "https://creativecommons.org/licenses/BSD/",
            utils.compute_canonical_url(
                category="licenses",
                unit="BSD",
                version="",
                jurisdiction_code="",
            ),
        )

    def test_mit(self):
        self.assertEqual(
            "https://creativecommons.org/licenses/MIT/",
            utils.compute_canonical_url(
                category="licenses",
                unit="MIT",
                version="",
                jurisdiction_code="",
            ),
        )

    def test_gpl20(self):
        self.assertEqual(
            "https://creativecommons.org/licenses/GPL/2.0/",
            utils.compute_canonical_url(
                category="licenses",
                unit="GPL",
                version="2.0",
                jurisdiction_code="",
            ),
        )

    def test_30_nl(self):
        self.assertEqual(
            "https://creativecommons.org/licenses/by/3.0/nl/",
            utils.compute_canonical_url(
                category="licenses",
                unit="by",
                version="3.0",
                jurisdiction_code="nl",
            ),
        )


class TestMisc(TestCase):
    def test_validate_list_is_all_text(self):
        utils.validate_list_is_all_text(["a", "b"])
        with self.assertRaises(ValueError):
            utils.validate_list_is_all_text(["a", 1])
        with self.assertRaises(ValueError):
            utils.validate_list_is_all_text(["a", 4.2])
        with self.assertRaises(ValueError):
            utils.validate_list_is_all_text(["a", object()])
        soup = BeautifulSoup("<span>foo</span>", "lxml")
        navstring = soup.span.string
        out = utils.validate_list_is_all_text([navstring])
        self.assertEqual(["foo"], out)
        self.assertEqual(
            [["foo"]], utils.validate_list_is_all_text([[navstring]])
        )
        self.assertEqual(
            [{"a": "foo"}], utils.validate_list_is_all_text([{"a": navstring}])
        )

    def test_validate_dictionary_is_all_text(self):
        utils.validate_dictionary_is_all_text({"1": "a", "2": "b"})
        with self.assertRaises(ValueError):
            utils.validate_dictionary_is_all_text({"1": "a", "2": 1})
        with self.assertRaises(ValueError):
            utils.validate_dictionary_is_all_text({"1": "a", "2": 3.14})
        with self.assertRaises(ValueError):
            utils.validate_dictionary_is_all_text({"1": "a", "2": object()})
        soup = BeautifulSoup("<span>foo</span>", "lxml")
        navstring = soup.span.string
        self.assertEqual(
            {"a": "foo"},
            utils.validate_dictionary_is_all_text({"a": navstring}),
        )
        self.assertEqual(
            {"a": ["foo"]},
            utils.validate_dictionary_is_all_text({"a": [navstring]}),
        )
        self.assertEqual(
            {"a": {"b": "foo"}},
            utils.validate_dictionary_is_all_text({"a": {"b": "foo"}}),
        )

    def test_save_dict_to_pofile(self):
        mock_pofile = MagicMock()
        mock_pofile.append = MagicMock()
        messages = {"a": "one", "b": "two"}
        utils.save_dict_to_pofile(mock_pofile, messages)
        self.assertEqual([], mock_pofile.call_args_list)
        self.assertEqual(2, len(mock_pofile.append.call_args_list))
        args, kwargs = mock_pofile.append.call_args_list[0]
        self.assertTrue(isinstance(args[0], POEntry))

    def test_strip_list_whitespace(self):
        expected_list = ["left", "right", "center"]
        left_list = [" left", " right", " center"]
        right_list = ["left ", "right ", "center "]
        center_list = [" left ", " right ", " center "]
        self.assertEqual(
            utils.strip_list_whitespace("left", left_list), expected_list
        )
        self.assertEqual(
            utils.strip_list_whitespace("right", right_list), expected_list
        )
        self.assertEqual(
            utils.strip_list_whitespace("center", center_list), expected_list
        )

    def test_cleanup_current_branch_output(self):
        expected_list = ["some-branch", "another-branch", "main"]
        unmodified_list = ["some-branch", "* another-branch", "main"]
        self.assertEqual(
            utils.cleanup_current_branch_output(unmodified_list), expected_list
        )

    def test_b64encode_string(self):
        string = "abc123"
        expected_encoded = "YWJjMTIz"
        encoded_string = utils.b64encode_string(string)
        self.assertEqual(expected_encoded, encoded_string)


class CleanStringTest(TestCase):
    def test_clean_string(self):
        data = [
            # input, expected result
            ("foo", "foo"),
            ("foo bar", "foo bar"),
            ("foo  bar", "foo bar"),
            ("foo   bar", "foo bar"),
            (" x ", "x"),
            ("one\ntwo", "one two"),
        ]
        for input, expected in data:
            with self.subTest(input):
                self.assertEqual(expected, utils.clean_string(input))
