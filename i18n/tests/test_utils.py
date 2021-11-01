# Standard library
import datetime
import os
from unittest import mock
from unittest.mock import MagicMock

# Third-party
import polib
from dateutil.tz import tzutc
from django.test import TestCase, override_settings

# First-party/Local
from i18n.utils import (
    active_translation,
    get_default_language_for_jurisdiction,
    get_pofile_creation_date,
    get_pofile_path,
    get_pofile_revision_date,
    get_translation_object,
    map_django_to_redirects_language_codes,
    map_django_to_redirects_language_codes_lowercase,
    map_django_to_transifex_language_code,
    map_legacy_to_django_language_code,
    parse_date,
    save_content_as_pofile_and_mofile,
)

TEST_POFILE = os.path.join(
    os.path.dirname(__file__),
    "locales",
    "es_test_4.0",
    "LC_MESSAGES",
    "test-4.0.po",
)


class UtilTest(TestCase):
    def test_parse_date_good(self):
        parse_result = parse_date("2020-06-29 12:54:48+00:0")
        self.assertEqual(
            parse_result,
            datetime.datetime(2020, 6, 29, 12, 54, 48, tzinfo=tzutc()),
        )

        parse_result = parse_date("2020-06-29T12:54:48Z")
        self.assertEqual(
            parse_result,
            datetime.datetime(2020, 6, 29, 12, 54, 48, tzinfo=tzutc()),
        )

    def test_parse_date_none(self):
        parse_result = parse_date(None)
        self.assertEqual(
            parse_result,
            None,
        )

        parse_result = parse_date("")
        self.assertEqual(
            parse_result,
            None,
        )


class I18NTest(TestCase):
    def test_get_language_for_jurisdiction(self):
        # 'be' default is "fr"
        self.assertEqual(
            "fr", get_default_language_for_jurisdiction("be", "ar")
        )
        # There is none for "xx" so we return the default instead
        self.assertEqual(
            "ar", get_default_language_for_jurisdiction("xx", "ar")
        )


class TranslationTest(TestCase):
    def test_get_translation_object(self):
        translation_object = MagicMock()

        with mock.patch(
            "i18n.utils.translation.trans_real.DjangoTranslation"
        ) as mock_djt:
            mock_djt.return_value = translation_object
            with mock.patch(
                "i18n.utils.translation.trans_real.translation"
            ) as mock_trans:
                result = get_translation_object(
                    django_language_code="LANGUAGE_CODE",
                    domain="GETTEXT_DOMAIN",
                )
        mock_djt.assert_called_with(
            domain="GETTEXT_DOMAIN",
            language="LANGUAGE_CODE",
        )
        mock_trans.assert_called_with("LANGUAGE_CODE")
        self.assertEqual(translation_object, result)

    def test_active_translation(self):
        # Third-party
        from django.utils.translation.trans_real import _active

        translation_object = getattr(_active, "value", None)
        with active_translation(translation_object):
            self.assertEqual(
                getattr(_active, "value", None),
                translation_object,
            )
        del _active.value
        self.assertEqual(getattr(_active, "value", None), None)
        with active_translation(translation_object):
            self.assertEqual(
                getattr(_active, "value", None),
                translation_object,
            )


