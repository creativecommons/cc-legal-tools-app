# Standard library
import datetime
import os
from unittest import mock
from unittest.mock import MagicMock, call

# Third-party
import git
import polib
import requests
from django.conf import settings
from django.test import TestCase, override_settings
from django.utils.timezone import now, utc

# First-party/Local
from i18n import DEFAULT_LANGUAGE_CODE
from i18n.utils import get_pofile_content
from licenses.models import LegalCode, TranslationBranch
from licenses.tests.factories import LegalCodeFactory, LicenseFactory
from licenses.transifex import TransifexAuthRequests, TransifexHelper

TEST_PROJECT_SLUG = "proj"
TEST_ORGANIZATION_SLUG = "org"
TEST_TOKEN = "aaaaabbbbbb"
TEST_TRANSIFEX_SETTINGS = {
    "ORGANIZATION_SLUG": TEST_ORGANIZATION_SLUG,
    "PROJECT_SLUG": TEST_PROJECT_SLUG,
    "API_TOKEN": TEST_TOKEN,
}

# To shorten lines of code, make a short alias
# for  'mock.patch' and 'mock.patch.object'
mp = mock.patch
mpo = mock.patch.object


class DummyRepo:
    def __init__(self, path):
        self.index = MagicMock()
        self.remotes = MagicMock()
        self.branches = MagicMock()
        self.heads = MagicMock()

    # def __str__(self):
    #     return "a dummy repo"

    def __enter__(self):
        return self

    def __exit__(self, *a, **k):
        pass

    def is_dirty(self):
        return False

    def delete_head(self, name, force):
        pass


