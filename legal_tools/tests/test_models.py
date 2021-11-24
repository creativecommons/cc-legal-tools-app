# Standard library
from unittest import mock

# Third-party
import polib
from django.conf import settings
from django.test import TestCase, override_settings
from django.utils.translation import override

# First-party/Local
from legal_tools import FREEDOM_LEVEL_MAX, FREEDOM_LEVEL_MID, FREEDOM_LEVEL_MIN
from legal_tools.models import LegalCode, Tool
from legal_tools.tests.factories import (
    LegalCodeFactory,
    ToolFactory,
    TranslationBranchFactory,
)

# TODO: update as part of translation rewrite
# from i18n.transifex import TransifexHelper
# from legal_tools.tests.test_transifex import TEST_TRANSIFEX_SETTINGS


class LegalCodeQuerySetTest(TestCase):
    def test_translated(self):
        bylicense30ported = ToolFactory(
            unit="by-nc", version="3.0", jurisdiction_code="ar"
        )
        bylicense30unported = ToolFactory(
            unit="by-nc", version="3.0", jurisdiction_code=""
        )

        bylicense40 = ToolFactory(
            unit="by-nc", version="4.0", jurisdiction_code=""
        )

        zerov1declaration = ToolFactory(
            unit="zero", version="1.0", jurisdiction_code=""
        )

        should_be_translated = [
            LegalCodeFactory(tool=bylicense40),
            LegalCodeFactory(tool=zerov1declaration),
        ]
        should_not_be_translated = [
            LegalCodeFactory(tool=bylicense30ported),
            LegalCodeFactory(tool=bylicense30unported),
        ]
        self.assertCountEqual(
            should_be_translated, list(LegalCode.objects.translated())
        )
        self.assertCountEqual(
            should_not_be_translated,
            set(LegalCode.objects.all()) - set(LegalCode.objects.translated()),
        )

    def test_valid(self):
        bylicense30ported = ToolFactory(
            unit="by-nc", version="3.0", jurisdiction_code="ar"
        )
        bylicense30unported = ToolFactory(
            unit="by-nc", version="3.0", jurisdiction_code=""
        )
        nonbylicense30ported = ToolFactory(
            unit="xyz", version="3.0", jurisdiction_code="ar"
        )
        nonbylicense30unported = ToolFactory(
            unit="xyz", version="3.0", jurisdiction_code=""
        )

        bylicense40 = ToolFactory(
            unit="by-nc", version="4.0", jurisdiction_code=""
        )
        nonbylicense40 = ToolFactory(
            unit="xyz", version="4.0", jurisdiction_code=""
        )

        zerov1declaration = ToolFactory(
            unit="zero", version="1.0", jurisdiction_code=""
        )
        nonzerov1declaration = ToolFactory(
            unit="xyz", version="1.0", jurisdiction_code=""
        )

        # Test valid()
        should_be_valid = [
            LegalCodeFactory(tool=bylicense30ported),
            LegalCodeFactory(tool=bylicense30unported),
            LegalCodeFactory(tool=bylicense40),
            LegalCodeFactory(tool=zerov1declaration),
        ]
        should_not_be_valid = [
            LegalCodeFactory(tool=nonbylicense30ported),
            LegalCodeFactory(tool=nonbylicense30unported),
            LegalCodeFactory(tool=nonbylicense40),
            LegalCodeFactory(tool=nonzerov1declaration),
        ]
        self.assertCountEqual(should_be_valid, list(LegalCode.objects.valid()))
        self.assertCountEqual(
            should_not_be_valid,
            set(LegalCode.objects.all()) - set(LegalCode.objects.valid()),
        )
        # Test validgroups()
        self.assertCountEqual(
            should_be_valid,
            list(LegalCode.objects.validgroups()["Licenses 4.0"])
            + list(LegalCode.objects.validgroups()["Licenses 3.0"])
            + list(LegalCode.objects.validgroups()["Public Domain all"]),
        )
        self.assertCountEqual(
            should_not_be_valid,
            set(LegalCode.objects.all())
            - set(
                list(LegalCode.objects.validgroups()["Licenses 4.0"])
                + list(LegalCode.objects.validgroups()["Licenses 3.0"])
                + list(LegalCode.objects.validgroups()["Public Domain all"])
            ),
        )


