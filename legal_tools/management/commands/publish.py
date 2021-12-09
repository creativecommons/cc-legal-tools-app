# Standard library
import logging
import os
import re
import socket
from argparse import ArgumentParser
from shutil import copyfile, rmtree

# Third-party
import git
from django.conf import settings
from django.core.management import BaseCommand, CommandError
from django.http.response import Http404
from django.urls import reverse

# First-party/Local
from i18n import DEFAULT_CSV_FILE
from i18n.utils import write_transstats_csv
from legal_tools.git_utils import commit_and_push_changes, setup_local_branch
from legal_tools.models import LegalCode, TranslationBranch
from legal_tools.utils import (
    init_utils_logger,
    relative_symlink,
    save_bytes_to_file,
    save_redirect,
    save_url_as_static_file,
)

LOG = logging.getLogger(__name__)
LOG_LEVELS = {
    0: logging.ERROR,
    1: logging.WARNING,
    2: logging.INFO,
    3: logging.DEBUG,
}
# RE: .nojekyll:
# https://github.blog/2009-12-29-bypassing-jekyll-on-github-pages/
# RE: CNAME
# https://docs.github.com/en/pages/configuring-a-custom-domain-for-your-github-pages-site
DOCS_IGNORE = [".nojekyll", "CNAME"]


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
    branch in cc-legal-tools-data repository

    Arguments:
        branch_name - Branch name in cc-legal-tools-data to pull translations
                      from and publish artifacts too.
        list_branches - A list of active branches in cc-legal-tools-data will
                        be displayed

    If no arguments are supplied all cc-legal-tools-data branches are checked
    and then updated.
    """

    def add_arguments(self, parser: ArgumentParser):
        parser.add_argument(
            "-l",
            "--list_branches",
            action="store_true",
            help="A list of active translation branches will be displayed.",
        )

        gitargs = parser.add_mutually_exclusive_group()
        gitargs.add_argument(
            "-b",
            "--branch_name",
            help="Translation branch name to pull translations from and push"
            " artifacts to. Use --list_branches to see available branch names."
            " With no option, all active branches are published.",
        )
        gitargs.add_argument(
            "--nogit",
            action="store_true",
            help="Update the local files without any attempt to manage them in"
            " git (implies --nopush)",
        )

        parser.add_argument(
            "--nopush",
            action="store_true",
            help="Update the local branches, but don't push upstream.",
        )

    def _quiet(self, *args, **kwargs):
        pass

    def run_clean_output_dir(self):
        output_dir = self.output_dir
        output_dir_items = [
            os.path.join(output_dir, item)
            for item in os.listdir(output_dir)
            if item not in DOCS_IGNORE
        ]
        for item in output_dir_items:
            if os.path.isdir(item):
                rmtree(item)
            else:
                os.remove(item)

    def run_create_robots_txt(self):
        """Create robots.txt to discourage indexing."""
        robots = "User-agent: *\nDisallow: /\n".encode("utf-8")
        save_bytes_to_file(robots, os.path.join(self.output_dir, "robots.txt"))

    def run_django_distill(self):
        """Outputs static files into the output dir."""
        if not os.path.isdir(settings.STATIC_ROOT):
            e = "Static source directory does not exist, run collectstatic"
            raise CommandError(e)
        hostname = socket.gethostname()
        output_dir = self.output_dir

        LOG.debug(f"{hostname}:{output_dir}")
        save_url_as_static_file(
            output_dir,
            url="/dev/status/",
            relpath="status/index.html",
        )
        tbranches = TranslationBranch.objects.filter(complete=False)
        for tbranch_id in tbranches.values_list("id", flat=True):
            relpath = f"status/{tbranch_id}.html"
            LOG.debug(f"    {relpath}")
            save_url_as_static_file(
                output_dir,
                url=f"/status/{tbranch_id}/",
                relpath=relpath,
            )

        legal_codes = LegalCode.objects.validgroups()
        redirect_pairs = []
        for group in legal_codes.keys():
            LOG.info(f"Publishing {group}")
            LOG.debug(f"{hostname}:{output_dir}")
            for legal_code in legal_codes[group]:
                # deed
                try:
                    (
                        relpath,
                        symlinks,
                        redirects_data,
                    ) = legal_code.get_publish_files("deed")
                    save_url_as_static_file(
                        output_dir,
                        url=legal_code.deed_url,
                        relpath=relpath,
                    )
                    for symlink in symlinks:
                        relative_symlink(output_dir, relpath, symlink)
                    for redirect_data in redirects_data:
                        save_redirect(output_dir, redirect_data)
                    redirect_pairs += legal_code.get_redirect_pairs("deed")
                except Http404 as e:
                    if "invalid language" not in str(e):
                        raise
                # legalcode
                (
                    relpath,
                    symlinks,
                    redirects_data,
                ) = legal_code.get_publish_files("legalcode")
                if relpath:
                    # Deed-only tools will not return a legal code relpath
                    save_url_as_static_file(
                        output_dir,
                        url=legal_code.legal_code_url,
                        relpath=relpath,
                    )
                for symlink in symlinks:
                    relative_symlink(output_dir, relpath, symlink)
                for redirect_data in redirects_data:
                    save_redirect(output_dir, redirect_data)
                redirect_pairs += legal_code.get_redirect_pairs("legalcode")

        redirect_pairs.sort(key=lambda x: x[0], reverse=True)
        for i, pair in enumerate(redirect_pairs):
            redirect_pairs[i][0] = re.escape(pair[0])
        widths = [max(map(len, map(str, col))) for col in zip(*redirect_pairs)]
        redirects_include = [
            "# DO NOT EDIT MANUALLY",
            "# This file was generated by the publish command.",
            "# https://github.com/creativecommons/cc-legal-tools-app",
        ]
        for regex, replacement in redirect_pairs:
            regex = f"^/{regex.ljust(widths[0])}"
            replacement = replacement.ljust(widths[1])
            redirects_include.append(
                f"rewrite {regex} {replacement} permanent;"
            )
        redirects_include.append("# vim: set ft=nginx")
        redirects_include.append("")
        redirects_include = "\n".join(redirects_include).encode("utf-8")
        redirects_filename = os.path.join(
            self.config_dir, "nginx_language_redirects"
        )
        save_bytes_to_file(redirects_include, redirects_filename)

        LOG.debug(f"{hostname}:{output_dir}")
        save_url_as_static_file(
            output_dir,
            url=reverse("metadata"),
            relpath="licenses/metadata.yaml",
        )

    def run_copy_tools_rdfs(self):
        hostname = socket.gethostname()
        legacy_dir = self.legacy_dir
        output_dir = self.output_dir
        tools_rdf_dir = os.path.join(legacy_dir, "rdf-licenses")
        tools_rdfs = [
            rdf_file
            for rdf_file in os.listdir(tools_rdf_dir)
            if os.path.isfile(os.path.join(tools_rdf_dir, rdf_file))
        ]
        tools_rdfs.sort()
        LOG.info("Copying legal code RDFs")
        LOG.debug(f"{hostname}:{output_dir}")
        for rdf in tools_rdfs:
            if rdf.endswith(".rdf"):
                name = rdf[:-4]
            else:
                continue
            relative_name = os.path.join(*name.split("_"), "rdf")
            dest_file = os.path.join(output_dir, relative_name)
            os.makedirs(os.path.dirname(dest_file), exist_ok=True)
            copyfile(os.path.join(tools_rdf_dir, rdf), dest_file)
            LOG.debug(f"    {relative_name}")

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
        LOG.info("Copying RDF information and metadata")
        LOG.debug(f"{hostname}:{output_dir}")
        for meta_file in meta_files:
            dest_relative = os.path.join("rdf", meta_file)
            dest_full = os.path.join(output_dir, dest_relative)
            LOG.debug(f"    {dest_relative}")
            copyfile(os.path.join(meta_rdf_dir, meta_file), dest_full)
            if meta_file == "index.rdf":
                os.makedirs(
                    os.path.join(output_dir, "licenses"), exist_ok=True
                )
                dir_fd = os.open(output_dir, os.O_RDONLY)
                symlink = os.path.join("licenses", meta_file)
                try:
                    os.symlink(f"../{dest_relative}", symlink, dir_fd=dir_fd)
                    LOG.debug(f"   ^{symlink}")
                finally:
                    os.close(dir_fd)
            elif meta_file == "ns.html":
                dir_fd = os.open(output_dir, os.O_RDONLY)
                symlink = meta_file
                try:
                    os.symlink(dest_relative, symlink, dir_fd=dir_fd)
                    LOG.debug(f"   ^{symlink}")
                finally:
                    os.close(dir_fd)
            elif meta_file == "schema.rdf":
                dir_fd = os.open(output_dir, os.O_RDONLY)
                symlink = meta_file
                try:
                    os.symlink(dest_relative, symlink, dir_fd=dir_fd)
                    LOG.debug(f"   ^{symlink}")
                finally:
                    os.close(dir_fd)

    def run_copy_legal_code_plaintext(self):
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
        LOG.info("Copying plaintext legal code")
        LOG.debug(f"{hostname}:{output_dir}")
        for text in plaintext_files:
            if text.startswith("by"):
                context = "licenses"
            else:
                context = "publicdomain"
            name = text[:-4]
            relative_name = os.path.join(
                context,
                *name.split("_"),
                "legalcode.txt",
            )
            dest_file = os.path.join(output_dir, relative_name)
            os.makedirs(os.path.dirname(dest_file), exist_ok=True)
            copyfile(os.path.join(plaintext_dir, text), dest_file)
            LOG.debug(f"    {relative_name}")

    def run_write_transstats_csv(self):
        LOG.info("Generating translations statistics CSV")
        write_transstats_csv(DEFAULT_CSV_FILE)

    def distill_and_copy(self):
        self.run_clean_output_dir()
        self.run_create_robots_txt()
        self.run_django_distill()
        self.run_copy_tools_rdfs()
        self.run_copy_meta_rdfs()
        self.run_copy_legal_code_plaintext()
        self.run_write_transstats_csv()

    def publish_branch(self, branch: str):
        """Workflow for publishing a single branch"""
        LOG.debug(f"Publishing branch {branch}")
        with git.Repo(settings.DATA_REPOSITORY_DIR) as repo:
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
                    raise git.exc.RepositoryDirtyError(
                        settings.DATA_REPOSITORY_DIR,
                        "Repository is dirty. We cannot continue.",
                    )
            else:
                LOG.debug(f"{branch} build dir is up to date.")

    def publish_all(self):
        """Workflow for checking branches and updating their build dir"""
        branches = list_open_translation_branches()
        LOG.info(
            f"Checking and updating build dirs for {len(branches)}"
            " translation branches."
        )
        for branch in branches:
            self.publish_branch(branch)

    def handle(self, *args, **options):
        LOG.setLevel(LOG_LEVELS[int(options["verbosity"])])
        init_utils_logger(LOG)
        self.options = options

        if options.get("branch_name", None) == "main":
            raise CommandError(
                "Publishing to the main branch is prohibited. Changes to the"
                " main branch should be done via a pull request."
            )

        self.output_dir = os.path.abspath(settings.DISTILL_DIR)
        self.config_dir = os.path.abspath(
            os.path.join(self.output_dir, "..", "config")
        )
        self.legacy_dir = os.path.abspath(settings.LEGACY_DIR)
        git_dir = os.path.abspath(settings.DATA_REPOSITORY_DIR)
        if not self.output_dir.startswith(git_dir):
            raise CommandError(
                "In Django settings, DISTILL_DIR must be inside"
                f" DATA_REPOSITORY_DIR, but DISTILL_DIR={self.output_dir} is"
                f" outside DATA_REPOSITORY_DIR={git_dir}."
            )

        self.relpath = os.path.relpath(self.output_dir, git_dir)
        self.push = not options["nopush"]

        if options.get("list_branches"):
            branches = list_open_translation_branches()
            LOG.debug("Which branch are we publishing to?")
            for branch in branches:
                LOG.debug(branch)
        elif options.get("nogit"):
            self.distill_and_copy()
        elif options.get("branch_name"):
            self.publish_branch(options["branch_name"])
        else:
            self.publish_all()