@override_settings(
    TRANSIFEX=TEST_TRANSIFEX_SETTINGS,
    TRANSLATION_REPOSITORY_DIRECTORY="/trans/repo",
)
class TestTransifex(TestCase):
    def setUp(self):
        self.helper = TransifexHelper()

    def test_request20_success(self):
        with mpo(self.helper.api_v20, "get") as mock_get:
            mock_get.return_value = mock.MagicMock(status_code=200)
            self.helper.request20(
                path="foo/bar", method="get", data={"a": 1}, files=[(1, 2)]
            )
        mock_get.assert_called_with(
            "https://www.transifex.com/api/2/foo/bar",
            data={"a": 1},
            files=[(1, 2)],
        )

    def test_request25_success(self):
        with mpo(self.helper.api_v25, "get") as mock_get:
            mock_get.return_value = mock.MagicMock(status_code=200)
            self.helper.request25(
                path="foo/bar", method="get", data={"a": 1}, files=[(1, 2)]
            )
        mock_get.assert_called_with(
            "https://api.transifex.com/foo/bar", data={"a": 1}, files=[(1, 2)]
        )

    def test_request20_failure(self):
        error_response = requests.Response()
        error_response.status_code = 500
        error_response.reason = "testing"

        with mpo(self.helper.api_v20, "get") as mock_get:
            mock_get.return_value = error_response
            with self.assertRaises(requests.HTTPError):
                self.helper.request20(
                    path="foo/bar", method="get", data={"a": 1}, files=[(1, 2)]
                )
        mock_get.assert_called_with(
            "https://www.transifex.com/api/2/foo/bar",
            data={"a": 1},
            files=[(1, 2)],
        )

    def test_request25_failure(self):
        error_response = requests.Response()
        error_response.status_code = 500
        error_response.reason = "testing"

        with mpo(self.helper.api_v25, "get") as mock_get:
            mock_get.return_value = error_response
            with self.assertRaises(requests.HTTPError):
                self.helper.request25(
                    path="foo/bar", method="get", data={"a": 1}, files=[(1, 2)]
                )
        mock_get.assert_called_with(
            "https://api.transifex.com/foo/bar", data={"a": 1}, files=[(1, 2)]
        )

    def test_get_transifex_resources(self):
        with mpo(self.helper, "request25") as mock_request:
            mock_request.return_value.json.return_value = {"a": 1}
            result = self.helper.get_transifex_resources()
        mock_request.assert_called_with(
            "get", "organizations/org/projects/proj/resources/"
        )
        self.assertEqual({"a": 1}, result)

    def test_files_argument(self):
        result = self.helper.files_argument("foo", "bar", "baz")
        self.assertEqual(
            [("foo", ("bar", "baz", "application/octet-stream"))], result
        )

    def test_create_resource(self):
        with mpo(self.helper, "request20") as mock_request:
            self.helper.create_resource(
                "slug", "name", "pofilename", "pofilecontent"
            )
        mock_request.assert_called_with(
            "post",
            "project/proj/resources/",
            data={"slug": "slug", "name": "name", "i18n_type": "PO"},
            files=[
                (
                    "content",
                    (
                        "pofilename",
                        "pofilecontent",
                        "application/octet-stream",
                    ),
                )
            ],
        )

    def test_update_source_messages(self):
        with mpo(self.helper, "request20") as mock_request:
            self.helper.update_source_messages(
                "slug", "pofilename", "pofilecontent"
            )
        mock_request.assert_called_with(
            "put",
            "project/proj/resource/slug/content/",
            files=[
                (
                    "content",
                    (
                        "pofilename",
                        "pofilecontent",
                        "application/octet-stream",
                    ),
                )
            ],
        )

    def test_update_translations(self):
        with mpo(self.helper, "request20") as mock_request:
            self.helper.update_translations(
                "slug", "lang", "pofilename", "pofilecontent"
            )
        mock_request.assert_called_with(
            "put",
            "project/proj/resource/slug/translation/lang/",
            files=[
                (
                    "file",
                    (
                        "pofilename",
                        "pofilecontent",
                        "application/octet-stream",
                    ),
                )
            ],
        )

    def test_upload_messages_to_transifex_no_resource_yet(self):
        # English so we can create the resource
        license = LicenseFactory(license_code="by-nd", version="4.0")
        legalcode = LegalCodeFactory(
            license=license,
            language_code=DEFAULT_LANGUAGE_CODE,
        )

        pofile_content = """
msgid ""
msgstr ""
"Project-Id-Version: by-nd-4.0\n"
"Language: en\n"
"MIME-Version: 1.0\n"
"Content-Type: text/plain; charset=utf-8\n"
"Content-Transfer-Encoding: 8bit\n"

msgid "license_medium"
msgstr "Attribution-NoDerivatives 4.0 International"
        """
        english_pofile = polib.pofile(pofile=pofile_content)

        with mpo(self.helper, "get_transifex_resources") as mock_gtr:
            mock_gtr.return_value = []

            with mpo(self.helper, "create_resource") as mock_create_resource:
                with mpo(legalcode, "get_pofile") as mock_gpwem:
                    mock_gpwem.return_value = english_pofile
                    with mp(
                        "licenses.transifex.get_pofile_content"
                    ) as mock_gpc:
                        mock_gpc.return_value = "not really"
                        self.helper.upload_messages_to_transifex(legalcode)

        mock_create_resource.assert_called_with(
            "by-nd_40",
            "CC BY-ND 4.0",
            "/trans/repo/legalcode/en/LC_MESSAGES/by-nd_40.po",
            "not really",
        )
        mock_gpwem.assert_called_with()
        mock_gtr.assert_called_with()

    def test_upload_messages_to_transifex_no_resource_yet_not_english(self):
        # Must be english or we can't create the resource
        # If we try this with a non-english language and there's no resource,
        # we should get an error.
        legalcode = LegalCodeFactory(language_code="es")
        test_pofile = polib.POFile()

        with mpo(self.helper, "get_transifex_resources") as mock_gtr:
            mock_gtr.return_value = []
            with mpo(legalcode, "get_pofile") as mock_gpwem:
                mock_gpwem.return_value = test_pofile
                with self.assertRaisesMessage(
                    ValueError, "Must upload English first"
                ):
                    self.helper.upload_messages_to_transifex(legalcode)

        mock_gtr.assert_called_with()
        mock_gpwem.assert_called_with()

    def test_upload_messages_english_resource_exists(self):
        # English because it's the source messages and is handled differently
        license = LicenseFactory(license_code="by-nd", version="4.0")
        legalcode = LegalCodeFactory(
            license=license,
            language_code=DEFAULT_LANGUAGE_CODE,
        )
        test_resources = [
            {
                "slug": license.resource_slug,
            }
        ]
        test_pofile = polib.POFile()
        with mpo(self.helper, "get_transifex_resources") as mock_gtr:
            mock_gtr.return_value = test_resources
            with mp("licenses.transifex.get_pofile_content") as mock_gpc:
                mock_gpc.return_value = "not really"
                with mpo(self.helper, "update_source_messages") as mock_usm:
                    self.helper.upload_messages_to_transifex(
                        legalcode, test_pofile
                    )

        mock_gtr.assert_called_with()
        mock_gpc.assert_called_with(test_pofile)
        mock_usm.assert_called_with(
            "by-nd_40",
            "/trans/repo/legalcode/en/LC_MESSAGES/by-nd_40.po",
            "not really",
        )

    def test_upload_messages_non_english_resource_exists(self):
        # non-English because it's not the source messages and is handled
        # differently
        license = LicenseFactory(license_code="by-nd", version="4.0")
        legalcode = LegalCodeFactory(license=license, language_code="fr")
        test_resources = [
            {
                "slug": license.resource_slug,
            }
        ]
        test_pofile = mock.MagicMock()
        with mpo(self.helper, "get_transifex_resources") as mock_gtr:
            mock_gtr.return_value = test_resources
            with mp("licenses.transifex.get_pofile_content") as mock_gpc:
                mock_gpc.return_value = "not really"
                with mpo(self.helper, "update_translations") as mock_ut:
                    self.helper.upload_messages_to_transifex(
                        legalcode, test_pofile
                    )

        mock_gtr.assert_called_with()
        mock_gpc.assert_called_with(test_pofile)
        mock_ut.assert_called_with(
            "by-nd_40",
            "fr",
            "/trans/repo/legalcode/fr/LC_MESSAGES/by-nd_40.po",
            "not really",
        )

    def test_get_transifex_resource_stats(self):
        # First call returns a response whose json value is a list of dicts
        # with slug keys
        call0_response = MagicMock()
        call0_response.json.return_value = [{"slug": "slug0"}]

        # second call is more data about slug0 - FIXME
        call1_response = MagicMock()
        call1_response.json.return_value = {"stats": "stats1"}
        with mpo(self.helper, "request25") as mock_request25:
            # Return values for each call to request25
            mock_request25.side_effect = [
                call0_response,
                call1_response,
            ]
            result = self.helper.get_transifex_resource_stats()
        calls = mock_request25.call_args_list
        self.assertEqual(
            [
                call("get", "organizations/org/projects/proj/resources/"),
                call("get", "organizations/org/projects/proj/resources/slug0"),
            ],
            calls,
        )
        self.assertEqual({"slug0": "stats1"}, result)


