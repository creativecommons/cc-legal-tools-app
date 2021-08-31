# Standard library
import os
from unittest import mock
from unittest.mock import MagicMock

# Third-party
import polib
from django.test import TestCase, override_settings

# First-party/Local
from i18n.utils import (
    active_translation,
    get_pofile_creation_date,
    get_pofile_path,
    get_pofile_revision_date,
    get_translation_object,
    map_django_to_redirects_language_code,
    map_django_to_transifex_language_code,
    map_legacy_to_django_language_code,
    save_content_as_pofile_and_mofile,
)

TEST_POFILE = os.path.join(
    os.path.dirname(__file__),
    "locales",
    "es_test_4.0",
    "LC_MESSAGES",
    "test-4.0.po",
)


@override_settings(DATA_REPOSITORY_DIR="/foo/bar")
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
        locale_path = get_pofile_path("locale", "ar", "slug1")
        self.assertEqual(
            "/foo/bar/locale/ar/LC_MESSAGES/slug1.po", locale_path
        )

        locale_path = get_pofile_path("legalcode", "en", "slug2")
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
    def test_map_django_to_redirects_language_code(self):
        self.assertEqual(
            ["DE-AT", "DE_AT", "de-AT", "de_AT", "de_at"],
            map_django_to_redirects_language_code("de-at"),
        )

        self.assertEqual(
            ["EN", "EN-US", "en-US", "en-us"],
            map_django_to_redirects_language_code("en"),
        )

        self.assertEqual(
            [
                "NL",
            ],
            map_django_to_redirects_language_code("nl"),
        )

        self.assertEqual(
            ["OC-ARANES", "OCI", "oc-Aranes", "oci"],
            map_django_to_redirects_language_code("oc-aranes"),
        )

        self.assertEqual(
            [
                "SR-LATIN",
                "SR-LATN",
                "SR@LATIN",
                "sr-Latin",
                "sr-Latn",
                "sr-latin",
                "sr@Latin",
                "sr@latin",
            ],
            map_django_to_redirects_language_code("sr-latn"),
        )

        self.assertEqual(
            [
                "ZH",
                "ZH-CN",
                "ZH-HANS",
                "ZH_CN",
                "zh",
                "zh-CN",
                "zh-Hans",
                "zh-cn",
                "zh_CN",
                "zh_cn",
            ],
            map_django_to_redirects_language_code("zh-hans"),
        )

    def test_map_django_to_transifex_language_code(self):
        transifex_code = map_django_to_transifex_language_code("de-at")
        self.assertEqual("de_AT", transifex_code)

        transifex_code = map_django_to_transifex_language_code("oc-aranes")
        self.assertEqual("oc", transifex_code)

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