@override_settings(DATA_REPOSITORY_DIR="/foo/bar")
class PofileTest(TestCase):
    def test_get_pofile_path(self):
        locale_path = get_pofile_path(
            locale_or_legalcode="locale",
            language_code="ar",
            translation_domain="slug1",
        )
        self.assertEqual(
            "/foo/bar/locale/ar/LC_MESSAGES/slug1.po", locale_path
        )

        locale_path = get_pofile_path(
            locale_or_legalcode="legalcode",
            language_code="en",
            translation_domain="slug2",
            data_dir="/foo/bar",
        )
        self.assertEqual(
            "/foo/bar/legalcode/en/LC_MESSAGES/slug2.po", locale_path
        )

    def test_get_pofile_creation_date(self):
        content = (
            'msgid ""\n'
            'msgstr ""\n'
            '"POT-Creation-Date: 2020-06-29 12:54:48+00:00\\n"\n'
        )
        pofile_obj = polib.pofile(content, encoding="utf-8")
        creation_date = get_pofile_creation_date(pofile_obj)
        self.assertEqual("2020-06-29 12:54:48+00:00", str(creation_date))

        content = (
            'msgid ""\n'
            'msgstr ""\n'
            '"POT-Creation-Date: YEAR-MO-DA HO:MI+ZONE\\n"\n'
        )
        pofile_obj = polib.pofile(content, encoding="utf-8")
        creation_date = get_pofile_creation_date(pofile_obj)
        self.assertEqual(None, creation_date)

        content = 'msgid ""\n' 'msgstr ""\n'
        pofile_obj = polib.pofile(content, encoding="utf-8")
        creation_date = get_pofile_creation_date(pofile_obj)
        self.assertEqual(None, creation_date)

    def test_get_pofile_revision_date(self):
        content = (
            b'msgid ""\n'
            b'msgstr ""\n'
            b'"PO-Revision-Date: 2020-06-29 12:54:48+00:00\\n"\n'
        )
        pofile_obj = polib.pofile(content.decode(), encoding="utf-8")
        revision_date = get_pofile_revision_date(pofile_obj)
        self.assertEqual("2020-06-29 12:54:48+00:00", str(revision_date))

        content = (
            b'msgid ""\n'
            b'msgstr ""\n'
            b'"PO-Revision-Date: YEAR-MO-DA HO:MI+ZONE\\n"\n'
        )
        pofile_obj = polib.pofile(content.decode(), encoding="utf-8")
        revision_date = get_pofile_revision_date(pofile_obj)
        self.assertEqual(None, revision_date)

        content = b'msgid ""\n' b'msgstr ""\n'
        pofile_obj = polib.pofile(content.decode(), encoding="utf-8")
        revision_date = get_pofile_revision_date(pofile_obj)
        self.assertEqual(None, revision_date)

    def test_save_content_as_pofile_and_mofile(self):
        path = "/foo/bar.po"
        content = b"xxxxxyyyyy"
        with mock.patch("i18n.utils.polib") as mock_polib:
            return_value = save_content_as_pofile_and_mofile(path, content)
        self.assertEqual(("/foo/bar.po", "/foo/bar.mo"), return_value)
        mock_polib.pofile.assert_called_with(
            pofile=content.decode(), encoding="utf-8"
        )
        pofile = mock_polib.pofile.return_value
        pofile.save.assert_called_with(path)
        pofile.save_as_mofile.assert_called_with("/foo/bar.mo")


class MappingTest(TestCase):
    def test_map_django_to_redirects_language_codes(self):
        self.assertEqual(
            ["DE-AT", "DE_AT", "de-AT", "de-At", "de_AT", "de_At", "de_at"],
            map_django_to_redirects_language_codes("de-at"),
        )

        self.assertEqual(
            [
                "EN",
                "EN-US",
                "EN_US",
                "en-US",
                "en-Us",
                "en-us",
                "en_US",
                "en_Us",
                "en_us",
            ],
            map_django_to_redirects_language_codes("en"),
        )

        self.assertEqual(
            ["NL"],
            map_django_to_redirects_language_codes("nl"),
        )

        self.assertEqual(
            ["OC-ARANES", "OCI", "oc-ARANES", "oc-Aranes", "oci"],
            map_django_to_redirects_language_codes("oc-aranes"),
        )

        self.assertEqual(
            [
                "SR-LATIN",
                "SR-LATN",
                "SR@LATIN",
                "sr-LATIN",
                "sr-LATN",
                "sr-Latin",
                "sr-Latn",
                "sr-latin",
                "sr@LATIN",
                "sr@Latin",
                "sr@latin",
            ],
            map_django_to_redirects_language_codes("sr-latn"),
        )

        self.assertEqual(
            [
                "ZH",
                "ZH-CN",
                "ZH-HANS",
                "ZH_CN",
                "zh",
                "zh-CN",
                "zh-Cn",
                "zh-HANS",
                "zh-Hans",
                "zh-cn",
                "zh_CN",
                "zh_Cn",
                "zh_cn",
            ],
            map_django_to_redirects_language_codes("zh-hans"),
        )

    def test_map_django_to_redirects_language_codes_lowercase(self):
        self.assertEqual(
            ["de_at"],
            map_django_to_redirects_language_codes_lowercase("de-at"),
        )

        self.assertEqual(
            ["en-us", "en_us"],
            map_django_to_redirects_language_codes_lowercase("en"),
        )

        self.assertEqual(
            [],
            map_django_to_redirects_language_codes_lowercase("nl"),
        )

        self.assertEqual(
            ["oci"],
            map_django_to_redirects_language_codes_lowercase("oc-aranes"),
        )

        self.assertEqual(
            ["sr-latin", "sr@latin"],
            map_django_to_redirects_language_codes_lowercase("sr-latn"),
        )

        self.assertEqual(
            ["zh", "zh-cn", "zh_cn"],
            map_django_to_redirects_language_codes_lowercase("zh-hans"),
        )

    def test_map_django_to_transifex_language_code(self):
        transifex_code = map_django_to_transifex_language_code("de-at")
        self.assertEqual("de_AT", transifex_code)

        transifex_code = map_django_to_transifex_language_code("oc-aranes")
        self.assertEqual("oc-aranes", transifex_code)

        transifex_code = map_django_to_transifex_language_code("sr-latn")
        self.assertEqual("sr@latin", transifex_code)

        transifex_code = map_django_to_transifex_language_code("zh-hans")
        self.assertEqual("zh-Hans", transifex_code)

    def test_map_legacy_to_django_language_code(self):
        transifex_code = map_legacy_to_django_language_code("de_AT")
        self.assertEqual("de-at", transifex_code)

        transifex_code = map_legacy_to_django_language_code("oc")
        self.assertEqual("oc-aranes", transifex_code)

        transifex_code = map_legacy_to_django_language_code("sr@latin")
        self.assertEqual("sr-latn", transifex_code)

        transifex_code = map_legacy_to_django_language_code("zh_Hans")
        self.assertEqual("zh-hans", transifex_code)


