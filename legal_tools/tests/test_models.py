# Standard library
from unittest import mock

# Third-party
import polib
from django.conf import settings
from django.test import TestCase, override_settings
from django.utils.translation import override

# First-party/Local
from legal_tools.models import (
    FREEDOM_LEVEL_MAX,
    FREEDOM_LEVEL_MID,
    FREEDOM_LEVEL_MIN,
    LegalCode,
    Tool,
)
from legal_tools.tests.factories import (
    LegalCodeFactory,
    ToolFactory,
    TranslationBranchFactory,
)


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

    # get_publish_files BY-NC-ND 4.0 #########################################
    # BY-NC-ND 4.0 is an international license with multiple languages

    def test_get_publish_files_by_nc_nd4_deed_en(self):
        legal_code = LegalCodeFactory(
            tool__category="licenses",
            tool__unit="by-nc-nd",
            tool__version="4.0",
            language_code="en",
        )

        returned_list = legal_code.get_publish_files("deed")

        self.assertEqual(
            [
                # relpath
                "licenses/by-nc-nd/4.0/deed.en.html",
                # symlinks
                ["deed.html", "index.html"],
                # redirects_data
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
            ],
            returned_list,
        )

    def test_get_publish_files_by_nc_nd4_legal_code_en(self):
        legal_code = LegalCodeFactory(
            tool__category="licenses",
            tool__unit="by-nc-nd",
            tool__version="4.0",
            language_code="en",
        )

        returned_list = legal_code.get_publish_files("legalcode")

        self.assertEqual(
            [
                # relpath
                "licenses/by-nc-nd/4.0/legalcode.en.html",
                # symlinks
                ["legalcode.html"],
                # redirects_data
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
            ],
            returned_list,
        )

    def test_get_publish_files_by_nc_nd_4_deed_zh_hant(self):
        legal_code = LegalCodeFactory(
            tool__category="licenses",
            tool__unit="by-nc-nd",
            tool__version="4.0",
            language_code="zh-hant",
        )

        returned_list = legal_code.get_publish_files("deed")

        self.assertEqual(
            [
                # relpath
                "licenses/by-nc-nd/4.0/deed.zh-hant.html",
                # symlinks
                [],
                # redirects_data
                [
                    {
                        "destination": "deed.zh-hant",
                        "language_code": "zh-hant",
                        "redirect_file": (
                            "licenses/by-nc-nd/4.0/deed.zh-tw.html"
                        ),
                        "title": "",
                    },
                    {
                        "destination": "deed.zh-hant",
                        "language_code": "zh-hant",
                        "redirect_file": (
                            "licenses/by-nc-nd/4.0/deed.zh_tw.html"
                        ),
                        "title": "",
                    },
                ],
            ],
            returned_list,
        )

    def test_get_publish_files_by_nc_nd_4_legal_code_zh_hant(self):
        legal_code = LegalCodeFactory(
            tool__category="licenses",
            tool__unit="by-nc-nd",
            tool__version="4.0",
            language_code="zh-hant",
        )

        returned_list = legal_code.get_publish_files("legalcode")

        self.assertEqual(
            [
                # relpath
                "licenses/by-nc-nd/4.0/legalcode.zh-hant.html",
                # symlinks
                [],
                # redirects_data
                [
                    {
                        "destination": "legalcode.zh-hant",
                        "language_code": "zh-hant",
                        "redirect_file": (
                            "licenses/by-nc-nd/4.0/legalcode.zh-tw.html"
                        ),
                        "title": "",
                    },
                    {
                        "destination": "legalcode.zh-hant",
                        "language_code": "zh-hant",
                        "redirect_file": (
                            "licenses/by-nc-nd/4.0/legalcode.zh_tw.html"
                        ),
                        "title": "",
                    },
                ],
            ],
            returned_list,
        )

    # get_publish_files BY-NC 3.0 CA #########################################
    # BY-NC 3.0 CA is a ported license with multiple languages

    def test_get_publish_files_by_nc3_deed_ca_en(self):
        legal_code = LegalCodeFactory(
            tool__category="licenses",
            tool__jurisdiction_code="ca",
            tool__unit="by-nc",
            tool__version="3.0",
            language_code="en",
        )

        returned_list = legal_code.get_publish_files("deed")

        self.assertEqual(
            [
                # relpath
                "licenses/by-nc/3.0/ca/deed.en.html",
                # symlinks
                ["deed.html", "index.html"],
                # redirects_data
                [
                    {
                        "destination": "deed.en",
                        "language_code": "en",
                        "redirect_file": (
                            "licenses/by-nc/3.0/ca/deed.en-us.html"
                        ),
                        "title": "",
                    },
                    {
                        "destination": "deed.en",
                        "language_code": "en",
                        "redirect_file": (
                            "licenses/by-nc/3.0/ca/deed.en_us.html"
                        ),
                        "title": "",
                    },
                ],
            ],
            returned_list,
        )

    def test_get_publish_files_by_nc3_legal_code_ca_en(self):
        legal_code = LegalCodeFactory(
            tool__category="licenses",
            tool__jurisdiction_code="ca",
            tool__unit="by-nc",
            tool__version="3.0",
            language_code="en",
        )

        returned_list = legal_code.get_publish_files("legalcode")

        self.assertEqual(
            [
                # relpath
                "licenses/by-nc/3.0/ca/legalcode.en.html",
                # symlinks
                ["legalcode.html"],
                # redirects_data
                [
                    {
                        "destination": "legalcode.en",
                        "language_code": "en",
                        "redirect_file": (
                            "licenses/by-nc/3.0/ca/legalcode.en-us.html"
                        ),
                        "title": "",
                    },
                    {
                        "destination": "legalcode.en",
                        "language_code": "en",
                        "redirect_file": (
                            "licenses/by-nc/3.0/ca/legalcode.en_us.html"
                        ),
                        "title": "",
                    },
                ],
            ],
            returned_list,
        )

    # get_publish_files BY-SA 3.0 AM #########################################
    # BY-SA 3.0 AM is a ported license with a single language

    def test_get_publish_files_by_sa3_deed_am_hy(self):
        legal_code = LegalCodeFactory(
            tool__category="licenses",
            tool__jurisdiction_code="am",
            tool__unit="by-sa",
            tool__version="3.0",
            language_code="hy",
        )

        returned_list = legal_code.get_publish_files("deed")

        self.assertEqual(
            [
                # relpath
                "licenses/by-sa/3.0/am/deed.hy.html",
                # symlinks
                ["deed.html", "index.html"],
                # redirects_data
                [],
            ],
            returned_list,
        )

    def test_get_publish_files_by_sa3_legal_code_am_hy(self):
        legal_code = LegalCodeFactory(
            tool__category="licenses",
            tool__jurisdiction_code="am",
            tool__unit="by-sa",
            tool__version="3.0",
            language_code="hy",
        )

        returned_list = legal_code.get_publish_files("legalcode")

        self.assertEqual(
            [
                # relpath
                "licenses/by-sa/3.0/am/legalcode.hy.html",
                # symlinks
                ["legalcode.html"],
                # redirects_data
                [],
            ],
            returned_list,
        )

    # get_publish_files CC0 1.0 ##############################################
    # CC0 1.0 is an unported declaration with multiple languages

    def test_get_publish_files_zero_deed_en(self):
        legal_code = LegalCodeFactory(
            tool__category="publicdomain",
            tool__unit="zero",
            tool__version="1.0",
            language_code="en",
        )

        returned_list = legal_code.get_publish_files("deed")

        self.assertEqual(
            [
                # relpath
                "publicdomain/zero/1.0/deed.en.html",
                # symlinks
                ["deed.html", "index.html"],
                # redirects_data
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
            ],
            returned_list,
        )

    def test_get_publish_files_zero_legal_code_en(self):
        legal_code = LegalCodeFactory(
            tool__category="publicdomain",
            tool__unit="zero",
            tool__version="1.0",
            language_code="en",
        )

        returned_list = legal_code.get_publish_files("legalcode")

        self.assertEqual(
            [
                # relpath
                "publicdomain/zero/1.0/legalcode.en.html",
                # symlinks
                ["legalcode.html"],
                # redirects_data
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
            ],
            returned_list,
        )

    def test_get_publish_files_zero_deed_nl(self):
        legal_code = LegalCodeFactory(
            tool__category="publicdomain",
            tool__unit="zero",
            tool__version="1.0",
            language_code="nl",
        )

        returned_list = legal_code.get_publish_files("deed")

        self.assertEqual(
            [
                # relpath
                "publicdomain/zero/1.0/deed.nl.html",
                # symlinks
                [],
                # redirects_data
                [],
            ],
            returned_list,
        )

    # get_publish_files Mark 1.0 #############################################
    # Mark 1.0 is an unported deed-only declaration

    def test_get_publish_files_mark_deed(self):
        legal_code = LegalCodeFactory(
            tool__category="publicdomain",
            tool__deed_only=True,
            tool__unit="mark",
            tool__version="1.0",
            language_code="en",
        )

        returned_list = legal_code.get_publish_files("deed")

        self.assertEqual(
            [
                # relpath
                "publicdomain/mark/1.0/deed.en.html",
                # symlinks
                ["deed.html", "index.html"],
                # redirects_data
                [
                    {
                        "destination": "deed.en",
                        "language_code": "en",
                        "redirect_file": (
                            "publicdomain/mark/1.0/deed.en-us.html"
                        ),
                        "title": "",
                    },
                    {
                        "destination": "deed.en",
                        "language_code": "en",
                        "redirect_file": (
                            "publicdomain/mark/1.0/deed.en_us.html"
                        ),
                        "title": "",
                    },
                ],
            ],
            returned_list,
        )

    def test_get_publish_files_mark_legal_code(self):
        legal_code = LegalCodeFactory(
            tool__category="publicdomain",
            tool__deed_only=True,
            tool__unit="mark",
            tool__version="1.0",
            language_code="en",
        )

        returned_list = legal_code.get_publish_files("legalcode")

        self.assertEqual(
            [
                # relpath
                None,
                # symlinks
                [],
                # redirects_data
                [
                    {
                        "destination": "deed.en",
                        "language_code": "en",
                        "redirect_file": (
                            "publicdomain/mark/1.0/legalcode.en-us.html"
                        ),
                        "title": "",
                    },
                    {
                        "destination": "deed.en",
                        "language_code": "en",
                        "redirect_file": (
                            "publicdomain/mark/1.0/legalcode.en_us.html"
                        ),
                        "title": "",
                    },
                    {
                        "destination": "deed.en",
                        "language_code": "en",
                        "redirect_file": (
                            "publicdomain/mark/1.0/legalcode.en.html"
                        ),
                        "title": "",
                    },
                    {
                        "destination": "deed.en",
                        "language_code": "en",
                        "redirect_file": (
                            "publicdomain/mark/1.0/legalcode.html"
                        ),
                        "title": "",
                    },
                ],
            ],
            returned_list,
        )

    # get_redirect_pairs #####################################################

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
            "jurisdiction_name": "UNDEFINED",
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
