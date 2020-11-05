import logging
import os
from typing import List

import git
from django.conf import settings

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


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
    Return list of names of branches on the remote, without any leading remote name.
    E.g. ["branch", "branch"], NOT ["origin/branch", "origin/branch"]
    """

    full_branch_names = [ref.name for ref in remote.refs]  # ["origin/a", "origin/b"]
    prefix_length = len(remote.name) + 1  # "origin/"
    return [name[prefix_length:] for name in full_branch_names]


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


def setup_local_branch(repo: git.Repo, branch_name: str, parent_branch_name: str):
    """
    Ensure we have a local branch named 'branch_name'.  WARNING: If there's
    already such a branch, we first DELETE it. The local repo is considered
    a temporary working place. The upstream repo is authoritative.
    Then we pull from upstream ('origin'), or create as a branch from parent_branch_name.
    If there's an upstream one, pull from it to make sure we're up to date.
    Check it out.
    """
    if branch_name == "develop":
        raise ValueError(f"Should not be trying to work on branch {branch_name}")

    if branch_exists(repo, branch_name):
        kill_branch(repo, branch_name)

    origin = getattr(repo.remotes, "origin")
    origin.fetch()
    if not branch_exists(origin, parent_branch_name):
        raise ValueError(f"No such parent branch {parent_branch_name} on origin")

    # Now create branch fresh. Does upstream already have a branch with this name?
    if branch_exists(origin, branch_name):
        # Create locally, based on upstream
        repo.create_head(branch_name, f"origin/{branch_name}")
    else:
        # Nope, need to create from scratch from the upstream with "parent_branch_name"
        parent_branch = getattr(origin.refs, parent_branch_name)
        repo.create_head(branch_name, parent_branch)

    # Checkout the branch
    branch = getattr(repo.heads, branch_name)
    branch.checkout()


def push(repo: git.Repo):
    # Separate function just so we can mock it for testing
    current_branch = repo.head.reference
    branch_name = current_branch.name
    return repo.remotes.origin.push(f"{branch_name}:{branch_name}")


def commit_and_push_changes(repo: git.Repo, commit_msg: str):
    """Commit new translation changes to current branch, and push upstream"""
    index = repo.index
    index.commit(commit_msg)
    results = push(repo)
    if len(results) == 0:
        raise Exception("PUSH FAILED COMPLETELY - add more info to this message")
    for result in results:
        if git.PushInfo.ERROR & result.flags:
            raise Exception(f"PUSH FAILED {result.summary}")
