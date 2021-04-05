# Standard library
import os

# Third-party
from django.test import TestCase

# First-party/Local
from i18n.utils import (
    get_default_language_for_jurisdiction,
    get_locale_text_orientation,
    locale_to_lower_upper,
    rtl_context_stuff,
    ugettext_for_locale,
)

this_file = __file__
this_dir = os.path.abspath(os.path.dirname(this_file))
test_locale_dir = os.path.join(this_dir, "locales")


class I18NTest(TestCase):
    def test_text_orientation(self):
        with self.subTest("en"):
            self.assertEqual("ltr", get_locale_text_orientation("en"))
        with self.subTest("ar"):
            self.assertEqual("rtl", get_locale_text_orientation("ar"))
        with self.subTest("he"):
            self.assertEqual("rtl", get_locale_text_orientation("he"))
        with self.subTest("zh"):
            self.assertEqual("ltr", get_locale_text_orientation("zh"))
        with self.subTest("bad locale"):
            with self.assertRaises(ValueError):
                get_locale_text_orientation("klingon")

    def test_rtl_context_stuff(self):
        with self.subTest("ar"):
            self.assertEqual(
                {
                    "get_ltr_rtl": "rtl",
                    "is_rtl": True,
                    "is_rtl_align": "text-align: right",
                },
                rtl_context_stuff("ar"),
            )
        with self.subTest("en"):
            self.assertEqual(
                {
                    "get_ltr_rtl": "ltr",
                    "is_rtl": False,
                    "is_rtl_align": "text-align: left",
                },
                rtl_context_stuff("en"),
            )

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

    def test_ugettext_for_locale(self):
        ugettext_en = ugettext_for_locale("en")
        ugettext_fr = ugettext_for_locale("fr")

        # Need something translated already in Django
        msg_en = "That page contains no results"
        msg_fr = "Cette page ne contient aucun résultat"
        self.assertEqual(msg_en, ugettext_en(msg_en))
        self.assertEqual(msg_fr, ugettext_fr(msg_en))

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

    def test_locale_to_lower_upper(self):
        # (in, out)
        testdata = [
            ("en", "en"),
            ("en-us", "en_US"),
            ("EN_us", "en_US"),
        ]
        for input, output in testdata:
            self.assertEqual(output, locale_to_lower_upper(input))

    #
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

    def test_get_language_for_jurisdiction(self):
        # 'be' default is "fr"
        self.assertEqual(
            "fr", get_default_language_for_jurisdiction("be", "ar")
        )
        # There is none for "xx" so we return the default instead
        self.assertEqual(
            "ar", get_default_language_for_jurisdiction("xx", "ar")
        )
