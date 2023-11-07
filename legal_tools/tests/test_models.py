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

        zerov1dedication = ToolFactory(
            unit="zero", version="1.0", jurisdiction_code=""
        )

        should_be_translated = [
            LegalCodeFactory(tool=bylicense40),
            LegalCodeFactory(tool=zerov1dedication),
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

        zerov1dedication = ToolFactory(
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
            LegalCodeFactory(tool=zerov1dedication),
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
            domain="by-sa_40", language_code="de", language_default="en"
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

    def test_get_publish_files_by_nc_nd4_legal_code_en(self):
        legal_code = LegalCodeFactory(
            tool__category="licenses",
            tool__unit="by-nc-nd",
            tool__version="4.0",
            language_code="en",
        )

        returned_list = legal_code.get_publish_files()

        self.assertEqual(
            [
                # relpath
                "licenses/by-nc-nd/4.0/legalcode.en.html",
                # symlinks
                ["legalcode.html"],
                # redirects_data
                [],
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

        returned_list = legal_code.get_publish_files()

        self.assertEqual(
            [
                # relpath
                "licenses/by-nc-nd/4.0/legalcode.zh-hant.html",
                # symlinks
                [],
                # redirects_data
                [],
            ],
            returned_list,
        )

    # get_publish_files BY-NC 3.0 CA #########################################
    # BY-NC 3.0 CA is a ported license with multiple languages

    def test_get_publish_files_by_nc3_legal_code_ca_en(self):
        legal_code = LegalCodeFactory(
            tool__category="licenses",
            tool__jurisdiction_code="ca",
            tool__unit="by-nc",
            tool__version="3.0",
            language_code="en",
        )

        returned_list = legal_code.get_publish_files()

        self.assertEqual(
            [
                # relpath
                "licenses/by-nc/3.0/ca/legalcode.en.html",
                # symlinks
                ["legalcode.html"],
                # redirects_data
                [],
            ],
            returned_list,
        )

    # get_publish_files BY-SA 3.0 AM #########################################
    # BY-SA 3.0 AM is a ported license with a single language

    def test_get_publish_files_by_sa3_legal_code_am_hy(self):
        legal_code = LegalCodeFactory(
            tool__category="licenses",
            tool__jurisdiction_code="am",
            tool__unit="by-sa",
            tool__version="3.0",
            language_code="hy",
        )

        returned_list = legal_code.get_publish_files()

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

    # LegalCode.get_publish_files CC0 1.0 ####################################
    # CC0 1.0 is an unported dedication with multiple languages

    def test_get_publish_files_zero_legal_code_en(self):
        legal_code = LegalCodeFactory(
            tool__category="publicdomain",
            tool__unit="zero",
            tool__version="1.0",
            language_code="en",
        )

        returned_list = legal_code.get_publish_files()

        self.assertEqual(
            [
                # relpath
                "publicdomain/zero/1.0/legalcode.en.html",
                # symlinks
                ["legalcode.html"],
                # redirects_data
                [],
            ],
            returned_list,
        )

    def test_get_publish_files_zero_legal_code_nl(self):
        legal_code = LegalCodeFactory(
            tool__category="publicdomain",
            tool__unit="zero",
            tool__version="1.0",
            language_code="nl",
        )

        returned_list = legal_code.get_publish_files()

        self.assertEqual(
            [
                # relpath
                "publicdomain/zero/1.0/legalcode.nl.html",
                # symlinks
                [],
                # redirects_data
                [],
            ],
            returned_list,
        )

    # get_publish_files Mark 1.0 #############################################
    # Mark 1.0 is an unported deed-only declaration

    def test_get_publish_files_mark_legal_code_en(self):
        legal_code = LegalCodeFactory(
            tool__category="publicdomain",
            tool__deed_only=True,
            tool__unit="mark",
            tool__version="1.0",
            language_code="en",
        )

        returned_list = legal_code.get_publish_files()

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

    def test_get_redirect_pairs(self):
        legal_code = LegalCodeFactory(
            tool__category="license",
            tool__unit="by",
            tool__version="4.0",
            language_code="en",
        )
        redirect_pairs = legal_code.get_redirect_pairs()
        self.assertEqual(
            [
                [
                    "/license/by/4[.]0/legalcode[.]en[@_-]gb(?:[.]html)?",
                    "/license/by/4.0/legalcode.en",
                ],
                [
                    "/license/by/4[.]0/legalcode[.]en[@_-]us(?:[.]html)?",
                    "/license/by/4.0/legalcode.en",
                ],
            ],
            redirect_pairs,
        )

    def test_identifier(self):
        self.assertEqual(
            "CC BY 4.0",
            LegalCodeFactory(
                tool__unit="by", tool__version="4.0"
            ).identifier(),
        )
        self.assertEqual(
            "CC BY-SA 3.0 NL",
            LegalCodeFactory(
                tool__jurisdiction_code="nl",
                tool__unit="by-sa",
                tool__version="3.0",
            ).identifier(),
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

    def test__lt__sort(self):
        TF = ToolFactory
        tools = [
            TF(category="a", unit="a", version="1", jurisdiction_code="a"),
            TF(category="a", unit="c", version="1", jurisdiction_code="b"),
            TF(category="b", unit="a", version="1", jurisdiction_code="a"),
            TF(category="b", unit="b", version="1", jurisdiction_code="b"),
            TF(category="c", unit="a", version="1", jurisdiction_code="a"),
            TF(category="c", unit="a", version="1", jurisdiction_code="b"),
        ]
        self.assertNotEqual(tools, sorted(tools, reverse=True))
        self.assertEqual(tools, sorted(sorted(tools, reverse=True)))

    def test_get_metadata(self):
        # Ported
        tool = ToolFactory(
            **{
                "base_url": (
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
                "prohibits_commercial_use": True,
                "prohibits_high_income_nation_use": False,
            }
        )

        LegalCodeFactory(tool=tool, language_code="pt")
        LegalCodeFactory(tool=tool, language_code="en")

        data = tool.get_metadata()
        expected_data = {
            "jurisdiction_name": "Generic",
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
                "base_url": (
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
            "legal_code_languages": {
                "en": "English",
            },
        }

        for key in expected_data.keys():
            self.assertEqual(expected_data[key], data[key])

        # Deprecated
        tool = ToolFactory(
            **{
                "base_url": (
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
            "legal_code_languages": {
                "en": "English",
            },
        }

        for key in expected_data.keys():
            self.assertEqual(expected_data[key], data[key])

        # Deed-only
        tool = ToolFactory(
            **{
                "base_url": (
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
        }

        for key in expected_data.keys():
            self.assertEqual(expected_data[key], data[key])

    # get_publish_files BY-NC-ND 4.0 #########################################
    # BY-NC-ND 4.0 is an international license with multiple languages

    def test_get_publish_files_by_nc_nd4_deed_en(self):
        language_code = "en"
        tool = ToolFactory(
            category="licenses",
            unit="by-nc-nd",
            version="4.0",
        )

        returned_list = tool.get_publish_files(language_code)

        self.assertEqual(
            [
                # relpath
                "licenses/by-nc-nd/4.0/deed.en.html",
                # symlinks
                ["deed.html", "index.html"],
            ],
            returned_list,
        )

    # get_publish_files BY-NC 3.0 CA #########################################
    # BY-NC 3.0 CA is a ported license with multiple languages

    def test_get_publish_files_by_nc3_deed_ca_en(self):
        language_code = "en"
        tool = ToolFactory(
            category="licenses",
            jurisdiction_code="ca",
            unit="by-nc",
            version="3.0",
        )

        returned_list = tool.get_publish_files(language_code)

        self.assertEqual(
            [
                # relpath
                "licenses/by-nc/3.0/ca/deed.en.html",
                # symlinks
                ["deed.html", "index.html"],
            ],
            returned_list,
        )

    # get_publish_files BY-NC-ND 4.0 #########################################
    # BY-NC-ND 4.0 is an international license with multiple languages

    def test_get_publish_files_by_nc_nd_4_deed_zh_hant(self):
        # English content is returned as translation.activate() is not used
        language_code = "zh-hant"
        tool = ToolFactory(
            category="licenses",
            unit="by-nc-nd",
            version="4.0",
        )

        returned_list = tool.get_publish_files(language_code)

        self.assertEqual(
            [
                # relpath
                "licenses/by-nc-nd/4.0/deed.zh-hant.html",
                # symlinks
                [],
            ],
            returned_list,
        )

    # get_publish_files BY-SA 3.0 AM #########################################
    # BY-SA 3.0 AM is a ported license with a single language

    def test_get_publish_files_by_sa3_deed_am_hy(self):
        # English content is returned as translation.activate() is not used
        language_code = "hy"
        tool = ToolFactory(
            category="licenses",
            jurisdiction_code="am",
            unit="by-sa",
            version="3.0",
        )

        returned_list = tool.get_publish_files(language_code)

        self.assertEqual(
            [
                # relpath
                "licenses/by-sa/3.0/am/deed.hy.html",
                # symlinks
                ["deed.html", "index.html"],
            ],
            returned_list,
        )

    # get_publish_files CC0 1.0 ##############################################
    # CC0 1.0 is an unported dedication with multiple languages

    def test_get_publish_files_zero_deed_en(self):
        language_code = "en"
        tool = ToolFactory(
            category="publicdomain",
            unit="zero",
            version="1.0",
        )

        returned_list = tool.get_publish_files(language_code)

        self.assertEqual(
            [
                # relpath
                "publicdomain/zero/1.0/deed.en.html",
                # symlinks
                ["deed.html", "index.html"],
            ],
            returned_list,
        )

    # get_publish_files Mark 1.0 #############################################
    # Mark 1.0 is an unported deed-only declaration

    def test_get_publish_files_mark_deed_en(self):
        language_code = "en"
        tool = ToolFactory(
            category="publicdomain",
            deed_only=True,
            unit="mark",
            version="1.0",
        )

        returned_list = tool.get_publish_files(language_code)

        self.assertEqual(
            [
                # relpath
                "publicdomain/mark/1.0/deed.en.html",
                # symlinks
                ["deed.html", "index.html"],
            ],
            returned_list,
        )

    def test_get_publish_files_zero_deed_nl(self):
        # English content is returned as translation.activate() is not used
        language_code = "nl"
        tool = ToolFactory(
            category="publicdomain",
            unit="zero",
            version="1.0",
        )

        returned_list = tool.get_publish_files(language_code)

        self.assertEqual(
            [
                # relpath
                "publicdomain/zero/1.0/deed.nl.html",
                # symlinks
                [],
            ],
            returned_list,
        )

    # get_redirect_pairs #####################################################

    def test_get_redirect_pairs(self):
        language_code = "zh-hant"
        tool = ToolFactory(category="license", unit="by", version="4.0")
        redirect_pairs = tool.get_redirect_pairs(language_code)
        self.assertEqual(
            [
                [
                    "/license/by/4[.]0/deed[.]zh[@_-]tw(?:[.]html)?",
                    "/license/by/4.0/deed.zh-hant",
                ],
            ],
            redirect_pairs,
        )

    # logos ##################################################################

    def test_logos(self):
        # Every tool includes "cc-logo"
        self.assertIn("cc-logo", ToolFactory().logos())
        self.assertEqual(
            ["cc-logo"],
            ToolFactory(unit="devnations", version="2.0").logos(),
        )
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
        self.assertEqual(
            ["cc-logo", "cc-nc"],
            ToolFactory(
                unit="nc",
                version="1.0",
                prohibits_commercial_use=True,
            ).logos(),
        )
        self.assertEqual(
            ["cc-logo", "cc-nc", "cc-sampling-plus"],
            ToolFactory(unit="nc-sampling+", version="1.0").logos(),
        )
        self.assertEqual(
            ["cc-logo", "cc-nd"],
            ToolFactory(
                unit="nd",
                version="1.0",
                permits_derivative_works=False,
            ).logos(),
        )
        self.assertEqual(
            ["cc-logo", "cc-sampling"],
            ToolFactory(unit="sampling", version="1.0").logos(),
        )
        self.assertEqual(
            ["cc-logo", "cc-sampling-plus"],
            ToolFactory(unit="sampling+", version="1.0").logos(),
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