class LegalCodeModelTest(TestCase):
    def test_str(self):
        LegalCodeFactory()
        legal_code = LegalCode.objects.first()
        self.assertEqual(
            str(legal_code),
            f"LegalCode<{legal_code.language_code},"
            f" {str(legal_code.tool)}>",
        )

    def test_translation_domain(self):
        data = [
            # (expected, unit, version, jurisdiction, language)
            ("by-sa_30", "by-sa", "3.0", "", "fr"),
            ("by-sa_30_xx", "by-sa", "3.0", "xx", "fr"),
        ]

        for expected, unit, version, jurisdiction, language in data:
            with self.subTest(expected):
                legal_code = LegalCodeFactory(
                    tool__unit=unit,
                    tool__version=version,
                    tool__jurisdiction_code=jurisdiction,
                    language_code=language,
                )
                self.assertEqual(expected, legal_code.translation_domain)

    @override_settings(DATA_REPOSITORY_DIR="/foo")
    def test_translation_filename(self):
        data = [
            # (expected, unit, version, jurisdiction, language)
            (
                "/foo/legalcode/de/LC_MESSAGES/by-sa_03.po",
                "by-sa",
                "0.3",
                "",
                "de",
            ),
            (
                "/foo/legalcode/de/LC_MESSAGES/by-sa_03_xx.po",
                "by-sa",
                "0.3",
                "xx",
                "de",
            ),
        ]

        for expected, unit, version, jurisdiction, language in data:
            with self.subTest(expected):
                tool = ToolFactory(
                    unit=unit,
                    version=version,
                    jurisdiction_code=jurisdiction,
                )
                self.assertEqual(
                    expected,
                    LegalCodeFactory(
                        tool=tool, language_code=language
                    ).translation_filename(),
                )

    # NOTE: plaintext functionality disabled
    # def test_plain_text_url(self):
    #     lc0 = LegalCodeFactory(
    #         tool__unit="by",
    #         tool__version="4.0",
    #         tool__jurisdiction_code="",
    #         language_code="en",
    #     )
    #     lc1 = LegalCodeFactory(
    #         tool__unit="by",
    #         tool__version="4.0",
    #         tool__jurisdiction_code="",
    #         language_code="fr",
    #     )
    #     lc2 = LegalCodeFactory(
    #         tool__unit="by",
    #         tool__version="4.0",
    #         tool__jurisdiction_code="",
    #         language_code="ar",
    #     )
    #     self.assertEqual(
    #         lc0.plain_text_url,
    #         f"{lc0.legal_code_url.replace('legalcode.en', 'legalcode.txt')}",
    #     )
    #     self.assertEqual(lc1.plain_text_url, "")
    #     self.assertEqual(lc2.plain_text_url, "")

    def test_get_pofile(self):
        legal_code = LegalCodeFactory()
        test_pofile = polib.POFile()
        test_translation_filename = "/dev/null"
        with mock.patch.object(LegalCode, "translation_filename") as mock_tf:
            mock_tf.return_value = test_translation_filename
            with mock.patch.object(polib, "pofile") as mock_pofile:
                mock_pofile.return_value = test_pofile
                result = legal_code.get_pofile()
        mock_pofile.assert_called_with("", encoding="utf-8")
        self.assertEqual(test_pofile, result)

    @override_settings(DATA_REPOSITORY_DIR="/some/dir")
    def test_get_english_pofile_path(self):
        legal_code = LegalCodeFactory(
            tool__version="4.0",
            tool__unit="by-sa",
            language_code="de",
        )
        legal_code_en = LegalCodeFactory(
            tool=legal_code.tool, language_code=settings.LANGUAGE_CODE
        )
        expected_path = "/some/dir/legalcode/en/LC_MESSAGES/by-sa_40.po"

        with mock.patch.object(
            Tool, "get_legal_code_for_language_code"
        ) as mock_glfl:
            mock_glfl.return_value = legal_code_en
            self.assertEqual(
                expected_path, legal_code.get_english_pofile_path()
            )
            self.assertEqual(
                expected_path, legal_code_en.get_english_pofile_path()
            )
        mock_glfl.assert_called_with(settings.LANGUAGE_CODE)

    @override_settings(DATA_REPOSITORY_DIR="/some/dir")
    def test_get_translation_object(self):
        # get_translation_object on the model calls the
        # i18n.utils.get_translation_object.
        legal_code = LegalCodeFactory(
            tool__version="4.0",
            tool__unit="by-sa",
            language_code="de",
        )

        with mock.patch(
            "legal_tools.models.get_translation_object"
        ) as mock_djt:
            legal_code.get_translation_object()
        mock_djt.assert_called_with(
            django_language_code="de", domain="by-sa_40"
        )

    def test_branch_name(self):
        legal_code = LegalCodeFactory(
            tool__version="4.0",
            tool__unit="by-sa",
            language_code="de",
        )
        self.assertEqual("cc4-de", legal_code.branch_name())
        legal_code = LegalCodeFactory(
            tool__version="3.5",
            tool__unit="other",
            language_code="de",
        )
        self.assertEqual("other-35-de", legal_code.branch_name())
        legal_code = LegalCodeFactory(
            tool__version="3.5",
            tool__unit="other",
            language_code="de",
            tool__jurisdiction_code="xyz",
        )
        self.assertEqual("other-35-de-xyz", legal_code.branch_name())

    def test_has_english(self):
        tool = ToolFactory()
        lc_fr = LegalCodeFactory(tool=tool, language_code="fr")
        self.assertFalse(lc_fr.has_english())
        lc_en = LegalCodeFactory(tool=tool, language_code="en")
        self.assertTrue(lc_fr.has_english())
        self.assertTrue(lc_en.has_english())

    def _test_get_publish_files(self, data):
        for (
            category,
            version,
            unit,
            jurisdiction_code,
            language_code,
            expected_deed_path,
            expected_deed_symlinks,
            expected_deed_redirects_data,
            expected_tool_path,
            expected_tool_symlinks,
            expected_tool_redirects_data,
        ) in data:
            tool = ToolFactory(
                category=category,
                unit=unit,
                version=version,
                jurisdiction_code=jurisdiction_code,
            )
            legal_code = LegalCodeFactory(
                tool=tool, language_code=language_code
            )
            self.assertEqual(
                [
                    expected_deed_path,
                    expected_deed_symlinks,
                    expected_deed_redirects_data,
                ],
                legal_code.get_publish_files("deed"),
            )
            self.assertEqual(
                [
                    expected_tool_path,
                    expected_tool_symlinks,
                    expected_tool_redirects_data,
                ],
                legal_code.get_publish_files("legalcode"),
            )

    def test_get_publish_files_by4(self):
        """
        4.0:
            Formula
                CATEGORY/UNIT/VERSION/DOCUMENT.LANG.html
            Examples
                licenses/by-nc-nd/4.0/deed.en-us.html
                licenses/by-nc-nd/4.0/legalcode.en-us.html
                licenses/by/4.0/deed.nl.html
                licenses/by/4.0/legalcode.nl.html
        """
        self._test_get_publish_files(
            [
                (
                    "licenses",
                    "4.0",
                    "by-nc-nd",
                    "",
                    "en",
                    "licenses/by-nc-nd/4.0/deed.en.html",
                    ["deed.html", "index.html"],
                    [
                        {
                            "destination": "deed.en",
                            "language_code": "en",
                            "redirect_file": (
                                "licenses/by-nc-nd/4.0/deed.en-us.html"
                            ),
                            "title": "",
                        },
                        {
                            "destination": "deed.en",
                            "language_code": "en",
                            "redirect_file": (
                                "licenses/by-nc-nd/4.0/deed.en_us.html"
                            ),
                            "title": "",
                        },
                    ],
                    "licenses/by-nc-nd/4.0/legalcode.en.html",
                    ["legalcode.html"],
                    [
                        {
                            "destination": "legalcode.en",
                            "language_code": "en",
                            "redirect_file": (
                                "licenses/by-nc-nd/4.0/legalcode.en-us.html"
                            ),
                            "title": "",
                        },
                        {
                            "destination": "legalcode.en",
                            "language_code": "en",
                            "redirect_file": (
                                "licenses/by-nc-nd/4.0/legalcode.en_us.html"
                            ),
                            "title": "",
                        },
                    ],
                ),
                (
                    "licenses",
                    "4.0",
                    "by",
                    "",
                    "nl",
                    "licenses/by/4.0/deed.nl.html",
                    [],
                    [],
                    "licenses/by/4.0/legalcode.nl.html",
                    [],
                    [],
                ),
            ]
        )
        self._test_get_publish_files(
            [
                (
                    "licenses",
                    "4.0",
                    "by",
                    "",
                    "zh-hans",
                    "licenses/by/4.0/deed.zh-hans.html",
                    [],
                    [
                        {
                            "destination": "deed.zh-hans",
                            "language_code": "zh-hans",
                            "redirect_file": "licenses/by/4.0/deed.zh.html",
                            "title": "",
                        },
                        {
                            "destination": "deed.zh-hans",
                            "language_code": "zh-hans",
                            "redirect_file": (
                                "licenses/by/4.0/deed.zh-cn.html"
                            ),
                            "title": "",
                        },
                        {
                            "destination": "deed.zh-hans",
                            "language_code": "zh-hans",
                            "redirect_file": (
                                "licenses/by/4.0/deed.zh_cn.html"
                            ),
                            "title": "",
                        },
                    ],
                    "licenses/by/4.0/legalcode.zh-hans.html",
                    [],
                    [
                        {
                            "destination": "legalcode.zh-hans",
                            "language_code": "zh-hans",
                            "redirect_file": (
                                "licenses/by/4.0/legalcode.zh.html"
                            ),
                            "title": "",
                        },
                        {
                            "destination": "legalcode.zh-hans",
                            "language_code": "zh-hans",
                            "redirect_file": (
                                "licenses/by/4.0/legalcode.zh-cn.html"
                            ),
                            "title": "",
                        },
                        {
                            "destination": "legalcode.zh-hans",
                            "language_code": "zh-hans",
                            "redirect_file": (
                                "licenses/by/4.0/legalcode.zh_cn.html"
                            ),
                            "title": "",
                        },
                    ],
                ),
            ]
        )

    def test_get_publish_files_by3(self):
        """
        3.0 unported
            Formula
                CATEGORY/UNIT/VERSION/JURISDICTION/DOCUMENT.LANG.html
            Examples
                licenses/by/3.0/deed.en.html
                licenses/by/3.0/legalcode.en.html

        3.0 ported
            Formula
                CATEGORY/UNIT/VERSION/JURISDICTION/DOCUMENT.LANG.html
            Examples
                licenses/by/3.0/ca/deed.en.html
                licenses/by/3.0/ca/legalcode.en.html
                licenses/by-sa/3.0/ca/deed.fr.html
                licenses/by-sa/3.0/ca/legalcode.fr.html
        """
        # Unported
        self._test_get_publish_files(
            [
                (
                    "licenses",
                    "3.0",
                    "by",
                    "",
                    "en",
                    "licenses/by/3.0/deed.en.html",
                    ["deed.html", "index.html"],
                    [
                        {
                            "destination": "deed.en",
                            "language_code": "en",
                            "redirect_file": (
                                "licenses/by/3.0/deed.en-us.html"
                            ),
                            "title": "",
                        },
                        {
                            "destination": "deed.en",
                            "language_code": "en",
                            "redirect_file": (
                                "licenses/by/3.0/deed.en_us.html"
                            ),
                            "title": "",
                        },
                    ],
                    "licenses/by/3.0/legalcode.en.html",
                    ["legalcode.html"],
                    [
                        {
                            "destination": "legalcode.en",
                            "language_code": "en",
                            "redirect_file": (
                                "licenses/by/3.0/legalcode.en-us.html"
                            ),
                            "title": "",
                        },
                        {
                            "destination": "legalcode.en",
                            "language_code": "en",
                            "redirect_file": (
                                "licenses/by/3.0/legalcode.en_us.html"
                            ),
                            "title": "",
                        },
                    ],
                ),
            ]
        )
        # Ported with multiple languages
        self._test_get_publish_files(
            [
                (
                    "licenses",
                    "3.0",
                    "by",
                    "ca",
                    "en",
                    "licenses/by/3.0/ca/deed.en.html",
                    ["deed.html", "index.html"],
                    [
                        {
                            "destination": "deed.en",
                            "language_code": "en",
                            "redirect_file": (
                                "licenses/by/3.0/ca/deed.en-us.html"
                            ),
                            "title": "",
                        },
                        {
                            "destination": "deed.en",
                            "language_code": "en",
                            "redirect_file": (
                                "licenses/by/3.0/ca/deed.en_us.html"
                            ),
                            "title": "",
                        },
                    ],
                    "licenses/by/3.0/ca/legalcode.en.html",
                    ["legalcode.html"],
                    [
                        {
                            "destination": "legalcode.en",
                            "language_code": "en",
                            "redirect_file": (
                                "licenses/by/3.0/ca/legalcode.en-us.html"
                            ),
                            "title": "",
                        },
                        {
                            "destination": "legalcode.en",
                            "language_code": "en",
                            "redirect_file": (
                                "licenses/by/3.0/ca/legalcode.en_us.html"
                            ),
                            "title": "",
                        },
                    ],
                ),
            ]
        )
        self._test_get_publish_files(
            [
                (
                    "licenses",
                    "3.0",
                    "by-sa",
                    "ca",
                    "fr",
                    "licenses/by-sa/3.0/ca/deed.fr.html",
                    [],  # no symlinks
                    [],  # no redirects data
                    "licenses/by-sa/3.0/ca/legalcode.fr.html",
                    [],  # no symlinks
                    [],  # no redirects data
                ),
            ]
        )
        # Ported with single language
        self._test_get_publish_files(
            [
                (
                    "licenses",
                    "3.0",
                    "by-nc-nd",
                    "am",
                    "hy",
                    "licenses/by-nc-nd/3.0/am/deed.hy.html",
                    ["deed.html", "index.html"],
                    [],  # no redirects data
                    "licenses/by-nc-nd/3.0/am/legalcode.hy.html",
                    ["legalcode.html"],
                    [],  # no redirects data
                ),
            ]
        )

    def test_get_publish_files_zero(self):
        """
        Formula
            CATEGORY/UNIT/VERSION/DOCUMENT.LANG.html
        Examples
            publicdomain/zero/1.0/deed.en.html
            publicdomain/zero/1.0/legalcode.en.html
        """
        self._test_get_publish_files(
            [
                (
                    "publicdomain",
                    "1.0",
                    "zero",
                    "",
                    "en",
                    "publicdomain/zero/1.0/deed.en.html",
                    ["deed.html", "index.html"],
                    [
                        {
                            "destination": "deed.en",
                            "language_code": "en",
                            "redirect_file": (
                                "publicdomain/zero/1.0/deed.en-us.html"
                            ),
                            "title": "",
                        },
                        {
                            "destination": "deed.en",
                            "language_code": "en",
                            "redirect_file": (
                                "publicdomain/zero/1.0/deed.en_us.html"
                            ),
                            "title": "",
                        },
                    ],
                    "publicdomain/zero/1.0/legalcode.en.html",
                    ["legalcode.html"],
                    [
                        {
                            "destination": "legalcode.en",
                            "language_code": "en",
                            "redirect_file": (
                                "publicdomain/zero/1.0/legalcode.en-us.html"
                            ),
                            "title": "",
                        },
                        {
                            "destination": "legalcode.en",
                            "language_code": "en",
                            "redirect_file": (
                                "publicdomain/zero/1.0/legalcode.en_us.html"
                            ),
                            "title": "",
                        },
                    ],
                ),
            ]
        )
        self._test_get_publish_files(
            [
                (
                    "publicdomain",
                    "1.0",
                    "zero",
                    "",
                    "ja",
                    "publicdomain/zero/1.0/deed.ja.html",
                    [],  # no symlinks
                    [],  # no redirects data
                    "publicdomain/zero/1.0/legalcode.ja.html",
                    [],  # no symlinks
                    [],  # no redirects data
                ),
            ]
        )

    def test_get_redirect_pairs_4(self):
        tool = ToolFactory(category="license", unit="by", version="4.0")
        legal_code = LegalCodeFactory(tool=tool, language_code="nl")
        redirect_pairs = legal_code.get_redirect_pairs("deed")
        self.assertEqual(
            [["license/by/4.0/deed.NL", "license/by/4.0/deed.nl"]],
            redirect_pairs,
        )


