# Standard library
import os
import socket
from argparse import ArgumentParser
from shutil import copyfile, rmtree

# Third-party
import git
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.management import BaseCommand, CommandError
from django.urls import reverse

# First-party/Local
from licenses.git_utils import commit_and_push_changes, setup_local_branch
from licenses.models import LegalCode, TranslationBranch
from licenses.utils import relative_symlink, save_url_as_static_file


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
            help="Translation branch name to pull translations from and push"
            " artifacts to. Use --list_branches to see available branch names."
            " With no option, all active branches are published.",
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
        parser.add_argument(
            "--nogit",
            action="store_true",
            help="Update the local files without any attempt to manage them in"
            " git (implies --nopush)",
        )

    def _quiet(self, *args, **kwargs):
        pass

    def run_clean_output_dir(self):
        output_dir = self.output_dir
        output_dir_items = [
            os.path.join(output_dir, item)
            for item in os.listdir(output_dir)
            if item != "CNAME"
        ]
        for item in output_dir_items:
            if os.path.isdir(item):
                rmtree(item)
            else:
                os.remove(item)

    def run_django_distill(self):
        """Outputs static files into the output dir."""
        if not os.path.isdir(settings.STATIC_ROOT):
            e = "Static source directory does not exist, run collectstatic"
            raise CommandError(e)
        hostname = socket.gethostname()
        output_dir = self.output_dir

        self.stdout.write(f"\n{hostname}:{output_dir}")
        save_url_as_static_file(output_dir, "/status/", "status/index.html")
        tbranches = TranslationBranch.objects.filter(complete=False)
        for tbranch_id in tbranches.values_list("id", flat=True):
            save_url_as_static_file(
                output_dir,
                f"/status/{tbranch_id}/",
                f"status/{tbranch_id}.html",
            )

        legalcodes = LegalCode.objects.validgroups()
        for group in legalcodes.keys():
            self.stdout.write(f"\n{hostname}:{output_dir}")
            for legalcode in legalcodes[group]:
                # deed
                filepath, symlinks = legalcode.get_file_and_links("deed")
                save_url_as_static_file(
                    output_dir,
                    legalcode.deed_url,
                    filepath,
                )
                for symlink in symlinks:
                    relative_symlink(output_dir, filepath, symlink)
                # legalcode
                filepath, symlinks = legalcode.get_file_and_links("legalcode")
                save_url_as_static_file(
                    output_dir,
                    legalcode.license_url,
                    filepath,
                )
                for symlink in symlinks:
                    relative_symlink(output_dir, filepath, symlink)

        self.stdout.write(f"\n{hostname}:{output_dir}")
        save_url_as_static_file(
            output_dir, reverse("metadata"), "licenses/metadata.yaml"
        )

    def run_copy_licenses_rdfs(self):
        hostname = socket.gethostname()
        legacy_dir = self.legacy_dir
        output_dir = self.output_dir
        licenses_rdf_dir = os.path.join(legacy_dir, "rdf-licenses")
        licenses_rdfs = [
            rdf_file
            for rdf_file in os.listdir(licenses_rdf_dir)
            if os.path.isfile(os.path.join(licenses_rdf_dir, rdf_file))
        ]
        licenses_rdfs.sort()
        self.stdout.write(f"\n{hostname}:{output_dir}")
        for rdf in licenses_rdfs:
            if rdf.endswith(".rdf"):
                name = rdf[:-4]
            else:
                continue
            relative_name = os.path.join(*name.split("_"), "rdf")
            dest_file = os.path.join(output_dir, relative_name)
            os.makedirs(os.path.dirname(dest_file), exist_ok=True)
            copyfile(os.path.join(licenses_rdf_dir, rdf), dest_file)
            self.stdout.write(f"    {relative_name}")
            if relative_name.endswith("xu/rdf"):
                relative_symlink(output_dir, relative_name, "../rdf")

    def run_copy_meta_rdfs(self):
        hostname = socket.gethostname()
        legacy_dir = self.legacy_dir
        output_dir = self.output_dir
        meta_rdf_dir = os.path.join(legacy_dir, "rdf-meta")
        meta_files = [
            meta_file
            for meta_file in os.listdir(meta_rdf_dir)
            if os.path.isfile(os.path.join(meta_rdf_dir, meta_file))
        ]
        meta_files.sort()
        dest_dir = os.path.join(output_dir, "rdf")
        os.makedirs(dest_dir, exist_ok=True)
        self.stdout.write(f"\n{hostname}:{output_dir}")
        for meta_file in meta_files:
            dest_relative = os.path.join("rdf", meta_file)
            dest_full = os.path.join(output_dir, dest_relative)
            self.stdout.write(f"    {dest_relative}")
            copyfile(os.path.join(meta_rdf_dir, meta_file), dest_full)
            if meta_file == "index.rdf":
                os.makedirs(
                    os.path.join(output_dir, "licenses"), exist_ok=True
                )
                dir_fd = os.open(output_dir, os.O_RDONLY)
                symlink = os.path.join("licenses", meta_file)
                try:
                    os.symlink(f"../{dest_relative}", symlink, dir_fd=dir_fd)
                    self.stdout.write(f"   ^{symlink}")
                finally:
                    os.close(dir_fd)
            elif meta_file == "ns.html":
                dir_fd = os.open(output_dir, os.O_RDONLY)
                symlink = meta_file
                try:
                    os.symlink(dest_relative, symlink, dir_fd=dir_fd)
                    self.stdout.write(f"   ^{symlink}")
                finally:
                    os.close(dir_fd)
            elif meta_file == "schema.rdf":
                dir_fd = os.open(output_dir, os.O_RDONLY)
                symlink = meta_file
                try:
                    os.symlink(dest_relative, symlink, dir_fd=dir_fd)
                    self.stdout.write(f"   ^{symlink}")
                finally:
                    os.close(dir_fd)

    def run_copy_legalcode_plaintext(self):
        hostname = socket.gethostname()
        legacy_dir = self.legacy_dir
        output_dir = self.output_dir
        plaintext_dir = os.path.join(legacy_dir, "legalcode")
        plaintext_files = [
            text_file
            for text_file in os.listdir(plaintext_dir)
            if (
                os.path.isfile(os.path.join(plaintext_dir, text_file))
                and text_file.endswith(".txt")
            )
        ]
        self.stdout.write(f"\n{hostname}:{output_dir}")
        for text in plaintext_files:
            if text.startswith("by"):
                context = "licenses"
            else:
                context = "publicdomain"
            name = text[:-4]
            if "3.0" in text:
                name = f"{name}_xu"
            relative_name = os.path.join(
                context,
                *name.split("_"),
                "legalcode.txt",
            )
            dest_file = os.path.join(output_dir, relative_name)
            os.makedirs(os.path.dirname(dest_file), exist_ok=True)
            copyfile(os.path.join(plaintext_dir, text), dest_file)
            self.stdout.write(f"    {relative_name}")
            if relative_name.endswith("xu/legalcode.txt"):
                relative_symlink(output_dir, relative_name, "../legalcode.txt")

    def distill_and_copy(self):
        self.run_clean_output_dir()
        self.run_django_distill()
        self.run_copy_licenses_rdfs()
        self.run_copy_meta_rdfs()
        self.run_copy_legalcode_plaintext()

    def publish_branch(self, branch: str):
        """Workflow for publishing a single branch"""
        self.stdout.write(f"Publishing branch {branch}")
        with git.Repo(settings.TRANSLATION_REPOSITORY_DIRECTORY) as repo:
            setup_local_branch(repo, branch)
            self.distill_and_copy()
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
                self.stdout.write(f"\n{branch} build dir is up to date.\n")

    def publish_all(self):
        """Workflow for checking branches and updating their build dir"""
        branches = list_open_translation_branches()
        self.stdout.write(
            f"\n\nChecking and updating build dirs for {len(branches)}"
            " translation branches\n\n"
        )
        for branch in branches:
            self.publish_branch(branch)

    def handle(self, *args, **options):
        self.options = options
        self.output_dir = os.path.abspath(settings.DISTILL_DIR)
        self.legacy_dir = os.path.abspath(settings.LEGACY_DIR)
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
            self.stdout.write("\n\nWhich branch are we publishing to?\n")
            for branch in branches:
                self.stdout.write(branch)
        elif options.get("nogit"):
            self.distill_and_copy()
        elif options.get("branch_name"):
            self.publish_branch(options["branch_name"])
        else:
            self.publish_all()
