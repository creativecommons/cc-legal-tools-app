import fnmatch
import os
import subprocess
import tempfile
from argparse import ArgumentParser
from shutil import rmtree

import git
from bs4 import BeautifulSoup
from django.conf import settings
from django.core.management import BaseCommand, CommandError
from django_distill.distill import urls_to_distill
from django_distill.errors import DistillError
from django_distill.renderer import render_to_dir

from licenses.git_utils import commit_and_push_changes, setup_local_branch


def list_open_branches():
    """List of names of open local branches in cc-licenses-data repo
    """
    with git.Repo(settings.TRANSLATION_REPOSITORY_DIRECTORY) as repo:
        branches = [head.name for head in repo.branches]
    print("\n\nWhich branch are we publishing to?\n")
    for b in branches:
        print(b)
    return branches


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

    def output_text_files(self, *args, **kwargs):
        output_dir = getattr(settings, "DISTILL_DIR", None)
        licenses_dir = f"{output_dir}licenses/"
        pattern = "legalcode*"
        for root, dirs, files in os.walk(licenses_dir):
            for filename in fnmatch.filter(files, pattern):
                file_path = os.path.join(root, filename)
                txt_filename = f"{filename}.txt"
                txt_file_path = os.path.join(root, txt_filename)
                with open(file_path, "r") as f:
                    soup = BeautifulSoup(f, "lxml")
                    plain_text_soup = soup.find(id="plain-text-marker")
                    plain_text_html = plain_text_soup.prettify(formatter="html")
                with tempfile.NamedTemporaryFile(mode="w+t") as temp:
                    temp.write(plain_text_html)
                    temp.seek(0)
                    subprocess.run(
                        [
                            "pandoc",
                            "-f",
                            "html",
                            temp.name,
                            "-t",
                            "plain",
                            "-o",
                            txt_file_path,
                        ]
                    )

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
        with git.Repo(settings.TRANSLATION_REPOSITORY_DIRECTORY) as repo:
            setup_local_branch(repo, branch, settings.OFFICIAL_GIT_BRANCH)
            self.run_django_distill()
            self.output_text_files()
            if repo.is_dirty():
                repo.index.add("build")
                commit_and_push_changes(repo, "Updated built HTML files")
            else:
                print(f"\n{branch} build dir is up to date.\n")

    def publish_all(self):
        """Workflow for checking branches and updating their build dir
        """
        branch_list = list_open_branches()
        print(
            f"\n\nChecking and updating build dirs for {len(branch_list)} translation branches\n\n"
        )
        for b in branch_list:
            self.publish_branch(b)

    def handle(self, *args, **options):
        if options.get("list_branches"):
            list_open_branches()
        elif options.get("branch_name"):
            self.publish_branch(options["branch_name"])
        else:
            self.publish_all()
