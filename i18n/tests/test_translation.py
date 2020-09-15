import os
from unittest import mock
from unittest.mock import call

from django.test import TestCase, override_settings

from i18n.translation import Translation, get_translation_object

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

    def test_compare_to(self):
        t = Translation(TEST_POFILE, "es")
        out = t.compare_to(t)
        expected = {
            "different_translations": {},
            "keys_common": {"message in English"},
            "keys_extra": set(),
            "keys_missing": set(),
        }
        self.assertEqual(expected, out)
