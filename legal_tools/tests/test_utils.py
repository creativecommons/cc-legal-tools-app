# Standard library
import logging
import os
import tempfile
from io import StringIO
from unittest import mock
from unittest.mock import MagicMock

# Third-party
from bs4 import BeautifulSoup
from django.test import TestCase
from django.urls import Resolver404, URLResolver

# First-party/Local
from legal_tools import utils
from legal_tools.models import Tool
from .factories import LegalCodeFactory, ToolFactory


class LoggingTest(TestCase):
    def test_init_utils_logger(self):
        utils.init_utils_logger(None)
        self.assertEqual("legal_tools.utils", utils.LOG.name)

        logger = logging.getLogger(__name__)
        utils.init_utils_logger(logger)
        self.assertEqual("legal_tools.tests.test_utils", utils.LOG.name)


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

        with mock.patch("legal_tools.utils.save_bytes_to_file"):
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

    def test_save_url_as_static_file_200(self):
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

        with mock.patch("legal_tools.utils.save_bytes_to_file") as mock_save:
            with mock.patch.object(URLResolver, "resolve") as mock_resolve:
                mock_resolve.return_value = MockResolverMatch(
                    func=mock_view_metadata
                )
                utils.save_url_as_static_file(output_dir, url, relpath)

        mock_resolve.assert_called_with(url)
        mock_view_metadata.assert_called()
        mock_save.assert_called_with(
            file_content, "/output/licenses/metadata.yaml"
        )

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

    def test_save_redirect(self):
        output_dir = "/OUTPUT_DIR"
        redirect_data = {
            "destination": "DESTINATION",
            "language_code": "LANGUAGE_CODE",
            "redirect_file": ("FILE_PATH"),
            "title": "TITLE",
        }

        with mock.patch(
            "legal_tools.utils.render_redirect",
            return_value="STRING",
        ) as mock_render:
            with mock.patch(
                "legal_tools.utils.save_bytes_to_file"
            ) as mock_save:
                utils.save_redirect(output_dir, redirect_data)

        mock_render.assert_called_with(
            title="TITLE",
            destination="DESTINATION",
            language_code="LANGUAGE_CODE",
        )
        mock_save.assert_called_with("STRING", "/OUTPUT_DIR/FILE_PATH")


