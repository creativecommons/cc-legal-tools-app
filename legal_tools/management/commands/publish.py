# Standard library
import logging
import os
import socket
from argparse import ArgumentParser
from multiprocessing import Pool
from shutil import copyfile, rmtree

# Third-party
import git
from django.conf import settings
from django.core.management import BaseCommand, CommandError, call_command
from django.urls import reverse

# First-party/Local
from i18n import DEFAULT_CSV_FILE
from i18n.utils import write_transstats_csv
from legal_tools.git_utils import commit_and_push_changes, setup_local_branch
from legal_tools.models import LegalCode, TranslationBranch, build_path
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
# .nojekyll:
# https://github.blog/2009-12-29-bypassing-jekyll-on-github-pages/
# CNAME
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


def wrap_relative_symlink(output_dir, relpath, symlink):
    try:
        relative_symlink(output_dir, relpath, symlink)
    except FileExistsError as e:
        raise CommandError(f"[Errno {e.errno}] {e.strerror}: {relpath}")


def save_list(output_dir, category, language_code):
    # Function is at top level of module so that it can be pickled by
    # multiprocessing.
    relpath = f"{category}/list.{language_code}.html"
    save_url_as_static_file(
        output_dir,
        url=reverse(
            "view_list_language_specified",
            kwargs={
                "category": category,
                "language_code": language_code,
            },
        ),
        relpath=relpath,
    )


def save_deed(output_dir, tool, language_code):
    # Function is at top level of module so that it can be pickled by
    # multiprocessing.
    relpath, symlinks = tool.get_publish_files(language_code)
    save_url_as_static_file(
        output_dir,
        url=build_path(tool.base_url, "deed", language_code),
        relpath=relpath,
    )
    for symlink in symlinks:
        wrap_relative_symlink(output_dir, relpath, symlink)
    return tool.get_redirect_pairs(language_code)


def save_legal_code(output_dir, legal_code):
    # Function is at top level of module so that it can be pickled by
    # multiprocessing.
    (
        relpath,
        symlinks,
        redirects_data,
    ) = legal_code.get_publish_files()
    if relpath:
        # Deed-only tools will not return a legal code relpath
        save_url_as_static_file(
            output_dir,
            url=legal_code.legal_code_url,
            relpath=relpath,
        )
    for symlink in symlinks:
        wrap_relative_symlink(output_dir, relpath, symlink)
    for redirect_data in redirects_data:
        save_redirect(output_dir, redirect_data)
    return legal_code.get_redirect_pairs()

