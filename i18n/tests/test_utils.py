# Standard library
import datetime
import os
from unittest import mock
from unittest.mock import MagicMock

# Third-party
import polib
from dateutil.tz import tzutc
from django.conf import settings
from django.test import TestCase, override_settings

# First-party/Local
from i18n.utils import (
    active_translation,
    get_default_language_for_jurisdiction_deed_ux,
    get_default_language_for_jurisdiction_legal_code,
    get_jurisdiction_name,
    get_pofile_creation_date,
    get_pofile_path,
    get_pofile_revision_date,
    get_translation_object,
    map_django_to_transifex_language_code,
    map_legacy_to_django_language_code,
    parse_date,
    save_content_as_pofile_and_mofile,
    write_transstats_csv,
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

    def test_get_jurisdiction_name_licenses_40(self):
        category = "licenses"
        unit = "by"
        version = "4.0"

        jurisdiction_code = ""
        self.assertEqual(
            "International",
            get_jurisdiction_name(category, unit, version, jurisdiction_code),
        )

    def test_get_jurisdiction_name_licenses_30(self):
        category = "licenses"
        unit = "by"
        version = "3.0"

        jurisdiction_code = ""
        self.assertEqual(
            "Unported",
            get_jurisdiction_name(category, unit, version, jurisdiction_code),
        )

        jurisdiction_code = "am"
        self.assertEqual(
            "Armenia",
            get_jurisdiction_name(category, unit, version, jurisdiction_code),
        )

    def test_get_jurisdiction_name_licenses_25(self):
        category = "licenses"
        unit = "by"
        version = "2.5"

        jurisdiction_code = ""
        self.assertEqual(
            "Generic",
            get_jurisdiction_name(category, unit, version, jurisdiction_code),
        )

        jurisdiction_code = "be"
        self.assertEqual(
            "Belgium",
            get_jurisdiction_name(category, unit, version, jurisdiction_code),
        )

    def test_get_jurisdiction_name_licenses_21(self):
        category = "licenses"
        unit = "by"
        version = "2.1"

        jurisdiction_code = ""
        self.assertEqual(
            "Generic",
            get_jurisdiction_name(category, unit, version, jurisdiction_code),
        )

        jurisdiction_code = "ca"
        self.assertEqual(
            "Canada",
            get_jurisdiction_name(category, unit, version, jurisdiction_code),
        )

    def test_get_jurisdiction_name_licenses_20(self):
        category = "licenses"
        unit = "by"
        version = "2.0"

        jurisdiction_code = ""
        self.assertEqual(
            "Generic",
            get_jurisdiction_name(category, unit, version, jurisdiction_code),
        )

        jurisdiction_code = "de"
        self.assertEqual(
            "Germany",
            get_jurisdiction_name(category, unit, version, jurisdiction_code),
        )

    def test_get_jurisdiction_name_licenses_10(self):
        category = "licenses"
        unit = "by"
        version = "1.0"

        jurisdiction_code = ""
        self.assertEqual(
            "Generic",
            get_jurisdiction_name(category, unit, version, jurisdiction_code),
        )

        jurisdiction_code = "ec"
        self.assertEqual(
            "Ecuador",
            get_jurisdiction_name(category, unit, version, jurisdiction_code),
        )


class I18NTest(TestCase):
    def test_get_language_for_jurisdiction_deed(self):
        # "be" jurisdiction default is "fr"
        self.assertEqual(
            "fr", get_default_language_for_jurisdiction_deed_ux("be")
        )
        # "am" jurisdiction default is "hy"
        # the "hy" translation is incomplete so we return the global default
        # https://github.com/creativecommons/cc-legal-tools-app/issues/444
        self.assertEqual(
            "en", get_default_language_for_jurisdiction_deed_ux("am")
        )
        # "xx" is an invalid jurisdiction
        # return global default ("en")
        self.assertEqual(
            "en", get_default_language_for_jurisdiction_deed_ux("xx")
        )

    def test_get_language_for_jurisdiction_legal_code(self):
        # "be" jurisdiction default is "fr"
        self.assertEqual(
            "fr", get_default_language_for_jurisdiction_legal_code("be")
        )
        # "xx" is an invalid jurisdiction
        # return global default ("en")
        self.assertEqual(
            "en", get_default_language_for_jurisdiction_legal_code("xx")
        )


class TranslationTest(TestCase):
    @override_settings(
        LANGUAGES_AVAILABLE_DEEDS_UX=["LANGUAGE_CODE"],
        LEGAL_CODE_LOCALE_PATH="LOCALE_DIRS",
    )
    def test_get_translation_object_specified_translated(self):
        translation_object = MagicMock()

        with mock.patch(
            "i18n.utils.translation.trans_real.DjangoTranslation"
        ) as mock_djt:
            mock_djt.return_value = translation_object
            with mock.patch(
                "i18n.utils.translation.trans_real.translation"
            ) as mock_trans:
                result = get_translation_object(
                    domain="GETTEXT_DOMAIN",
                    language_code="LANGUAGE_CODE",
                    language_default="LANGUAGE_DEFAULT",
                )
        mock_djt.assert_called_with(
            domain="GETTEXT_DOMAIN",
            language="LANGUAGE_CODE",
            localedirs="LOCALE_DIRS",
        )
        mock_trans.assert_called_with("LANGUAGE_CODE")
        self.assertEqual(translation_object, result)

    @override_settings(
        LANGUAGES_AVAILABLE_DEEDS_UX=["LANGUAGE_DEFAULT"],
        LEGAL_CODE_LOCALE_PATH="LOCALE_DIRS",
    )
    def test_get_translation_object_default_translated(self):
        translation_object = MagicMock()

        with mock.patch(
            "i18n.utils.translation.trans_real.DjangoTranslation"
        ) as mock_djt:
            mock_djt.return_value = translation_object
            with mock.patch(
                "i18n.utils.translation.trans_real.translation"
            ) as mock_trans:
                result = get_translation_object(
                    domain="GETTEXT_DOMAIN",
                    language_code="LANGUAGE_CODE",
                    language_default="LANGUAGE_DEFAULT",
                )
        mock_djt.assert_called_with(
            domain="GETTEXT_DOMAIN",
            language="LANGUAGE_CODE",
            localedirs="LOCALE_DIRS",
        )
        mock_trans.assert_called_with("LANGUAGE_DEFAULT")
        self.assertEqual(translation_object, result)

    @override_settings(
        LANGUAGES_AVAILABLE_DEEDS_UX=[],
        LEGAL_CODE_LOCALE_PATH="LOCALE_DIRS",
    )
    def test_get_translation_object_untranslated(self):
        translation_object = MagicMock()

        with mock.patch(
            "i18n.utils.translation.trans_real.DjangoTranslation"
        ) as mock_djt:
            mock_djt.return_value = translation_object
            with mock.patch(
                "i18n.utils.translation.trans_real.translation"
            ) as mock_trans:
                result = get_translation_object(
                    domain="GETTEXT_DOMAIN",
                    language_code="LANGUAGE_CODE",
                    language_default="LANGUAGE_DEFAULT",
                )
        mock_djt.assert_called_with(
            domain="GETTEXT_DOMAIN",
            language="LANGUAGE_CODE",
            localedirs="LOCALE_DIRS",
        )
        mock_trans.assert_called_with(settings.LANGUAGE_CODE)
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
class PofileTestSimple(TestCase):
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


class PofileTestWithData(TestCase):
    def test_write_transstats_csv(self):
        output_file = "TESTFILE"

        with mock.patch("builtins.open", mock.mock_open()) as mo:
            write_transstats_csv(output_file)

        call = mock.call
        # Open output file and write CSV headers
        mo.assert_has_calls(
            [
                call(output_file, "w"),
                call().__enter__(),
                call().write(
                    '"lang_django","lang_locale","lang_transifex",'
                    '"num_messages","num_trans","num_fuzzy","percent_trans"\n'
                ),
            ]
        )
        # Open Aragonese PO FILE, read lines, and close it
        location = f"{settings.DEEDS_UX_LOCALE_PATH}/af"
        mo.assert_has_calls(
            [
                call(f"{location}/LC_MESSAGES/django.po", "rb"),
                call().__enter__(),
                call().readlines(),
                call().__exit__(None, None, None),
            ]
        )
        # Open Dutch PO FILE, read lines, and close it
        location = f"{settings.DEEDS_UX_LOCALE_PATH}/nl"
        mo.assert_has_calls(
            [
                call(f"{location}/LC_MESSAGES/django.po", "rb"),
                call().__enter__(),
                call().readlines(),
                call().__exit__(None, None, None),
            ]
        )
        # Open Aranese PO FILE, read lines, and close it
        location = f"{settings.DEEDS_UX_LOCALE_PATH}/oc_Aranes"
        mo.assert_has_calls(
            [
                call(f"{location}/LC_MESSAGES/django.po", "rb"),
                call().__enter__(),
                call().readlines(),
                call().__exit__(None, None, None),
            ]
        )
        # Open Serbian (Latin) PO FILE, read lines, and close it
        location = f"{settings.DEEDS_UX_LOCALE_PATH}/sr_Latn"
        mo.assert_has_calls(
            [
                call(f"{location}/LC_MESSAGES/django.po", "rb"),
                call().__enter__(),
                call().readlines(),
                call().__exit__(None, None, None),
            ]
        )
        # Open Chinese (Traditional) PO FILE, read lines, and close it
        location = f"{settings.DEEDS_UX_LOCALE_PATH}/zh_Hant"
        mo.assert_has_calls(
            [
                call(f"{location}/LC_MESSAGES/django.po", "rb"),
                call().__enter__(),
                call().readlines(),
                call().__exit__(None, None, None),
            ]
        )


class MappingTest(TestCase):
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
