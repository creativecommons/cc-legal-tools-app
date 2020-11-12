import os
from tempfile import TemporaryDirectory
from unittest import mock

import git
from django.conf import settings
from django.test import TestCase, override_settings

from licenses.git_utils import (
    branch_exists,
    commit_and_push_changes,
    push,
    setup_local_branch,
    setup_to_call_git,
)


class Dummy:
    """
    Just an empty object we can set attributes on,
    but that won't make them up as a Mock would.
    """


class GitTestMixin:
    file_num = 0

    def setUp(self):
        self.temp_dir = TemporaryDirectory(prefix="cc-git-tests.")
        self.temp_dir_path = self.temp_dir.name

        self.upstream_repo_path = os.path.join(self.temp_dir_path, "upstream")
        os.makedirs(self.upstream_repo_path)
        self.origin_repo = git.Repo.init(self.upstream_repo_path)
        self.origin_repo.index.commit("Initial commit")
        self.origin_repo.create_head("master", "HEAD")
        # We want the develop branch to be a different commit from master so we can tell
        # them apart, so add and commit a file.
        self.origin_repo.create_head("develop", "HEAD")
        # "checkout" develop
        self.origin_repo.heads.develop.checkout()
        self.add_file(self.origin_repo)

        # Now clone the upstream repo and make master and develop branches
        self.local_repo_path = os.path.join(self.temp_dir_path, "local")
        self.local_repo = self.origin_repo.clone(self.local_repo_path)
        self.local_repo.create_head("develop", "origin/develop")
        self.local_repo.create_head("master", "origin/master")
        super().setUp()

    def add_file(self, repo):
        # Create new file in repo and commit
        self.file_num += 1
        filename = f"test{self.file_num}.txt"
        filepath = os.path.join(repo.working_tree_dir, filename)
        with open(filepath, "w") as f:
            f.write(filename)
        repo.index.add([filepath])
        repo.active_branch.commit = repo.index.commit(f"Add {filename}")
        repo.head.reset(index=True, working_tree=True)


@override_settings(TRANSLATION_REPOSITORY_DIRECTORY="/trans/repo")
class SetupLocalBranchTest(GitTestMixin, TestCase):
    def test_neither_branch_nor_parent_exist(self):
        with self.assertRaisesMessage(
            ValueError, "No such parent branch notthisoneeither"
        ):
            setup_local_branch(self.local_repo, "nosuchbranch", "notthisoneeither")

    def test_branch_exists_nowhere_but_parent_does(self):
        # No "ourbranch" locally or upstream, so we branch from origin/develop
        setup_local_branch(self.local_repo, "ourbranch", "develop")

        our_branch = self.local_repo.heads.ourbranch
        self.assertEqual(self.origin_repo.heads.develop.commit, our_branch.commit)
        self.assertNotEqual(self.origin_repo.heads.master.commit, our_branch.commit)

    def test_branch_exists_upstream(self):
        # There's an ourbranch upstream and we branch from that
        self.origin_repo.create_head("ourbranch")
        self.origin_repo.heads.ourbranch.checkout()
        self.add_file(self.origin_repo)
        self.origin_repo.heads.master.checkout()
        assert branch_exists(self.origin_repo, "ourbranch")

        setup_local_branch(self.local_repo, "ourbranch", "ourbranch")
        our_branch = self.local_repo.heads.ourbranch
        self.assertEqual(self.origin_repo.heads.ourbranch.commit, our_branch.commit)
        self.assertNotEqual(self.origin_repo.heads.develop.commit, our_branch.commit)
        self.assertNotEqual(self.origin_repo.heads.master.commit, our_branch.commit)

    def test_branch_exists_locally(self):
        # We do NOT use the local branch
        self.local_repo.create_head("ourbranch")
        self.local_repo.heads.ourbranch.checkout()
        self.add_file(self.local_repo)
        old_local_repo_commit = self.local_repo.heads.ourbranch.commit
        self.local_repo.heads.master.checkout()  # Switch to master

        # There's an ourbranch upstream and we branch from that
        self.origin_repo.create_head("parentbranch")
        self.origin_repo.heads.parentbranch.checkout()
        self.add_file(self.origin_repo)
        self.origin_repo.heads.master.checkout()

        setup_local_branch(self.local_repo, "ourbranch", "parentbranch")
        our_branch = self.local_repo.heads.ourbranch
        self.assertEqual(self.origin_repo.heads.parentbranch.commit, our_branch.commit)
        self.assertNotEqual(old_local_repo_commit, our_branch.commit)


@override_settings(TRANSLATION_REPOSITORY_DIRECTORY="/trans/repo")
class CommitAndPushChangesTest(GitTestMixin, TestCase):
    def test_no_push_results_failure(self):
        """For bad failures, push returns an empty list"""
        with mock.patch("licenses.git_utils.push") as mock_push:
            mock_push.return_value = []
            with self.assertRaisesMessage(Exception, "PUSH FAILED COMPLETELY"):
                commit_and_push_changes(self.local_repo, "commit")

    def test_good_push_results(self):
        commit_msg = "commit message"
        mock_result = mock.MagicMock()
        mock_result.summary = "push result"
        mock_result.flags = 0

        with mock.patch("licenses.git_utils.push") as mock_push:
            mock_push.return_value = [mock_result]
            commit_and_push_changes(self.local_repo, commit_msg)

    def test_bad_push_results(self):
        commit_msg = "commit message"
        mock_result = mock.MagicMock()
        mock_result.summary = "push result"
        mock_result.flags = git.PushInfo.ERROR

        with mock.patch("licenses.git_utils.push") as mock_push:
            mock_push.return_value = [mock_result]
            with self.assertRaisesMessage(Exception, "PUSH FAILED push result"):
                commit_and_push_changes(self.local_repo, commit_msg)

    def test_push(self):
        # Just make sure our helper function does what it should
        mock_repo = mock.MagicMock()
        mock_repo.head.reference = mock.MagicMock()
        mock_repo.head.reference.name = "some name"
        mock_repo.remotes.origin.push.return_value = ["something"]
        out = push(mock_repo)
        self.assertEqual(["something"], out)


class SetupToCallGitTest(TestCase):
    def test_setup_to_call_git_empty_env(self):
        # Use defaults if nothing in env already
        with mock.patch.object(os, "environ", new={}):
            for name in [
                "GIT_SSH",
                "TRANSLATION_REPOSITORY_DEPLOY_KEY",
                "PROJECT_ROOT",
            ]:
                if name in os.environ:
                    del os.environ[name]
            setup_to_call_git()
            self.assertEqual(
                os.path.join(settings.ROOT_DIR, "ssh_wrapper.sh"), os.environ["GIT_SSH"]
            )
            self.assertEqual(
                settings.TRANSLATION_REPOSITORY_DEPLOY_KEY,
                os.environ["TRANSLATION_REPOSITORY_DEPLOY_KEY"],
            )
            self.assertEqual(settings.ROOT_DIR, os.environ["PROJECT_ROOT"])

    def test_setup_to_call_git_full_env(self):
        # If value in env, use them
        mock_env = {
            "GIT_SSH": "mock_git",
            "TRANSLATION_REPOSITORY_DEPLOY_KEY": "mock_key",
            "PROJECT_ROOT": "mock_root",
        }
        with mock.patch.object(os, "environ", new=mock_env):
            setup_to_call_git()
            self.assertEqual("mock_git", os.environ["GIT_SSH"])
            self.assertEqual(
                "mock_key", os.environ["TRANSLATION_REPOSITORY_DEPLOY_KEY"]
            )
            self.assertEqual("mock_root", os.environ["PROJECT_ROOT"])