class ToolModelTest(TestCase):
    def test_nc(self):
        self.assertFalse(ToolFactory(unit="xyz").nc)
        self.assertTrue(ToolFactory(unit="by-nc-xyz").nc)

    def test_nd(self):
        self.assertFalse(ToolFactory(unit="xyz").nd)
        self.assertTrue(ToolFactory(unit="by-nd-xyz").nd)

    def test_sa(self):
        self.assertFalse(ToolFactory(unit="xyz").sa)
        self.assertTrue(ToolFactory(unit="xyz-sa").sa)

    def test_get_metadata(self):
        # Ported
        tool = ToolFactory(
            **{
                "canonical_url": (
                    "https://creativecommons.org/licenses/by-nc/3.0/xyz/"
                ),
                "category": "licenses",
                "unit": "by-nc",
                "version": "3.0",
                "jurisdiction_code": "xyz",
                "permits_derivative_works": False,
                "permits_reproduction": False,
                "permits_distribution": True,
                "permits_sharing": True,
                "requires_share_alike": True,
                "requires_notice": True,
                "requires_attribution": True,
                "requires_source_code": True,
                "prohibits_commercial_use": True,
                "prohibits_high_income_nation_use": False,
            }
        )

        LegalCodeFactory(tool=tool, language_code="pt")
        LegalCodeFactory(tool=tool, language_code="en")

        data = tool.get_metadata()
        expected_data = {
            "jurisdiction_name": "xyz",
            "unit": "by-nc",
            "permits_derivative_works": False,
            "permits_distribution": True,
            "permits_reproduction": False,
            "permits_sharing": True,
            "prohibits_commercial_use": True,
            "prohibits_high_income_nation_use": False,
            "requires_attribution": True,
            "requires_notice": True,
            "requires_share_alike": True,
            "requires_source_code": True,
            "legal_code_languages": {
                "en": "English",
                "pt": "Portuguese",
            },
            "version": "3.0",
        }

        for key in expected_data.keys():
            self.assertEqual(expected_data[key], data[key])

        # Unported
        tool = ToolFactory(
            **{
                "canonical_url": (
                    "https://creativecommons.org/licenses/by-nc/3.0/"
                ),
                "category": "licenses",
                "unit": "by-nc",
                "version": "3.0",
                "jurisdiction_code": "",
                "permits_derivative_works": False,
                "permits_reproduction": False,
                "permits_distribution": True,
                "permits_sharing": True,
                "requires_share_alike": True,
                "requires_notice": True,
                "requires_attribution": True,
                "requires_source_code": True,
                "prohibits_commercial_use": True,
                "prohibits_high_income_nation_use": False,
            }
        )

        LegalCodeFactory(tool=tool, language_code="en")

        data = tool.get_metadata()
        expected_data = {
            "unit": "by-nc",
            "version": "3.0",
            "permits_derivative_works": False,
            "permits_distribution": True,
            "permits_reproduction": False,
            "permits_sharing": True,
            "prohibits_commercial_use": True,
            "prohibits_high_income_nation_use": False,
            "requires_attribution": True,
            "requires_notice": True,
            "requires_share_alike": True,
            "requires_source_code": True,
            "legal_code_languages": {
                "en": "English",
            },
        }

        for key in expected_data.keys():
            self.assertEqual(expected_data[key], data[key])

        # Deprecated
        tool = ToolFactory(
            **{
                "canonical_url": (
                    "https://creativecommons.org/licenses/sampling/1.0/"
                ),
                "category": "licenses",
                "unit": "sampling",
                "version": "1.0",
                "jurisdiction_code": "",
                "deprecated_on": "2007-06-04",
                "permits_derivative_works": True,
                "permits_reproduction": True,
                "permits_distribution": True,
                "permits_sharing": True,
                "requires_share_alike": False,
                "requires_notice": True,
                "requires_attribution": True,
                "requires_source_code": False,
                "prohibits_commercial_use": False,
                "prohibits_high_income_nation_use": False,
            }
        )

        LegalCodeFactory(tool=tool, language_code="en")

        data = tool.get_metadata()
        expected_data = {
            "unit": "sampling",
            "version": "1.0",
            "deprecated_on": "2007-06-04",
            "permits_derivative_works": True,
            "permits_distribution": True,
            "permits_reproduction": True,
            "permits_sharing": True,
            "prohibits_commercial_use": False,
            "prohibits_high_income_nation_use": False,
            "requires_attribution": True,
            "requires_notice": True,
            "requires_share_alike": False,
            "requires_source_code": False,
            "legal_code_languages": {
                "en": "English",
            },
        }

        for key in expected_data.keys():
            self.assertEqual(expected_data[key], data[key])

        # Deed-only
        tool = ToolFactory(
            **{
                "canonical_url": (
                    "https://creativecommons.org/publicdomain/mark/1.0/"
                ),
                "category": "publicdomain",
                "unit": "mark",
                "version": "1.0",
                "jurisdiction_code": "",
                "deed_only": True,
                "deprecated_on": "2007-06-04",
                "permits_derivative_works": True,
                "permits_reproduction": True,
                "permits_distribution": True,
                "permits_sharing": True,
                "requires_share_alike": False,
                "requires_notice": False,
                "requires_attribution": False,
                "requires_source_code": False,
                "prohibits_commercial_use": False,
                "prohibits_high_income_nation_use": False,
            }
        )

        LegalCodeFactory(tool=tool, language_code="en")

        data = tool.get_metadata()
        expected_data = {
            "unit": "mark",
            "version": "1.0",
            "deprecated_on": "2007-06-04",
            "permits_derivative_works": True,
            "permits_distribution": True,
            "permits_reproduction": True,
            "permits_sharing": True,
            "prohibits_commercial_use": False,
            "prohibits_high_income_nation_use": False,
            "requires_attribution": False,
            "requires_notice": False,
            "requires_share_alike": False,
            "requires_source_code": False,
        }

        for key in expected_data.keys():
            self.assertEqual(expected_data[key], data[key])

    def test_logos(self):
        # Every tool includes "cc-logo"
        self.assertIn("cc-logo", ToolFactory().logos())
        self.assertEqual(
            ["cc-logo", "cc-zero"], ToolFactory(unit="zero").logos()
        )
        self.assertEqual(
            ["cc-logo", "cc-by"],
            ToolFactory(
                unit="by",
                version="4.0",
                prohibits_commercial_use=False,
                requires_share_alike=False,
                permits_derivative_works=True,
            ).logos(),
        )
        self.assertEqual(
            ["cc-logo", "cc-by", "cc-nc"],
            ToolFactory(
                unit="by-nc",
                version="3.0",
                prohibits_commercial_use=True,
                requires_share_alike=False,
                permits_derivative_works=True,
            ).logos(),
        )
        self.assertEqual(
            ["cc-logo", "cc-by", "cc-nd"],
            ToolFactory(
                unit="by-nd",
                version="4.0",
                prohibits_commercial_use=False,
                requires_share_alike=False,
                permits_derivative_works=False,
            ).logos(),
        )
        self.assertEqual(
            ["cc-logo", "cc-by", "cc-sa"],
            ToolFactory(
                unit="by-sa",
                version="4.0",
                prohibits_commercial_use=False,
                requires_share_alike=True,
                permits_derivative_works=True,
            ).logos(),
        )
        self.assertEqual(
            ["cc-logo", "cc-by", "cc-nc", "cc-sa"],
            ToolFactory(
                unit="by-nc-sa",
                version="4.0",
                prohibits_commercial_use=True,
                requires_share_alike=True,
                permits_derivative_works=True,
            ).logos(),
        )
        self.assertEqual(
            ["cc-logo", "cc-by", "cc-nc", "cc-sa"],
            ToolFactory(
                unit="by-nc-sa",
                version="3.0",
                prohibits_commercial_use=True,
                requires_share_alike=True,
                permits_derivative_works=True,
            ).logos(),
        )

    def test_get_legal_code_for_language_code(self):
        tool = ToolFactory()

        lc_pt = LegalCodeFactory(tool=tool, language_code="pt")
        lc_en = LegalCodeFactory(tool=tool, language_code="en")

        with override(language="pt"):
            result = tool.get_legal_code_for_language_code(None)
            self.assertEqual(lc_pt.id, result.id)
        result = tool.get_legal_code_for_language_code("pt")
        self.assertEqual(lc_pt.id, result.id)
        result = tool.get_legal_code_for_language_code("en")
        self.assertEqual(lc_en.id, result.id)
        with self.assertRaises(LegalCode.DoesNotExist):
            tool.get_legal_code_for_language_code("en_us")

    def test_resource_name(self):
        tool = ToolFactory(
            unit="qwerty", version="2.7", jurisdiction_code="zys"
        )
        self.assertEqual("QWERTY 2.7 ZYS", tool.resource_name)
        tool = ToolFactory(unit="qwerty", version="2.7", jurisdiction_code="")
        self.assertEqual("QWERTY 2.7", tool.resource_name)

    def test_resource_slug(self):
        tool = ToolFactory(
            unit="qwerty", version="2.7", jurisdiction_code="zys"
        )
        self.assertEqual("qwerty_27_zys", tool.resource_slug)
        tool = ToolFactory(unit="qwerty", version="2.7", jurisdiction_code="")
        self.assertEqual("qwerty_27", tool.resource_slug)

    def test_str(self):
        tool = ToolFactory(
            unit="bx-oh", version="1.3", jurisdiction_code="any"
        )
        self.assertEqual(
            str(tool),
            f"Tool<{tool.unit},{tool.version}," f"{tool.jurisdiction_code}>",
        )

    def test_rdf(self):
        tool = ToolFactory(
            unit="bx-oh", version="1.3", jurisdiction_code="any"
        )
        self.assertEqual("RDF Generation Not Implemented", tool.rdf())

    # def test_default_language_code(self):
    #     tool = ToolFactory(
    #         unit="bx-oh", version="1.3", jurisdiction_code=""
    #     )
    #     self.assertEqual(
    #         settings.LANGUAGE_CODE, tool.default_language_code()
    #     )
    #     tool = ToolFactory(
    #         unit="bx-oh", version="1.3", jurisdiction_code="fr"
    #     )
    #     self.assertEqual("fr", tool.default_language_code())
    #
    # def test_get_deed_url(self):
    #     # https://creativecommons.org/licenses/by-sa/4.0/
    #     # https://creativecommons.org/licenses/by-sa/4.0/deed.es
    #     # https://creativecommons.org/licenses/by/3.0/es/
    #     # https://creativecommons.org/licenses/by/3.0/es/deed.fr
    #     tool = ToolFactory(
    #         unit="bx-oh", version="1.3", jurisdiction_code="ae"
    #     )
    #     self.assertEqual("/licenses/bx-oh/1.3/ae/", tool.deed_url)
    #     tool = ToolFactory(
    #         unit="bx-oh", version="1.3", jurisdiction_code=""
    #     )
    #     self.assertEqual("/licenses/bx-oh/1.3/", tool.deed_url)
    #
    # def test_get_deed_url_for_language(self):
    #     tool = ToolFactory(
    #         unit="bx-oh", version="1.3", jurisdiction_code="ae"
    #     )
    #     self.assertEqual(
    #         "/licenses/bx-oh/1.3/ae/deed.fr",
    #         tool.get_deed_url_for_language("fr"),
    #     )
    #     tool = ToolFactory(
    #         unit="bx-oh", version="1.3", jurisdiction_code=""
    #     )
    #     self.assertEqual(
    #         "/licenses/bx-oh/1.3/deed.es",
    #         tool.get_deed_url_for_language("es"),
    #     )

    def test_sampling_plus(self):
        self.assertTrue(ToolFactory(unit="nc-sampling+").sampling_plus)
        self.assertTrue(ToolFactory(unit="sampling+").sampling_plus)
        self.assertFalse(ToolFactory(unit="sampling").sampling_plus)
        self.assertFalse(ToolFactory(unit="MIT").sampling_plus)
        self.assertFalse(ToolFactory(unit="by-nc-nd-sa").sampling_plus)

    def test_level_of_freedom(self):
        data = [
            ("by", FREEDOM_LEVEL_MAX),
            ("devnations", FREEDOM_LEVEL_MIN),
            ("sampling", FREEDOM_LEVEL_MIN),
            ("sampling+", FREEDOM_LEVEL_MID),
            ("by-nc", FREEDOM_LEVEL_MID),
            ("by-nd", FREEDOM_LEVEL_MID),
            ("by-sa", FREEDOM_LEVEL_MAX),
        ]
        for unit, expected_freedom in data:
            with self.subTest(unit):
                tool = ToolFactory(unit=unit)
                self.assertEqual(expected_freedom, tool.level_of_freedom)

    def test_superseded(self):
        lic1 = ToolFactory()
        lic2 = ToolFactory(is_replaced_by=lic1)
        self.assertTrue(lic2.superseded)
        self.assertFalse(lic1.superseded)


class TranslationBranchModelTest(TestCase):
    def test_str(self):
        tc = TranslationBranchFactory(complete=False)
        expected = f"Translation branch {tc.branch_name}. In progress."
        self.assertEqual(expected, str(tc))

    def test_stats(self):
        language_code = "es"
        lc1 = LegalCodeFactory(language_code=language_code)
        tb = TranslationBranchFactory(
            language_code=language_code, legal_codes=[lc1]
        )

        class MockPofile(list):
            def untranslated_entries(self):
                return [1, 2, 3, 4, 5]

            def translated_entries(self):
                return [1, 2, 3]

        mock_pofile = MockPofile()
        with mock.patch.object(LegalCode, "get_pofile") as mock_get_pofile:
            mock_get_pofile.return_value = mock_pofile
            stats = tb.stats
        self.assertEqual(
            {
                "percent_messages_translated": 37,
                "number_of_total_messages": 8,
                "number_of_translated_messages": 3,
                "number_of_untranslated_messages": 5,
            },
            stats,
        )