@override_settings(
    TRANSLATION_REPOSITORY_DIRECTORY="/trans/repo",
)
class CheckForTranslationUpdatesTest(TestCase):
    def test_check_for_translation_updates_with_dirty_repo(self):
        mock_repo = MagicMock()
        mock_repo.__str__.return_value = "mock_repo"
        mock_repo.is_dirty.return_value = True
        with mock.patch.object(git, "Repo") as mock_Repo:
            mock_Repo.return_value.__enter__.return_value = mock_repo
            helper = TransifexHelper()
            with self.assertRaisesMessage(
                Exception, "is dirty. We cannot continue."
            ):
                helper.check_for_translation_updates()

    def test_check_for_translation_updates_with_no_legalcodes(self):
        mock_repo = MagicMock()
        mock_repo.__str__.return_value = "mock_repo"
        mock_repo.is_dirty.return_value = False
        with mock.patch.object(git, "Repo") as mock_Repo:
            mock_Repo.return_value.__enter__.return_value = mock_repo
            with mock.patch.object(
                TransifexHelper, "get_transifex_resource_stats"
            ) as mock_get_transifex_resource_stats:
                mock_get_transifex_resource_stats.return_value = {}
                helper = TransifexHelper()
                helper.check_for_translation_updates()

    def test_check_for_translation_updates_first_time(self):
        # We don't have a 'translation_last_update' yet to compare to.
        self.help_test_check_for_translation_updates(
            first_time=True, changed=None
        )

    def test_check_for_translation_updates_unchanged(self):
        # The translation update timestamp has not changed
        self.help_test_check_for_translation_updates(
            first_time=False, changed=False
        )

    def test_check_for_translation_updates_changed(self):
        # 'translation' is newer than translation_last_update
        self.help_test_check_for_translation_updates(
            first_time=False, changed=True
        )

    def test_check_for_translation_updates_create_resource(self):
        # the resource isn't (yet) on transifex
        self.help_test_check_for_translation_updates(
            first_time=False, changed=True, resource_exists=False
        )

    def test_check_for_translation_updates_upload_language(self):
        # The language isn't (yet) on transifex
        self.help_test_check_for_translation_updates(
            first_time=False, changed=True, language_exists=False
        )

    def help_test_check_for_translation_updates(
        self, first_time, changed, resource_exists=True, language_exists=True
    ):
        """
        Helper to test several conditions, since all the setup is so
        convoluted.
        """
        language_code = "zh-Hans"
        license = LicenseFactory(version="4.0", license_code="by-nd")

        first_translation_update_datetime = datetime.datetime(
            2007, 1, 25, 12, 0, 0, tzinfo=utc
        )
        changed_translation_update_datetime = datetime.datetime(
            2020, 9, 30, 13, 11, 52, tzinfo=utc
        )

        if first_time:
            # We don't yet know when the last update was.
            legalcode_last_update = None
        else:
            # The last update we know of was at this time.
            legalcode_last_update = first_translation_update_datetime

        legalcode = LegalCodeFactory(
            license=license,
            language_code=language_code,
            translation_last_update=legalcode_last_update,
        )
        resource_slug = license.resource_slug

        # Will need an English legalcode if we need to create the resource
        if not resource_exists and language_code != DEFAULT_LANGUAGE_CODE:
            LegalCodeFactory(
                license=license,
                language_code=DEFAULT_LANGUAGE_CODE,
            )

        # 'timestamp' returns on translation stats from transifex
        if changed:
            # now it's the newer time
            timestamp = changed_translation_update_datetime.isoformat()
        else:
            # it's still the first time
            timestamp = first_translation_update_datetime.isoformat()

        mock_repo = MagicMock()
        mock_repo.is_dirty.return_value = False

        legalcodes = [legalcode]
        dummy_repo = DummyRepo("/trans/repo")

        # A couple of places use git.Repo(path) to get a git repo object. Have
        # them all get back our same dummy repo.
        def dummy_repo_factory(path):
            return dummy_repo

        helper = TransifexHelper()

        with mpo(
            helper, "handle_legalcodes_with_updated_translations"
        ) as mock_handle_legalcodes, mpo(
            helper, "get_transifex_resource_stats"
        ) as mock_get_transifex_resource_stats, mpo(
            helper, "create_resource"
        ) as mock_create_resource, mpo(
            LegalCode, "get_pofile"
        ) as mock_get_pofile, mpo(
            helper, "upload_messages_to_transifex"
        ) as mock_upload:
            if resource_exists:
                if language_exists:
                    mock_get_transifex_resource_stats.return_value = {
                        resource_slug: {
                            language_code: {
                                "translated": {
                                    "last_activity": timestamp,
                                }
                            }
                        }
                    }
                else:
                    # language does not exist first time, does the second time
                    mock_get_transifex_resource_stats.side_effect = [
                        {resource_slug: {}},
                        {
                            resource_slug: {
                                language_code: {
                                    "translated": {
                                        "last_activity": timestamp,
                                    }
                                }
                            }
                        },
                    ]
            else:
                # First time does not exist, second time does
                mock_get_transifex_resource_stats.side_effect = [
                    {},
                    {
                        resource_slug: {
                            language_code: {
                                "translated": {
                                    "last_activity": timestamp,
                                }
                            }
                        }
                    },
                ]
                # Will need pofile
                mock_get_pofile.return_value = polib.POFile()
            helper.check_for_translation_updates_with_repo_and_legalcodes(
                dummy_repo, legalcodes
            )

        if not resource_exists:
            # Should have tried to create resource
            mock_create_resource.assert_called_with(
                resource_slug=resource_slug,
                resource_name=legalcode.license.fat_code(),
                pofilename=os.path.basename(legalcode.translation_filename()),
                pofile_content=get_pofile_content(
                    mock_get_pofile.return_value
                ),
            )
        else:
            # Not
            mock_create_resource.assert_not_called()

        if language_exists:
            mock_upload.assert_not_called()
        else:
            mock_upload.assert_called()

        mock_get_transifex_resource_stats.assert_called_with()
        legalcode.refresh_from_db()
        if changed:
            # we mocked the actual processing, so...
            self.assertEqual(
                first_translation_update_datetime,
                legalcode.translation_last_update,
            )
            mock_handle_legalcodes.assert_called_with(dummy_repo, [legalcode])
        else:
            self.assertEqual(
                first_translation_update_datetime,
                legalcode.translation_last_update,
            )
            mock_handle_legalcodes.assert_called_with(dummy_repo, [])
        return

    def test_handle_legalcodes_with_updated_translations(self):
        helper = TransifexHelper()
        dummy_repo = DummyRepo("/trans/repo")

        # No legalcodes, shouldn't call anything or return anything
        result = helper.handle_legalcodes_with_updated_translations(
            dummy_repo, []
        )
        self.assertEqual([], result)

        # legalcodes for two branches
        legalcode1 = LegalCodeFactory(
            license__version="4.0",
            license__license_code="by-nc",
            language_code="fr",
        )
        legalcode2 = LegalCodeFactory(
            license__version="4.0",
            license__license_code="by-nd",
            language_code="de",
        )
        with mpo(helper, "handle_updated_translation_branch") as mock_handle:
            result = helper.handle_legalcodes_with_updated_translations(
                dummy_repo, [legalcode1, legalcode2]
            )
        self.assertEqual(
            [legalcode1.branch_name(), legalcode2.branch_name()], result
        )
        self.assertEqual(
            [
                mock.call(dummy_repo, [legalcode1]),
                mock.call(dummy_repo, [legalcode2]),
            ],
            mock_handle.call_args_list,
        )

    def test_handle_updated_translation_branch(self):
        helper = TransifexHelper()
        dummy_repo = DummyRepo("/trans/repo")
        result = helper.handle_updated_translation_branch(dummy_repo, [])
        self.assertIsNone(result)
        legalcode1 = LegalCodeFactory(
            license__version="4.0",
            license__license_code="by-nc",
            language_code="fr",
        )
        legalcode2 = LegalCodeFactory(
            license__version="4.0",
            license__license_code="by-nd",
            language_code="fr",
        )
        with mp("licenses.transifex.setup_local_branch") as mock_setup, mpo(
            helper, "update_branch_for_legalcode"
        ) as mock_update_branch, mp(
            "licenses.transifex.call_command"
        ) as mock_call_command, mp(
            "licenses.transifex.commit_and_push_changes"
        ) as mock_commit:
            # setup_local_branch
            # update_branch_for_legalcode
            # commit_and_push_changes
            # branch_object.save()
            result = helper.handle_updated_translation_branch(
                dummy_repo, [legalcode1, legalcode2]
            )
        self.assertIsNone(result)
        mock_setup.assert_called_with(dummy_repo, legalcode1.branch_name())
        # Should have published static files for this branch
        expected = [
            mock.call("publish", branch_name=legalcode1.branch_name()),
        ]
        self.assertEqual(expected, mock_call_command.call_args_list)
        trb = TranslationBranch.objects.get()
        expected = [
            mock.call(dummy_repo, legalcode1, trb),
            mock.call(dummy_repo, legalcode2, trb),
        ]
        self.assertEqual(expected, mock_update_branch.call_args_list)
        mock_commit.assert_called_with(
            dummy_repo, "Translation changes from Transifex.", "", push=True
        )

    def test_update_branch_for_legalcode(self):
        helper = TransifexHelper()
        dummy_repo = DummyRepo("/trans/repo")
        legalcode = LegalCodeFactory(
            license__version="4.0",
            license__license_code="by-nc",
            language_code="fr",
        )
        helper._stats = {
            legalcode.license.resource_slug: {
                legalcode.language_code: {
                    "translated": {
                        "last_activity": now().isoformat(),
                    }
                }
            }
        }
        trb = TranslationBranch.objects.create(
            branch_name=legalcode.branch_name(),
            version=legalcode.license.version,
            language_code=legalcode.language_code,
            complete=False,
        )
        content = b"wxyz"
        # transifex_get_pofile_content
        # save_content_as_pofile_and_mofile
        with mpo(
            helper, "transifex_get_pofile_content"
        ) as mock_get_content, mp(
            "licenses.transifex.save_content_as_pofile_and_mofile"
        ) as mock_save:
            mock_get_content.return_value = content
            mock_save.return_value = [legalcode.translation_filename()]
            result = helper.update_branch_for_legalcode(
                dummy_repo, legalcode, trb
            )
        self.assertIsNone(result)
        mock_get_content.assert_called_with(
            legalcode.license.resource_slug, legalcode.language_code
        )
        mock_save.assert_called_with(legalcode.translation_filename(), content)
        self.assertEqual({legalcode}, set(trb.legalcodes.all()))
        relpath = os.path.relpath(
            legalcode.translation_filename(),
            settings.TRANSLATION_REPOSITORY_DIRECTORY,
        )
        dummy_repo.index.add.assert_called_with([relpath])

    def test_transifex_get_pofile_content(self):
        helper = TransifexHelper()
        with mpo(helper, "request20") as mock_req20:
            mock_req20.return_value = mock.MagicMock(content=b"xxxxxx")
            result = helper.transifex_get_pofile_content("slug", "lang")
        mock_req20.assert_called_with(
            "get",
            "project/CC/resource/slug/translation/lang/"
            "?mode=translator&file=PO",
        )
        self.assertEqual(result, b"xxxxxx")


class TestTransifexAuthRequests(TestCase):
    def test_transifex_auth_requests(self):
        token = "frenchfriedpotatoes"
        auth = TransifexAuthRequests(token)
        self.assertEqual(token, auth.token)
        auth2 = TransifexAuthRequests(token)
        self.assertEqual(auth, auth2)
        auth3 = TransifexAuthRequests("another token")
        self.assertNotEqual(auth, auth3)
        r = mock.Mock(headers={})
        result = auth(r)
        self.assertEqual(r, result)
        self.assertEqual(
            {"Authorization": "Basic YXBpOmZyZW5jaGZyaWVkcG90YXRvZXM="},
            result.headers,
        )
