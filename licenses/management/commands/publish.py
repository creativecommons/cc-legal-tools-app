import os
from argparse import ArgumentParser
from shutil import rmtree

import git
from django.conf import settings
from django.core.management import BaseCommand, CommandError
from django.urls import reverse

from licenses.git_utils import commit_and_push_changes, kill_branch, setup_local_branch
from licenses.models import LegalCode, TranslationBranch
from licenses.utils import save_url_as_static_file


def list_open_branches():
    """List of names of open local branches in cc-licenses-data repo"""
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
        parser.add_argument(
            "--nogit",
            action="store_true",
            help="Don't do anything with git, just build the pages in the output directory and exit.",
        )
        parser.add_argument(
            "--output_dir",
            help=(
                f'Put output here instead of {getattr(settings, "DISTILL_DIR", None)}. '
                f"(Warning: will delete whatever is there first.)"
            ),
            default=getattr(settings, "DISTILL_DIR", None),
        )

    def _quiet(self, *args, **kwargs):
        pass

    def run_django_distill(self):
        """Outputs static files into the specified directory determined by settings.base.DISTILL_DIR"""
        output_dir = getattr(settings, "DISTILL_DIR", None)
        if not os.path.isdir(settings.STATIC_ROOT):
            e = "Static source directory does not exist, run collectstatic"
            raise CommandError(e)
        output_dir = os.path.abspath(os.path.expanduser(output_dir))
        # print(f"output_dir={output_dir}. Will delete, then generate HTML files there.")
        if os.path.isdir(output_dir):
            rmtree(output_dir)
        os.makedirs(output_dir)

        for legalcode in LegalCode.objects.valid():
            # print(str(legalcode))
            # e.g. URL https://creativecommons.org/licenses/by/3.0/ca/legalcode.en
            # NOT https://creativecommons.org/licenses/by/3.0/ca
            # NOT https://creativecommons.org/licenses/by/3.0/ca/
            # NOT https://creativecommons.org/licenses/by/3.0/ca/legalcode.en-gb
            save_url_as_static_file(output_dir, legalcode.license_url)
            save_url_as_static_file(output_dir, legalcode.deed_url)
        save_url_as_static_file(output_dir, reverse("metadata"))
        save_url_as_static_file(output_dir, "/status/")
        for tbranch in TranslationBranch.objects.filter(complete=False).only("id"):
            save_url_as_static_file(output_dir, f"/status/{tbranch.id}/")

    def publish_branch(self, branch: str):
        """Workflow for publishing a single branch"""
        print(f"Publishing branch {branch}")
        with git.Repo(settings.TRANSLATION_REPOSITORY_DIRECTORY) as repo:
            if self.use_git:
                setup_local_branch(repo, branch, settings.OFFICIAL_GIT_BRANCH)
            self.run_django_distill()
            if self.use_git:
                if repo.is_dirty():
                    # Add any changes and new files under 'build'
                    repo.index.add(["build"])
                    commit_and_push_changes(repo, "Updated built HTML files")
                    if repo.is_dirty():
                        raise Exception("Something went wrong, the repo is still dirty")
                else:
                    print(f"\n{branch} build dir is up to date.\n")
                # Don't need local branch anymore
                kill_branch(repo, branch)

    def publish_all(self):
        """Workflow for checking branches and updating their build dir"""
        branch_list = list_open_branches()
        print(
            f"\n\nChecking and updating build dirs for {len(branch_list)} translation branches\n\n"
        )
        for b in branch_list:
            self.publish_branch(b)

    def handle(self, *args, **options):
        self.options = options
        self.output_dir = options["output_dir"]
        self.use_git = True
        if options["nogit"]:
            self.use_git = False
            self.publish_branch(None)
        elif options.get("list_branches"):
            list_open_branches()
        elif options.get("branch_name"):
            self.publish_branch(options["branch_name"])
        else:
            self.publish_all()
