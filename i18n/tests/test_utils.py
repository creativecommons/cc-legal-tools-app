# Standard library
import os
from unittest import mock
from unittest.mock import MagicMock

# Third-party
from django.test import TestCase, override_settings

# First-party/Local
from i18n.utils import (
    get_translation_object,
    save_content_as_pofile_and_mofile,
)

TEST_POFILE = os.path.join(
    os.path.dirname(__file__),
    "locales",
    "es_test_4.0",
    "LC_MESSAGES",
    "test-4.0.po",
)


@override_settings(TRANSLATION_REPOSITORY_DIRECTORY="/foo/bar")
class TranslationTest(TestCase):
    def test_get_translation_object(self):
        translation_object = MagicMock()

        with mock.patch("i18n.utils.DjangoTranslation") as mock_djt:
            mock_djt.return_value = translation_object
            with mock.patch("i18n.utils.translation") as mock_trans:
                result = get_translation_object(
                    django_language_code="code", domain="cnn.com"
                )
        mock_djt.assert_called_with(
            domain="cnn.com",
            language="code",
            localedirs=["/foo/bar/translations"],
        )
        mock_trans.assert_called_with("code")
        self.assertEqual(translation_object, result)


class PofileTest(TestCase):
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
