import os
import subprocess
from argparse import ArgumentParser

from django.core.management import BaseCommand

from cc_licenses.settings.base import TRANSLATION_REPOSITORY_DIRECTORY


def run_django_distill():
    """Outputs static files into the specified directory determined by settings.base.DISTILL_DIR
    """
    my_env = os.environ.copy()
    cmd = ["python", "manage.py", "distill-local", "--quiet", "--force"]
    return subprocess.run(cmd, check=True, text=True, input="YES", env=my_env,)


def git_branch_status(branch: str):
    """Checks if there is a build to commit using git status

    Returns True or False
    """
    subprocess.run(
        ["git", "checkout", f"{branch}"], cwd=TRANSLATION_REPOSITORY_DIRECTORY
    )
    status = (
        subprocess.check_output(["git", "status"], cwd=TRANSLATION_REPOSITORY_DIRECTORY)
        .decode()
        .split("\n")
    )
    if "nothing to commit, working tree clean" in status:
        return False
    return True


def git_on_branch_and_pull(branch: str):
    """Commands to checkout and pull from a branch"""
    subprocess.run(
        ["git", "checkout", f"{branch}"], cwd=TRANSLATION_REPOSITORY_DIRECTORY
    )
    return subprocess.run(
        ["git", "pull", "origin", f"{branch}"], cwd=TRANSLATION_REPOSITORY_DIRECTORY
    )


def git_commit_and_push(branch: str):
    """Command to git checkout, commit, and push branch"""
    subprocess.run(["git", "add", "build/"], cwd=TRANSLATION_REPOSITORY_DIRECTORY)
    subprocess.run(
        ["git", "checkout", f"{branch}"], cwd=TRANSLATION_REPOSITORY_DIRECTORY
    )
    subprocess.run(
        ["git", "commit", "-m", f"{branch}"], cwd=TRANSLATION_REPOSITORY_DIRECTORY
    )
    return subprocess.run(
        ["git", "push", "origin" f"{branch}"], cwd=TRANSLATION_REPOSITORY_DIRECTORY
    )


def pull_translations_branches():
    """Git pulls branches in cc-licenses-data to update local git registry"""
    subprocess.run(["git", "checkout", "develop"], cwd=TRANSLATION_REPOSITORY_DIRECTORY)
    return subprocess.run(["git", "pull"], cwd=TRANSLATION_REPOSITORY_DIRECTORY)


def list_open_branches():
    """List of open branches in cc-licenses-data repo
    """
    pull_translations_branches()
    branches = (
        subprocess.check_output(
            ["git", "branch", "--list"], cwd=TRANSLATION_REPOSITORY_DIRECTORY
        )
        .decode()
        .split("\n")
    )
    print("\n\nWhich branch are we publishing to?\n")
    for b in branches:
        return print(b)


def publish_branch(branch: str):
    """Workflow for publishing a single branch"""
    git_on_branch_and_pull(branch)
    run_django_distill()
    build_to_push = git_branch_status(branch)
    if build_to_push:
        git_commit_and_push(branch)
    else:
        print(f"\n{branch} build dir is up to date.\n")


def publish_all():
    """Workflow for checking branches other than develop and updating their build dir

    Develop is not checked because it serves as the source of truth. It should be
    manually merged into.
    """
    branches = (
        subprocess.check_output(
            ["git", "branch", "--list"], cwd=TRANSLATION_REPOSITORY_DIRECTORY
        )
        .decode()
        .split("\n")
    )
    exclude_develop_list = [b for b in branches if "develop" not in b]
    del exclude_develop_list[-1]
    branch_list = [b.lstrip() for b in exclude_develop_list]
    print(
        f"\n\nChecking and updating build dirs for {len(branch_list)} translation branches"
    )
    for b in branch_list:
        publish_branch(b)


class Command(BaseCommand):
    """Command to push the static files in the build directory to a specified branch
    in cc-licenses-data repository

    Arguments:
        branch_name - Branch name in cc-license-data to pull translations from
                      and publish artifacts too.
        list_branches - A list of active branches in cc-licenses-data will be
                        displayed

    If no arguments are supplied all cc-licenses-data branches are checked and
    then updated.
    """

    def add_arguments(self, parser: ArgumentParser):
        parser.add_argument(
            "-b",
            "--branch_name",
            help=(
                "Branch name in cc-license-data to pull translations from "
                "and push artifacts too. If not specified a list of active "
                "branches in cc-licenses-data will be displayed"
            ),
        )
        parser.add_argument(
            "-l",
            "--list_branches",
            action="store_true",
            help="A list of active branches in cc-licenses-data will be displayed",
        )

    def handle(self, *args, **options):
        if options.get("list_branches"):
            return list_open_branches()
        if options.get("branch_name"):
            return publish_branch(options["branch_name"])
        return publish_all()
