# Standard library
import os
import subprocess
from tempfile import TemporaryDirectory
from unittest import mock

# Third-party
import git
from django.conf import settings
from django.test import TestCase, override_settings

# First-party/Local
from licenses.git_utils import (
    branch_exists,
    commit_and_push_changes,
    get_branch,
    push_current_branch,
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
        self.origin_repo.create_head("otherbranch", "HEAD")
        self.origin_repo.create_head("main", "HEAD")
        # "checkout" main
        self.origin_repo.heads.main.checkout()
        # We want the main branch to be a different commit from otherbranch so
        # we can tell them apart, so add and commit a file.
        self.add_file(self.origin_repo)

        # Now clone the upstream repo and make otherbranch and main branches
        self.local_repo_path = os.path.join(self.temp_dir_path, "local")
        self.local_repo = self.origin_repo.clone(self.local_repo_path)
        self.local_repo.create_head("main", "origin/main")
        self.local_repo.create_head("otherbranch", "origin/otherbranch")
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
        return filename


@override_settings(TRANSLATION_REPOSITORY_DIRECTORY="/trans/repo")
class SetupLocalBranchTest(GitTestMixin, TestCase):
    def test_branch_exists_nowhere_but_parent_does(self):
        # No "ourbranch" locally or upstream, so we branch from origin/main
        #
        # setup_local_branch uses settings.OFFICIAL_GIT_BRANCH. This function
        # will fail if that value is not "main".
        setup_local_branch(self.local_repo, "ourbranch")

        our_branch = self.local_repo.heads.ourbranch
        self.assertEqual(self.origin_repo.heads.main.commit, our_branch.commit)
        self.assertNotEqual(
            self.origin_repo.heads.otherbranch.commit, our_branch.commit
        )

    def test_branch_exists_upstream(self):
        # There's an ourbranch upstream and we branch from that
        self.origin_repo.create_head("ourbranch")
        self.origin_repo.heads.ourbranch.checkout()
        self.add_file(self.origin_repo)
        self.origin_repo.heads.otherbranch.checkout()
        assert branch_exists(self.origin_repo, "ourbranch")

        setup_local_branch(self.local_repo, "ourbranch")
        our_branch = self.local_repo.heads.ourbranch
        self.assertEqual(
            self.origin_repo.heads.ourbranch.commit, our_branch.commit
        )
        self.assertNotEqual(
            self.origin_repo.heads.main.commit, our_branch.commit
        )
        self.assertNotEqual(
            self.origin_repo.heads.otherbranch.commit, our_branch.commit
        )

    def test_branch_exists_locally_and_upstream(self):
        # There's an ourbranch upstream
        self.origin_repo.create_head("ourbranch")
        self.origin_repo.heads.ourbranch.checkout()
        self.add_file(self.origin_repo)
        upstream_commit = self.origin_repo.heads.ourbranch.commit
        self.origin_repo.heads.otherbranch.checkout()  # Switch to otherbranch

        # We use the local branch, but update to the upstream tip
        self.local_repo.remotes.origin.fetch()
        self.local_repo.create_head("ourbranch")
        upstream_branch = get_branch(
            self.local_repo.remotes.origin, "ourbranch"
        )
        self.local_repo.heads.ourbranch.set_tracking_branch(upstream_branch)
        self.local_repo.heads.ourbranch.checkout()
        self.add_file(self.local_repo)
        old_local_repo_commit = self.local_repo.heads.ourbranch.commit
        self.local_repo.heads.otherbranch.checkout()  # Switch to otherbranch

        setup_local_branch(self.local_repo, "ourbranch")

        our_branch = self.local_repo.heads.ourbranch
        self.assertEqual(upstream_commit, our_branch.commit)
        self.assertNotEqual(old_local_repo_commit, our_branch.commit)


@override_settings(TRANSLATION_REPOSITORY_DIRECTORY="/trans/repo")
class CommitAndPushChangesTest(GitTestMixin, TestCase):
    def test_push(self):
        # Just make sure our helper function does what it should
        mock_repo = mock.MagicMock()
        mock_repo.active_branch.name = "name"
        with mock.patch("licenses.git_utils.run_git") as mock_run_git:
            push_current_branch(mock_repo)
        mock_run_git.assert_called_with(
            mock_repo,
            ["git", "push", "-u", "origin", mock_repo.active_branch.name],
        )

    def test_commit_with_push(self):
        mock_repo = mock.MagicMock()
        mock_repo.active_branch.name = "name"
        with mock.patch("licenses.git_utils.run_git") as mock_run_git:
            commit_and_push_changes(mock_repo, "commit msg", "", push=True)
        self.assertEqual(
            [
                mock.call(
                    mock_repo,
                    ["git", "commit", "--quiet", "-am", "commit msg"],
                ),
                mock.call(
                    mock_repo, ["git", "status", "--untracked", "--short"]
                ),
                mock.call(
                    mock_repo,
                    [
                        "git",
                        "push",
                        "-u",
                        "origin",
                        mock_repo.active_branch.name,
                    ],
                ),
            ],
            mock_run_git.call_args_list,
        )

    def test_changes_are_added(self):
        self.local_repo.heads.otherbranch.checkout()
        file_to_delete = self.add_file(
            self.local_repo
        )  # This is automatically committed
        path_to_delete = os.path.join(self.local_repo_path, file_to_delete)
        file_to_change = self.add_file(self.local_repo)
        path_to_change = os.path.join(self.local_repo_path, file_to_change)

        os.remove(path_to_delete)
        untracked_file_to_add = "untracked_file_to_add"
        path_to_add = os.path.join(self.local_repo_path, untracked_file_to_add)
        with open(path_to_add, "w") as f:
            f.write("untracked")
        with open(path_to_change, "w") as f:
            f.write("Now this file has different content")

        commit_and_push_changes(
            self.local_repo, "Add and remove test", "", push=False
        )

        subprocess.run(
            ["git", "status"],
            cwd=self.local_repo_path,
        )

        self.assertFalse(self.local_repo.is_dirty())

        # Switch to main - these files don't exist
        self.local_repo.heads.main.checkout()
        self.assertFalse(os.path.exists(path_to_add))
        self.assertFalse(os.path.exists(path_to_change))
        self.assertFalse(os.path.exists(path_to_delete))

        # Switch to otherbranch - these files are as expected.
        self.local_repo.heads.otherbranch.checkout()
        self.assertTrue(os.path.exists(path_to_add))
        self.assertTrue(os.path.exists(path_to_change))
        self.assertEqual(
            "Now this file has different content",
            open(path_to_change, "r").read(),
        )
        self.assertFalse(os.path.exists(path_to_delete))


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
                os.path.join(settings.ROOT_DIR, "ssh_wrapper.sh"),
                os.environ["GIT_SSH"],
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