# Disabled tests (Do not belong under class MappingTest)

# def test_ugettext_for_locale(self):
#     ugettext_en = ugettext_for_locale("en")
#     ugettext_fr = ugettext_for_locale("fr")
#
#     # Need something translated already in Django
#     msg_en = "That page contains no results"
#     msg_fr = "Cette page ne contient aucun résultat"
#     self.assertEqual(msg_en, ugettext_en(msg_en))
#     self.assertEqual(msg_fr, ugettext_fr(msg_en))
#
# def test_get_well_translated_langs(self):
#     dirname = os.path.dirname(__file__)
#     filepath = os.path.join(dirname, "testdata.csv")
#     result = get_well_translated_langs(
#         threshold=80, trans_file=filepath, append_english=False
#     )
#     self.assertEqual([], result)
#     result = get_well_translated_langs(
#         threshold=80, trans_file=filepath, append_english=True
#     )
#     self.assertEqual([{"code": "en", "name": "English"}], result)
#     result = get_well_translated_langs(
#         threshold=1, trans_file=filepath, append_english=True
#     )
#     # Alphabetized
#     self.assertEqual(
#         [
#             {"code": "en", "name": "English"},
#             {"code": "fr", "name": "français"},
#         ],
#         result,
#     )
#
# def test_get_all_trans_stats(self):
#     from i18n.utils import CACHED_TRANS_STATS
#
#     CACHED_TRANS_STATS.clear()
#
#     with self.subTest("Uses cached result"):
#         CACHED_TRANS_STATS["unused filename"] = "ding dong"
#         self.assertEqual(
#             "ding dong", get_all_trans_stats("unused filename")
#         )
#         CACHED_TRANS_STATS.clear()
#
#     with self.subTest("Nonexistent file raises exception"):
#         with self.assertRaises(IOError):
#             get_all_trans_stats("no such filename here")
#
#     with self.subTest("reads CSV file"):
#         dirname = os.path.dirname(__file__)
#         filepath = os.path.join(dirname, "testdata.csv")
#         result = get_all_trans_stats(filepath)
#         self.assertEqual(
#             {
#                 "fr": {
#                     "num_messages": 222,
#                     "num_trans": 13,
#                     "num_fuzzy": 7,
#                     "num_untrans": 202,
#                     "percent_trans": 75,
#                 }
#             },
#             result,
#         )

# def test_applicable_langs(self):
#     from i18n.utils import CACHED_APPLICABLE_LANGS
#
#     CACHED_APPLICABLE_LANGS.clear()
#
#     with self.subTest("uses cached result"):
#         cache_key = ("foobar",)
#         CACHED_APPLICABLE_LANGS[cache_key] = ["bizzle"]
#         self.assertEqual(["bizzle"], applicable_langs("foobar"))
#         CACHED_APPLICABLE_LANGS.clear()
#
#     # Should always include "en". Does NOT cache that result.
#     with self.subTest("always includes 'en'"):
#         self.assertEqual(["en"], applicable_langs("no such locale"))
#         self.assertNotIn(("en",), CACHED_APPLICABLE_LANGS)
#
#     with self.subTest("Just the language works"):
#         locale = "fr"
#         self.assertEqual(["fr", "en"], applicable_langs(locale))
#         self.assertIn((locale,), CACHED_APPLICABLE_LANGS)
#         CACHED_APPLICABLE_LANGS.clear()
#
#     with self.subTest("adding the territory works too"):
#         locale = "es_ES"
#         self.assertEqual(["es_ES", "es", "en"], applicable_langs(locale))
#         self.assertIn((locale,), CACHED_APPLICABLE_LANGS)
#         CACHED_APPLICABLE_LANGS.clear()
