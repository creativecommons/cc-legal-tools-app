# Standard library
import logging
import os
import subprocess
from typing import List

# Third-party
import git
from django.conf import settings

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


def run_git(repo: git.Repo, command: List[str]):
    # print(" ".join(command))
    result = subprocess.run(command, cwd=repo.working_tree_dir)
    if result.returncode != 0:
        raise Exception("Something went wrong running git")


def setup_to_call_git(env=None):
    """
    Call this to set the environment before starting to use git.
    Safe to call any number of times.

    If env is none, it'll use os.environ, which is the usual case.
    You can pass a dictionary as env for testing.
    """
    if env is None:
        env = os.environ
    # Use custom ssh command to use the deploy key when pushing
    if "GIT_SSH" not in env:
        env["GIT_SSH"] = os.path.join(settings.ROOT_DIR, "ssh_wrapper.sh")
    if "TRANSLATION_REPOSITORY_DEPLOY_KEY" not in env:
        env[
            "TRANSLATION_REPOSITORY_DEPLOY_KEY"
        ] = settings.TRANSLATION_REPOSITORY_DEPLOY_KEY
    if "PROJECT_ROOT" not in env:
        env["PROJECT_ROOT"] = settings.ROOT_DIR


def remote_branch_names(remote: git.Remote) -> List[str]:
    """
    Return list of names of branches on the remote, without any leading remote
    name.
    E.g. ["branch", "branch"], NOT ["origin/branch", "origin/branch"]
    """

    full_branch_names = [
        ref.name for ref in remote.refs
    ]  # ["origin/a", "origin/b"]
    prefix_length = len(remote.name) + 1  # "origin/"
    return [name[prefix_length:] for name in full_branch_names]


def get_branch(repo_or_remote, name):
    """
    Get a branch for a repo or remote.
    Returns a branch (head)
    Or none if there's no such branch there.
    """
    if isinstance(repo_or_remote, git.Remote):
        remote = repo_or_remote
        prefix_length = len(remote.name) + 1  # "origin/"
        for ref in remote.refs:
            full_name = ref.name
            if full_name[prefix_length:] == name:
                return ref
    else:
        repo = repo_or_remote
        return getattr(repo.heads, name)


def branch_exists(repo_or_remote, name):
    if isinstance(repo_or_remote, git.Remote):
        return name in remote_branch_names(repo_or_remote)
    else:
        return hasattr(repo_or_remote.branches, name)


def kill_branch(repo, name):
    # delete the branch, regardless
    # Checkout another branch to make sure we can delete the one we want
    # Also makes sure we can't delete "develop"
    repo.heads.develop.checkout()
    # Delete the local branch
    repo.delete_head(name, force=True)


def setup_local_branch(repo: git.Repo, branch_name: str):
    """
    Ensure we have a local branch named 'branch_name', it's at the same
    state as its upstream parent, and checked out.

    THIS DISCARDS ANY LOCAL CHANGES!!!!
    """
    origin = repo.remotes.origin
    origin.fetch()

    # Hard reset in case the repo is dirty
    repo.head.reset(index=True, working_tree=True)

    if not branch_exists(repo, branch_name):
        # Is there an upstream branch with the same name?
        if branch_exists(origin, branch_name):
            repo.create_head(branch_name, get_branch(origin, branch_name))
            branch = get_branch(repo, branch_name)
            if not branch.tracking_branch():
                branch.set_tracking_branch(get_branch(origin, branch_name))
            assert branch.tracking_branch()
            branch.checkout(force=True)
        else:
            # No upstream branch either. Branch from the official branch
            # upstream, but don't track it.
            upstream = get_branch(origin, settings.OFFICIAL_GIT_BRANCH)
            repo.create_head(branch_name, upstream)
            branch = get_branch(repo, branch_name)
            assert not branch.tracking_branch()
            branch.checkout(force=True)
    else:
        # branch exists.
        branch = get_branch(repo, branch_name)
        branch.checkout(force=True)
        if branch.tracking_branch():
            # Use upstream branch tip commit
            repo.head.reset(
                f"origin/{branch_name}", index=True, working_tree=True
            )
        return


def push_current_branch(repo: git.Repo):
    # Separate function just so we can mock it for testing
    current_branch = repo.active_branch
    run_git(repo, ["git", "push", "-u", "origin", current_branch.name])


def commit_and_push_changes(
    repo: git.Repo, commit_msg: str, relpath: str, push: bool
):
    """
    Commit all changes under relpath to current branch, and maybe push upstream
    """
    untracked_to_add = [
        path for path in repo.untracked_files if path.startswith(relpath)
    ]
    if untracked_to_add:
        run_git(repo, ["git", "add", "--force"] + untracked_to_add)

    run_git(repo, ["git", "commit", "--quiet", "-am", commit_msg])
    run_git(
        repo,
        ["git", "status", "--untracked", "--short"],
    )
    if push:
        push_current_branch(repo)
