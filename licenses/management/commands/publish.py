import os
import subprocess
from argparse import ArgumentParser
from shutil import rmtree

from django.conf import settings
from django.core.management import BaseCommand, CommandError
from django_distill.distill import urls_to_distill
from django_distill.errors import DistillError
from django_distill.renderer import render_to_dir

from licenses.utils import cleanup_current_branch_output, strip_list_whitespace


def check_if_build_to_push(branch: str):
    """Navigates to a branch and checks the status of the branch

    Returns:
        True if files need to be committed
        False if the working tree is clean
    """
    subprocess.run(
        ["git", "checkout", f"{branch}"], cwd=settings.TRANSLATION_REPOSITORY_DIRECTORY
    )
    status = (
        subprocess.check_output(
            ["git", "status"], cwd=settings.TRANSLATION_REPOSITORY_DIRECTORY
        )
        .decode()
        .splitlines()
    )
    if "nothing to commit, working tree clean" in status:
        return False
    return True


def git_on_branch_and_pull(branch: str):
    """Commands to checkout and pull from a branch"""
    subprocess.run(
        ["git", "checkout", f"{branch}"], cwd=settings.TRANSLATION_REPOSITORY_DIRECTORY
    )
    return subprocess.run(
        ["git", "pull", "origin", f"{branch}"],
        cwd=settings.TRANSLATION_REPOSITORY_DIRECTORY,
    )


def git_commit_and_push(branch: str):
    """Command to git checkout, commit, and push branch"""
    subprocess.run(
        ["git", "add", "build/"], cwd=settings.TRANSLATION_REPOSITORY_DIRECTORY
    )
    subprocess.run(
        ["git", "commit", "-m", f"{branch}"],
        cwd=settings.TRANSLATION_REPOSITORY_DIRECTORY,
    )
    return subprocess.run(
        ["git", "push", "origin", f"{branch}"],
        cwd=settings.TRANSLATION_REPOSITORY_DIRECTORY,
    )


def pull_translations_branches():
    """Git pulls branches in cc-licenses-data to update local git registry"""
    subprocess.run(
        ["git", "checkout", settings.OFFICIAL_GIT_BRANCH],
        cwd=settings.TRANSLATION_REPOSITORY_DIRECTORY,
    )
    return subprocess.run(
        ["git", "pull"], cwd=settings.TRANSLATION_REPOSITORY_DIRECTORY
    )


def list_open_branches():
    """List of open branches in cc-licenses-data repo
    """
    pull_translations_branches()
    branches = (
        subprocess.check_output(
            ["git", "branch", "--list"], cwd=settings.TRANSLATION_REPOSITORY_DIRECTORY
        )
        .decode()
        .splitlines()
    )
    print("\n\nWhich branch are we publishing to?\n")
    for b in branches:
        print(b)


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

    def _quiet(self, *args, **kwargs):
        pass

    def run_django_distill(self):
        """Outputs static files into the specified directory determined by settings.base.DISTILL_DIR
        """
        stdout = self._quiet
        output_dir = getattr(settings, "DISTILL_DIR", None)
        if not os.path.isdir(settings.STATIC_ROOT):
            e = "Static source directory does not exist, run collectstatic"
            raise CommandError(e)
        output_dir = os.path.abspath(os.path.expanduser(output_dir))
        if os.path.isdir(output_dir):
            rmtree(output_dir)
        os.makedirs(output_dir)
        try:
            render_to_dir(output_dir, urls_to_distill, stdout)
        except DistillError as err:
            raise CommandError(str(err)) from err

    def publish_branch(self, branch: str):
        """Workflow for publishing a single branch"""
        git_on_branch_and_pull(branch)
        self.run_django_distill()
        build_to_push = check_if_build_to_push(branch)
        if build_to_push:
            git_commit_and_push(branch)
        else:
            print(f"\n{branch} build dir is up to date.\n")

    def publish_all(self):
        """Workflow for checking branches and updating their build dir
        """
        branches = (
            subprocess.check_output(
                ["git", "branch", "--list"],
                cwd=settings.TRANSLATION_REPOSITORY_DIRECTORY,
            )
            .decode()
            .splitlines()
        )
        branch_list = strip_list_whitespace("left", branches)
        cleaned_branch_list = cleanup_current_branch_output(branch_list)
        print(
            f"\n\nChecking and updating build dirs for {len(branch_list)} translation branches\n\n"
        )
        for b in cleaned_branch_list:
            self.publish_branch(b)

    def handle(self, *args, **options):
        if options.get("list_branches"):
            list_open_branches()
        elif options.get("branch_name"):
            self.publish_branch(options["branch_name"])
        else:
            self.publish_all()
