import logging
import os

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


def setup_local_branch(repo: git.Repo, branch_name: str, parent_branch_name: str):
    """
    Ensure we have a local branch named 'branch_name'.
    Pull from upstream ('origin'), or create as a branch from parent_branch_name.
    If there's an upstream one, pull from it to make sure we're up to date.
    Check it out.
    """
    # is there already a branch?
    origin = repo.remotes.origin
    origin.fetch()

    # Check for branches that track remote branches that no longer exist
    stale_refs = origin.stale_refs  # List[RemoteReference]
    stale_branchnames = [ref.remote_head for ref in stale_refs]
    logger.debug(f"STALE REFS = {stale_refs}")

    exists_locally = hasattr(repo.branches, branch_name)
    exists_upstream = (
        hasattr(origin.refs, branch_name) and branch_name not in stale_branchnames
    )

    if exists_locally:
        print("local already exists")
    else:
        # Not locally, maybe upstream
        if exists_upstream:
            # Create locally, based on upstream
            repo.create_head(branch_name, f"origin/{branch_name}")
        else:
            # Nope, need to create from scratch
            print("create from scratch")
            parent_branch = getattr(origin.refs, parent_branch_name)
            repo.create_head(branch_name, parent_branch)
    branch = getattr(repo.heads, branch_name)
    branch.checkout()
    # Make sure local branch is up to date if there's an upstream branch
    if exists_upstream:
        origin.pull(f"{branch_name}:{branch_name}")


def commit_and_push_changes(repo: git.Repo, commit_msg: str):
    """Commit new translation changes to current branch, and push upstream"""
    index = repo.index
    index.commit(commit_msg)
    current_branch = repo.head.reference
    branch_name = current_branch.name

    results = repo.remotes.origin.push(f"{branch_name}:{branch_name}")
    if len(results) == 0:
        raise Exception("PUSH FAILED COMPLETELY - add more info to this message")
    for result in results:
        if git.PushInfo.ERROR & result.flags:
            raise Exception(f"PUSH FAILED {result.summary}")