def save_rdf(output_dir, tool):
    # Function is at top level of module so that it can be pickled by
    # multiprocessing.
    relpath = os.path.join(tool._get_save_path(), "rdf")
    save_url_as_static_file(
        output_dir,
        url=build_path(tool.base_url, "rdf", None),
        relpath=relpath,
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

    def purge_output_dir(self):
        output_dir = self.output_dir
        LOG.info(f"Purging output_dir: {output_dir}")
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

    def call_collectstatic(self):
        LOG.info("Collecting static files")
        call_command("collectstatic", interactive=False)

    def write_robots_txt(self):
        """Create robots.txt to discourage indexing."""
        LOG.info("Writing robots.txt")
        robots = "User-agent: *\nDisallow: /\n".encode("utf-8")
        save_bytes_to_file(robots, os.path.join(self.output_dir, "robots.txt"))

    def copy_static_wp_content_files(self):
        hostname = socket.gethostname()
        output_dir = self.output_dir
        LOG.info("Copying WordPress content files")
        LOG.debug(f"{hostname}:{output_dir}")
        path = "wp-content/themes/creativecommons-base/assets/img"
        source = os.path.join(
            settings.PROJECT_ROOT,
            "cc_legal_tools",
            "static",
            path,
        )
        destination = os.path.join(output_dir, path)
        os.makedirs(destination, exist_ok=True)
        for file_name in os.listdir(source):
            copyfile(
                os.path.join(source, file_name),
                os.path.join(destination, file_name),
            )

    def copy_static_cc_legal_tools_files(self):
        hostname = socket.gethostname()
        output_dir = self.output_dir
        LOG.info("Copying static cc-legal-tools files")
        LOG.debug(f"{hostname}:{output_dir}")
        path = "cc-legal-tools"
        source = os.path.join(
            settings.PROJECT_ROOT,
            "cc_legal_tools",
            "static",
            path,
        )
        destination = os.path.join(output_dir, path)
        os.makedirs(destination, exist_ok=True)
        for file_name in os.listdir(source):
            copyfile(
                os.path.join(source, file_name),
                os.path.join(destination, file_name),
            )

    def copy_tools_rdfs(self):
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
        LOG.debug(f"{hostname}:{output_dir}")
        LOG.info("Copying legal code RDFs")
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

    def copy_meta_rdfs(self):
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
        LOG.debug(f"{hostname}:{output_dir}")
        LOG.info("Copying RDF information and metadata")
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

    def copy_legal_code_plaintext(self):
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

    def write_dev_index(self):
        hostname = socket.gethostname()
        output_dir = self.output_dir

        LOG.debug(f"{hostname}:{output_dir}")
        LOG.info("Writing dev index")
        save_url_as_static_file(
            output_dir,
            url=reverse("dev_index"),
            relpath="index.html",
        )

    def write_lists(self):
        hostname = socket.gethostname()
        output_dir = self.output_dir

        LOG.debug(f"{hostname}:{output_dir}")
        LOG.info("Writing lists")

        arguments = []
        for category in ["licenses", "publicdomain"]:
            for language_code in settings.LANGUAGES_MOSTLY_TRANSLATED:
                arguments.append((output_dir, category, language_code))
        self.pool.starmap(save_list, arguments)

        for category in ["licenses", "publicdomain"]:
            relpath = f"{category}/list.{settings.LANGUAGE_CODE}.html"
            symlink = "list.html"
            wrap_relative_symlink(output_dir, relpath, symlink)

    def write_legal_tools(self):
        hostname = socket.gethostname()
        output_dir = self.output_dir
        legal_codes = LegalCode.objects.validgroups()
        redirect_pairs_data = []
        for group in legal_codes.keys():
            tools = set()
            LOG.debug(f"{hostname}:{output_dir}")
            LOG.info(f"Writing {group}")
            legal_code_arguments = []
            deed_arguments = []
            rdf_arguments = []
            for legal_code in legal_codes[group]:
                tools.add(legal_code.tool)
                legal_code_arguments.append((output_dir, legal_code))
            for tool in tools:
                for language_code in settings.LANGUAGES_MOSTLY_TRANSLATED:
                    deed_arguments.append((output_dir, tool, language_code))
                rdf_arguments.append((output_dir, tool))

            redirect_pairs_data += self.pool.starmap(save_deed, deed_arguments)
            redirect_pairs_data += self.pool.starmap(
                  save_legal_code, legal_code_arguments
             )
            self.pool.starmap(save_rdf, rdf_arguments)


        redirect_pairs = []
        for pair_list in redirect_pairs_data:
            redirect_pairs += pair_list
        del redirect_pairs_data
        widths = [max(map(len, map(str, col))) for col in zip(*redirect_pairs)]
        redirect_lines = []
        for pair in redirect_pairs:
            pcre_match = f'"{pair[0]}"'
            pad = widths[0] + 2
            redirect_lines.append(
                f'RedirectMatch  301  {pcre_match.ljust(pad)}  "{pair[1]}"'
            )
        del redirect_pairs
        redirect_lines.sort(reverse=True)
        redirect_lines.sort(reverse=True)
        include_lines = [
            "# DO NOT EDIT MANUALLY",
            "#",
            "# This file was generated by the publish command.",
            "# https://github.com/creativecommons/cc-legal-tools-app",
            "#",
            "# It should be included from within an Apache2 httpd site config",
            "#",
            "# https://httpd.apache.org/docs/2.4/mod/mod_alias.html",
            "# https://httpd.apache.org/docs/2.4/mod/mod_rewrite.html",
            "",
            "########################################",
            "# Step 1: Redirect mixed/uppercase to lowercase",
            "#",
            "# Must be set within virtual host context:",
            "#     RewriteMap lowercase int:tolower",
            "RewriteCond $1 [A-Z]",
            "RewriteRule ^/?(.*)$ /${lowercase:$1} [R=301,L]",
            "",
            "########################################",
            "#Step 2: Redirect alternate language codes to supported Django"
            " language codes",
            "",
        ]
        include_lines += redirect_lines
        del redirect_lines
        include_lines.append("# vim: ft=apache ts=4 sw=4 sts=4 sr noet")
        include_lines.append("")
        include_lines = "\n".join(include_lines).encode("utf-8")
        include_filename = os.path.join(self.config_dir, "language-redirects")
        save_bytes_to_file(include_lines, include_filename)

    def write_translation_branch_statuses(self):
        hostname = socket.gethostname()
        output_dir = self.output_dir

        LOG.debug(f"{hostname}:{output_dir}")

        tbranches = TranslationBranch.objects.filter(complete=False)
        for tbranch_id in tbranches.values_list("id", flat=True):
            LOG.info(f"Writing Translation branch status: {tbranch_id}")
            relpath = f"dev/{tbranch_id}.html"
            LOG.debug(f"    {relpath}")
            save_url_as_static_file(
                output_dir,
                url=f"/dev/{tbranch_id}/",
                relpath=relpath,
            )

    def run_write_transstats_csv(self):
        LOG.info("Generating translations statistics CSV")
        write_transstats_csv(DEFAULT_CSV_FILE)

    def write_metadata_yaml(self):
        hostname = socket.gethostname()
        output_dir = self.output_dir

        LOG.debug(f"{hostname}:{output_dir}")
        LOG.info("Writing metadata.yaml")

        save_url_as_static_file(
            output_dir,
            url=reverse("metadata"),
            relpath="licenses/metadata.yaml",
        )

    def distill_and_copy(self):
        self.purge_output_dir()
        self.call_collectstatic()
        self.write_robots_txt()
        self.copy_static_wp_content_files()
        self.copy_static_cc_legal_tools_files()
        self.copy_tools_rdfs()
        self.copy_meta_rdfs()
        self.copy_legal_code_plaintext()
        self.write_dev_index()
        self.write_lists()
        self.write_legal_tools()
        # self.run_write_transstats_csv()
        # self.write_metadata_yaml()

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
        self.pool = Pool()

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
