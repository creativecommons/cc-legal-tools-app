import os
from unittest import mock

import git
from django.conf import settings
from django.test import TestCase, override_settings

from licenses.git_utils import (
    commit_and_push_changes,
    get_ssh_command,
    setup_local_branch,
)


class Dummy:
    """
    Just an empty object we can set attributes on,
    but that won't make them up as a Mock would.
    """


@override_settings(TRANSLATION_REPOSITORY_DIRECTORY="/trans/repo")
class SetupLocalBranchTest(TestCase):
    def test_branch_exists_nowhere(self):
        mock_repo = mock.MagicMock()
        mock_repo.branches = Dummy()  # won't have branchname as an attribute
        mock_repo.heads = Dummy()
        mock_branch = mock.MagicMock()
        setattr(mock_repo.heads, "ourbranch", mock_branch)
        mock_origin = mock.MagicMock()
        mock_origin.refs = Dummy()  # similar
        mock_parent_branch = mock.MagicMock()
        setattr(mock_origin.refs, "parentbranch", mock_parent_branch)
        mock_repo.remotes.origin = mock_origin

        setup_local_branch(mock_repo, "ourbranch", "parentbranch")

        mock_origin.fetch.assert_called_with()
        mock_repo.create_head.assert_called_with("ourbranch", mock_parent_branch)
        mock_origin.pull.assert_not_called()
        mock_branch.checkout.assert_called_with()

    def test_branch_exists_upstream(self):
        mock_repo = mock.MagicMock()
        mock_repo.branches = Dummy()  # won't have branchname as an attribute
        mock_origin = mock.MagicMock()
        mock_origin.refs = Dummy()  # similar
        mock_branch = mock.MagicMock()
        setattr(mock_repo.heads, "ourbranch", mock_branch)
        mock_upstream_branch = mock.MagicMock()
        setattr(mock_origin.refs, "ourbranch", mock_upstream_branch)
        mock_parent_branch = mock.MagicMock()
        setattr(mock_origin.refs, "parentbranch", mock_parent_branch)
        mock_repo.remotes.origin = mock_origin

        setup_local_branch(mock_repo, "ourbranch", "parentbranch")

        mock_origin.fetch.assert_called_with()
        mock_repo.create_head.assert_called_with("ourbranch", "origin/ourbranch")
        mock_origin.pull.assert_called_with("ourbranch:ourbranch")
        mock_branch.checkout.assert_called_with()

    def test_branch_exists_locally(self):
        mock_branch = mock.MagicMock()
        mock_repo = mock.MagicMock()
        setattr(mock_repo.heads, "ourbranch", mock_branch)
        mock_repo.branches = Dummy()
        setattr(mock_repo.branches, "ourbranch", mock_branch)
        mock_origin = mock.MagicMock()
        mock_origin.refs = Dummy()  # similar
        mock_branch = mock.MagicMock()
        setattr(mock_repo.heads, "ourbranch", mock_branch)
        mock_upstream_branch = mock.MagicMock()
        setattr(mock_origin.refs, "ourbranch", mock_upstream_branch)
        mock_parent_branch = mock.MagicMock()
        setattr(mock_origin.refs, "parentbranch", mock_parent_branch)
        mock_repo.remotes.origin = mock_origin

        setup_local_branch(mock_repo, "ourbranch", "parentbranch")

        mock_origin.fetch.assert_called_with()
        mock_repo.create_head.assert_not_called()
        mock_origin.pull.assert_called_with("ourbranch:ourbranch")
        mock_branch.checkout.assert_called_with()


class GetSshCommandTest(TestCase):
    @override_settings()
    def test_no_setting(self):
        del settings.TRANSLATION_REPOSITORY_DEPLOY_KEY
        with self.assertRaisesMessage(
            ValueError, "TRANSLATION_REPOSITORY_DEPLOY_KEY must be set"
        ):
            get_ssh_command()

    @override_settings(TRANSLATION_REPOSITORY_DEPLOY_KEY="/no/such/file")
    def test_no_file(self):
        with self.assertRaisesMessage(
            ValueError, "but that file does not exist or is not readable"
        ):
            get_ssh_command()

    @override_settings(TRANSLATION_REPOSITORY_DEPLOY_KEY="/fake/file")
    def test_mock_file(self):
        with mock.patch.object(os.path, "exists") as mock_exists:
            mock_exists.return_value = True
            result = get_ssh_command()
        self.assertEqual("ssh -o StrictHostKeyChecking=no -i '/fake/file'", result)


