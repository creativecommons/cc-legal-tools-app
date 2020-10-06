import os

import git
from django.conf import settings


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
    if not hasattr(repo.branches, branch_name):
        # Not locally, maybe upstream
        if hasattr(origin.refs, branch_name):
            repo.create_head(branch_name, f"origin/{branch_name}")
        else:
            # Nope, need to create from scratch
            print("create from scratch")
            parent_branch = getattr(origin.refs, parent_branch_name)
            repo.create_head(branch_name, parent_branch)
    else:
        print("local already exists")
    branch = getattr(repo.heads, branch_name)
    branch.checkout()
    # Make sure local branch is up to date if there's an upstream branch
    if hasattr(origin.refs, branch_name):
        origin.pull(f"{branch_name}:{branch_name}")


def get_ssh_command():
    """Return an ssh command that can be used to write to the repo"""
    keyfile = getattr(settings, "TRANSLATION_REPOSITORY_DEPLOY_KEY", False)
    if keyfile:
        if os.path.exists(keyfile):
            ssh_command = f"ssh -o StrictHostKeyChecking=no -i '{keyfile}'"
        else:
            raise ValueError(
                f"settings.TRANSLATION_REPOSITORY_DEPLOY_KEY is {keyfile}, but that file does not exist or is not readable."
            )
    else:
        raise ValueError(
            "settings.TRANSLATION_REPOSITORY_DEPLOY_KEY must be set to the filename "
            "of a private ssh deploy key for the repo before trying to push"
        )
    return ssh_command


def commit_and_push_changes(repo: git.Repo, commit_msg: str):
    """Commit new translation changes to current branch, and push upstream"""
    index = repo.index
    index.commit(commit_msg)
    current_branch = repo.head.reference
    branch_name = current_branch.name

    # Use custom ssh command to use the deploy key when pushing
    with repo.git.custom_environment(GIT_SSH_COMMAND=get_ssh_command()):
        results = repo.remotes.origin.push(f"{branch_name}:{branch_name}")
    if len(results) == 0:
        raise Exception("PUSH FAILED COMPLETELY - add more info to this message")
    for result in results:
        if git.PushInfo.ERROR & result.flags:
            raise Exception(f"PUSH FAILED {result.summary}")