class ParseLegalcodeFilenameTest(TestCase):
    def test_parse_legal_code_filename(self):
        data = [
            (
                "by_1.0.html",
                {
                    "base_url": (
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
                    "base_url": (
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
                    "base_url": (
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
                    "base_url": (
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
                    "base_url": (
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
                    "base_url": (
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
                    "base_url": (
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
                "certification_1.0.html",
                {
                    "base_url": (
                        "https://creativecommons.org/publicdomain/"
                        "certification/1.0/us/"
                    ),
                    "unit": "certification",
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


class GetToolUtilityTest(TestCase):
    """
    Test django-distill utility functions for generating an iterable of legal
    tool dictionaries
    """

    def setUp(self):
        self.license1 = ToolFactory(unit="by", version="4.0")
        self.license2 = ToolFactory(unit="by-nc", version="4.0")
        self.license3 = ToolFactory(
            unit="by-nd", version="3.0", jurisdiction_code="hk"
        )
        self.license4 = ToolFactory(
            unit="by-nc-sa", version="3.0", jurisdiction_code="us"
        )
        self.license5 = ToolFactory(
            unit="by-na", version="3.0", jurisdiction_code="nl"
        )
        self.license6 = ToolFactory(unit="by", version="")  # zero
        self.license7 = ToolFactory(unit="by", version="2.5")
        self.license8 = ToolFactory(unit="by", version="2.0")
        self.license9 = ToolFactory(unit="by", version="2.1")

        for tool in Tool.objects.all():
            LegalCodeFactory(tool=tool, language_code="en")
            LegalCodeFactory(tool=tool, language_code="fr")


class TestComputeCanonicalURL(TestCase):
    def test_by_nc_40(self):
        self.assertEqual(
            "https://creativecommons.org/licenses/by-nc/4.0/",
            utils.compute_base_url(
                category="licenses",
                unit="by-nc",
                version="4.0",
                jurisdiction_code="",
            ),
        )

    def test_bsd(self):
        self.assertEqual(
            "https://creativecommons.org/licenses/BSD/",
            utils.compute_base_url(
                category="licenses",
                unit="BSD",
                version="",
                jurisdiction_code="",
            ),
        )

    def test_mit(self):
        self.assertEqual(
            "https://creativecommons.org/licenses/MIT/",
            utils.compute_base_url(
                category="licenses",
                unit="MIT",
                version="",
                jurisdiction_code="",
            ),
        )

    def test_gpl20(self):
        self.assertEqual(
            "https://creativecommons.org/licenses/GPL/2.0/",
            utils.compute_base_url(
                category="licenses",
                unit="GPL",
                version="2.0",
                jurisdiction_code="",
            ),
        )

    def test_30_nl(self):
        self.assertEqual(
            "https://creativecommons.org/licenses/by/3.0/nl/",
            utils.compute_base_url(
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

    def test_cleanup_current_branch_output(self):
        expected_list = ["some-branch", "another-branch", "main"]
        unmodified_list = ["some-branch", "* another-branch", "main"]
        self.assertEqual(
            utils.cleanup_current_branch_output(unmodified_list), expected_list
        )


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


class UpdatePropertiesTest(TestCase):
    def test_update_is_replaced_by(self):
        # Setup
        license4by = ToolFactory(category="licenses", unit="by", version="4.0")
        license4bysa = ToolFactory(
            category="licenses", unit="by-sa", version="4.0"
        )
        license3by = ToolFactory(category="licenses", unit="by", version="3.0")
        license2by = ToolFactory(category="licenses", unit="by", version="2.0")
        license1by = ToolFactory(category="licenses", unit="by", version="1.0")
        license1xx = ToolFactory(category="licenses", unit="xx", version="1.0")

        # First run
        utils.update_is_replaced_by()
        license4by.refresh_from_db()
        self.assertIsNone(license4by.is_replaced_by)
        license4bysa.refresh_from_db()
        self.assertIsNone(license4bysa.is_replaced_by)
        license3by.refresh_from_db()
        self.assertEqual(license3by.is_replaced_by, license4by)
        license2by.refresh_from_db()
        self.assertEqual(license2by.is_replaced_by, license4by)
        license1by.refresh_from_db()
        self.assertEqual(license1by.is_replaced_by, license4by)
        license1xx.refresh_from_db()
        self.assertIsNone(license1xx.is_replaced_by)

        # Subsequent run
        utils.update_is_replaced_by()
        license4by.refresh_from_db()
        self.assertIsNone(license4by.is_replaced_by)
        license4bysa.refresh_from_db()
        self.assertIsNone(license4bysa.is_replaced_by)
        license3by.refresh_from_db()
        self.assertEqual(license3by.is_replaced_by, license4by)
        license2by.refresh_from_db()
        self.assertEqual(license2by.is_replaced_by, license4by)
        license1by.refresh_from_db()
        self.assertEqual(license1by.is_replaced_by, license4by)
        license1xx.refresh_from_db()
        self.assertIsNone(license1xx.is_replaced_by)

    def test_update_source(self):
        def tool(unit, version, jurisdiction_code=None):
            if jurisdiction_code is None:
                jurisdiction_code = ""
            return Tool.objects.get(
                category="licenses",
                unit=unit,
                version=version,
                jurisdiction_code=jurisdiction_code,
            )

        tools = [
            ["by", "4.0", ""],
            ["by", "3.0", ""],
            ["by", "3.0", "ar"],
            ["by", "2.5", "bg"],
            ["by", "2.0", ""],
            ["by-nc", "4.0", ""],
            ["by-nc", "3.0", ""],
            ["by-nc", "2.5", ""],
            ["by-nc", "1.0", ""],
        ]

        # Setup
        for unit, version, jurisdiction_code in tools:
            ToolFactory(
                category="licenses",
                unit=unit,
                version=version,
                jurisdiction_code=jurisdiction_code,
            )

        # Verify setup
        for unit, version, jurisdiction_code in tools:
            self.assertIsNone(tool(unit, version, jurisdiction_code).source)

        # Add some bad data
        tool_object = tool("by-nc", "1.0")
        tool_object.source = tool("by-nc", "3.0")
        tool_object.save()

        # Test
        def validate_udpate_source():
            utils.update_source()

            self.assertEqual(tool("by", "4.0").source, tool("by", "3.0"))
            self.assertEqual(tool("by", "3.0").source, tool("by", "2.0"))
            self.assertEqual(tool("by", "3.0", "ar").source, tool("by", "3.0"))
            self.assertEqual(tool("by", "2.5", "bg").source, tool("by", "2.0"))
            self.assertIsNone(tool("by", "2.0").source)

            self.assertEqual(tool("by-nc", "4.0").source, tool("by-nc", "3.0"))
            self.assertEqual(tool("by-nc", "3.0").source, tool("by-nc", "2.5"))
            self.assertEqual(tool("by-nc", "2.5").source, tool("by-nc", "1.0"))
            self.assertIsNone(tool("by-nc", "1.0").source)

        # First run
        validate_udpate_source()

        # Subsequent run to test with wrong data and verify behavior of
        # repeated runs
        validate_udpate_source()
