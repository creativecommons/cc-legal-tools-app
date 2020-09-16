import os
from unittest import mock
from unittest.mock import call

from django.test import TestCase, override_settings

from i18n.translation import Translation, get_translation_object
from licenses.tests.factories import LegalCodeFactory

TEST_POFILE = os.path.join(
    os.path.dirname(__file__), "locales", "es_test_4.0", "LC_MESSAGES", "test-4.0.po"
)


class TranslationTest(TestCase):
    def test_get_translation_object(self):
        with mock.patch("i18n.translation.Translation") as mock_Translation:
            get_translation_object("path", "code")
        self.assertEqual([call("path", "code")], mock_Translation.call_args_list)

    def test_translation_with_file_not_found(self):
        with self.assertRaises(FileNotFoundError):
            Translation("no_such_file", "code")

    @override_settings(DEBUG=True)
    def test_translating_missing_message_debug_on(self):
        t = Translation(TEST_POFILE, "es")
        result = t.translate("no such message")
        expected = f"[MISSING TRANSLATION FOR msgid='no such message' in pofile='{TEST_POFILE}']"
        self.assertEqual(expected, result)

    @override_settings(DEBUG=False)
    def test_translating_missing_message_debug_off(self):
        t = Translation(TEST_POFILE, "es")
        result = t.translate("no such message")
        expected = "no such message"
        self.assertEqual(expected, result)

    def test_translating(self):
        t = Translation(TEST_POFILE, "es")
        result = t.translate("message in English")
        self.assertEqual("Translation in Spanish", result)

    def test_misc_methods(self):
        t = Translation(TEST_POFILE, "es")
        self.assertEqual(1, t.num_messages())
        self.assertEqual(1, t.num_translated())
        self.assertEqual(100, t.percent_translated())
        t.translations["message in English"] = ""
        self.assertEqual(0, t.percent_translated())
        t.translations.clear()
        self.assertEqual(0, t.percent_translated())

    def test_compare_to(self):
        t1 = Translation(TEST_POFILE, "es")
        t2 = Translation(TEST_POFILE, "es")
        t2.translations["message in English"] = "different translation"
        lc1 = LegalCodeFactory(license__license_code="by-sa")
        lc2 = LegalCodeFactory(license=lc1.license)
        out = t1.compare_to(t2, lc1, lc2)
        expected = {
            "keys_missing": set(),
            "keys_extra": set(),
            "keys_common": {"message in English"},
            "different_translations": {
                "message in English": {
                    "Translation in Spanish": {"by-sa"},
                    "different translation": {"by-sa"},
                }
            },
        }
        self.assertEqual(expected, out)
