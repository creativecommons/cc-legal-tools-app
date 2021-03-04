# Standard library
import os
from argparse import ArgumentParser
from shutil import rmtree

# Third-party
import git
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.management import BaseCommand, CommandError
from django.urls import reverse

# First-party/Local
from licenses.git_utils import commit_and_push_changes, setup_local_branch
from licenses.models import LegalCode, TranslationBranch
from licenses.utils import save_url_as_static_file


def list_open_translation_branches():
    """
    Return list of names of open translation branches
    """
    return list(
        TranslationBranch.objects.filter(complete=False).values_list(
            "branch_name", flat=True
        )
    )


class Command(BaseCommand):
    """
    Command to push the static files in the build directory to a specified
    branch in cc-licenses-data repository

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
                "Translation branch name to pull translations from "
                "and push artifacts to.  Use --list_branches to see "
                "available branch names.  With no option, all active "
                "branches are published."
            ),
        )
        parser.add_argument(
            "-l",
            "--list_branches",
            action="store_true",
            help="A list of active translation branches will be displayed.",
        )
        parser.add_argument(
            "--nopush",
            action="store_true",
            help="Update the local branches, but don't push upstream.",
        )

    def _quiet(self, *args, **kwargs):
        pass

    def run_django_distill(self):
        """Outputs static files into the output dir."""
        if not os.path.isdir(settings.STATIC_ROOT):
            e = "Static source directory does not exist, run collectstatic"
            raise CommandError(e)
        output_dir = self.output_dir
        if os.path.isdir(output_dir):
            rmtree(output_dir)
        os.makedirs(output_dir)

        save_url_as_static_file(output_dir, "/status/", "status/index.html")
        tbranches = TranslationBranch.objects.filter(complete=False)
        for tbranch_id in tbranches.values_list("id", flat=True):
            save_url_as_static_file(
                output_dir,
                f"/status/{tbranch_id}/",
                f"status/{tbranch_id}.html",
            )

        for legalcode in LegalCode.objects.valid():
            save_url_as_static_file(
                output_dir, legalcode.license_url, legalcode.get_license_path()
            )
            save_url_as_static_file(
                output_dir, legalcode.deed_url, legalcode.get_deed_path()
            )
        save_url_as_static_file(
            output_dir, reverse("metadata"), "licenses/metadata.yaml"
        )

    def publish_branch(self, branch: str):
        """Workflow for publishing a single branch"""
        print(f"Publishing branch {branch}")
        with git.Repo(settings.TRANSLATION_REPOSITORY_DIRECTORY) as repo:
            setup_local_branch(repo, branch)
            self.run_django_distill()
            if repo.is_dirty(untracked_files=True):
                # Add any changes and new files

                commit_and_push_changes(
                    repo,
                    "Updated built HTML files",
                    self.relpath,
                    push=self.push,
                )
                if repo.is_dirty(untracked_files=True):
                    raise Exception(
                        "Something went wrong, the repo is still dirty"
                    )
            else:
                print(f"\n{branch} build dir is up to date.\n")

    def publish_all(self):
        """Workflow for checking branches and updating their build dir"""
        branch_list = list_open_translation_branches()
        print(
            f"\n\nChecking and updating build dirs for {len(branch_list)}"
            " translation branches\n\n"
        )
        for b in branch_list:
            self.publish_branch(b)

    def handle(self, *args, **options):
        self.options = options
        self.output_dir = os.path.abspath(settings.DISTILL_DIR)
        git_dir = os.path.abspath(settings.TRANSLATION_REPOSITORY_DIRECTORY)

        if not self.output_dir.startswith(git_dir):
            raise ImproperlyConfigured(
                f"In Django settings, DISTILL_DIR must be inside "
                f"TRANSLATION_REPOSITORY_DIRECTORY, "
                f"but DISTILL_DIR={self.output_dir} is outside "
                f"TRANSLATION_REPOSITORY_DIRECTORY={git_dir}."
            )

        self.relpath = os.path.relpath(self.output_dir, git_dir)
        self.push = not options["nopush"]

        if options.get("list_branches"):
            branches = list_open_translation_branches()
            print("\n\nWhich branch are we publishing to?\n")
            for b in branches:
                print(b)
        elif options.get("branch_name"):
            self.publish_branch(options["branch_name"])
        else:
            self.publish_all()