@override_settings(TRANSLATION_REPOSITORY_DIRECTORY="/trans/repo")
class CommitAndPushChangesTest(TestCase):
    @override_settings()
    def test_keyfile_not_set(self):
        del settings.TRANSLATION_REPOSITORY_DEPLOY_KEY
        branch_name = "ourbranch"
        commit_msg = "commit message"
        mock_repo = mock.MagicMock()
        mock_result = mock.MagicMock()
        mock_result.summary = "push result"
        mock_result.flags = 0
        mock_repo.remotes.origin.push.return_value = [mock_result]
        mock_repo.head.reference.name = branch_name

        with self.assertRaisesMessage(
            ValueError, "TRANSLATION_REPOSITORY_DEPLOY_KEY must be set"
        ):
            commit_and_push_changes(mock_repo, commit_msg)

    @override_settings(TRANSLATION_REPOSITORY_DEPLOY_KEY="/no/such/file")
    def test_keyfile_doesnt_exist(self):
        branch_name = "ourbranch"
        commit_msg = "commit message"
        mock_repo = mock.MagicMock()
        mock_result = mock.MagicMock()
        mock_result.summary = "push result"
        mock_result.flags = 0
        mock_repo.remotes.origin.push.return_value = [mock_result]
        mock_repo.head.reference.name = branch_name

        with self.assertRaisesMessage(
            ValueError, "but that file does not exist or is not readable"
        ):
            commit_and_push_changes(mock_repo, commit_msg)

    def test_no_push_results_failure(self):
        """For bad failures, push returns an empty list"""
        branch_name = "ourbranch"
        commit_msg = "commit message"
        mock_repo = mock.MagicMock()
        mock_repo.remotes.origin.push.return_value = []
        mock_repo.head.reference.name = branch_name

        with mock.patch("licenses.git_utils.get_ssh_command"):
            with self.assertRaisesMessage(Exception, "PUSH FAILED COMPLETELY"):
                commit_and_push_changes(mock_repo, commit_msg)

        mock_repo.index.commit.assert_called_with(commit_msg)
        mock_repo.remotes.origin.push.assert_called_with(f"{branch_name}:{branch_name}")

    def test_good_push_results(self):
        branch_name = "ourbranch"
        commit_msg = "commit message"
        mock_repo = mock.MagicMock()
        mock_result = mock.MagicMock()
        mock_result.summary = "push result"
        mock_result.flags = 0
        mock_repo.remotes.origin.push.return_value = [mock_result]
        mock_repo.head.reference.name = branch_name

        with mock.patch("licenses.git_utils.get_ssh_command"):
            commit_and_push_changes(mock_repo, commit_msg)

        mock_repo.index.commit.assert_called_with(commit_msg)
        mock_repo.remotes.origin.push.assert_called_with(f"{branch_name}:{branch_name}")

    def test_bad_push_results(self):
        branch_name = "ourbranch"
        commit_msg = "commit message"
        mock_repo = mock.MagicMock()
        mock_result = mock.MagicMock()
        mock_result.summary = "push result"
        mock_result.flags = git.PushInfo.ERROR
        mock_repo.remotes.origin.push.return_value = [mock_result]
        mock_repo.head.reference.name = branch_name

        with mock.patch("licenses.git_utils.get_ssh_command"):
            with self.assertRaisesMessage(Exception, "PUSH FAILED push result"):
                commit_and_push_changes(mock_repo, commit_msg)

        mock_repo.index.commit.assert_called_with(commit_msg)
        mock_repo.remotes.origin.push.assert_called_with(f"{branch_name}:{branch_name}")
