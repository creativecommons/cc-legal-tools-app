# Standard library
import logging
import os
import socket
from argparse import SUPPRESS, ArgumentParser
from copy import copy
from multiprocessing import Pool
from pathlib import Path
from pprint import pprint
from shutil import copyfile, copytree, rmtree

# Third-party
import git
from django.conf import settings
from django.core.management import BaseCommand, CommandError, call_command
from django.urls import reverse

# First-party/Local
from i18n import DEFAULT_CSV_FILE
from i18n.utils import (
    get_default_language_for_jurisdiction_deed_ux,
    write_transstats_csv,
)
from legal_tools.git_utils import commit_and_push_changes, setup_local_branch
from legal_tools.models import LegalCode, TranslationBranch, build_path
from legal_tools.utils import (
    init_utils_logger,
    relative_symlink,
    save_bytes_to_file,
    save_redirect,
    save_url_as_static_file,
    update_title,
)
from legal_tools.views import render_redirect

ALL_TRANSLATION_BRANCHES = "###all###"
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


def save_deed(output_dir, tool, language_code, opt_apache_only):
    # Function is at top level of module so that it can be pickled by
    # multiprocessing.
    if not opt_apache_only:
        relpath, symlinks = tool.get_publish_files(language_code)
        save_url_as_static_file(
            output_dir,
            url=build_path(tool.base_url, "deed", language_code),
            relpath=relpath,
        )
        for symlink in symlinks:
            wrap_relative_symlink(output_dir, relpath, symlink)
    return tool.get_redirect_pairs(language_code)


def save_legal_code(output_dir, legal_code, opt_apache_only):
    # Function is at top level of module so that it can be pickled by
    # multiprocessing.
    if not opt_apache_only:
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
            redirect_content = render_redirect(
                title=redirect_data["title"],
                destination=redirect_data["destination"],
                language_code=redirect_data["language_code"],
            )
            save_redirect(
                output_dir, redirect_data["redirect_file"], redirect_content
            )
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
    Publish static files to the data repository's docs directory (by default
    manage local changes in git and don't push changes to origin).
    """

    def add_arguments(self, parser: ArgumentParser):
        # Python defaults to lowercase starting character for the first
        # character of help text, but Djano appears to use uppercase and so
        # shall we
        parser.description = self.__doc__
        parser._optionals.title = "Django optional arguments"

        parser.set_defaults(action="dev")
        action_group = parser.add_argument_group(
            title="action optional arguments (mutually exclusive)"
        )
        action_args = action_group.add_mutually_exclusive_group()
        action_args.add_argument(
            "--list",
            "--list-branches",
            action="store_const",
            const="list",
            help="List active translation branches (implies at least"
            " --verbosity 2)",
            dest="action",
        )
        action_args.add_argument(
            "--dev",
            "--develop",
            action="store_const",
            const="dev",
            help="Publish changes to existing data docs directory",
            dest="action",
        )
        action_args.add_argument(
            "--push",
            action="store_const",
            const="push",
            help="Checkout branch(es), publish changes, commit changes to git,"
            " and push changes to origin (GitHub)",
            dest="action",
        )

        parser.set_defaults(branch="main")
        branch_group = parser.add_argument_group(
            title="branch optional arguments (mutually exclusive)"
        )
        branch_args = branch_group.add_mutually_exclusive_group()
        branch_args.add_argument(
            "--all",
            "--all-branches",
            action="store_const",
            const=ALL_TRANSLATION_BRANCHES,
            help="Manage all active translation branches",
            dest="branch",
        )
        branch_args.add_argument(
            "--branch",
            default="main",
            help="Manage specified translation branch",
            dest="branch",
        )
        branch_args.add_argument(
            "--main",
            action="store_const",
            const="main",
            help="Manage main branch",
            dest="branch",
        )

        parser.add_argument(
            "--branches",
            help=SUPPRESS,
        )

        # Hidden argparse troubleshooting option
        parser.add_argument(
            "--list-args",
            action="store_true",
            help=SUPPRESS,
        )

        branch_group = parser.add_argument_group(
            title="filter optional arguments (mutually exclusive)"
        )
        branch_args = branch_group.add_mutually_exclusive_group()
        branch_args.add_argument(
            "--rdf",
            "--rdf-xml-only",
            action="store_true",
            help="Only copy and distill RDF/XML files",
            dest="rdf_only",
        )
        branch_args.add_argument(
            "--apache",
            "--apache-config-only",
            action="store_true",
            help="Only distill the Apache2 language redirects configuration",
            dest="apache_only",
        )

    def check_titles(self):
        LOG.info("Checking legal code titles")
        log_level = copy(LOG.level)
        LOG.setLevel(LOG_LEVELS[0])
        results = update_title(options={"dryrun": True})
        LOG.setLevel(log_level)
        if results["records_requiring_update"] > 0:
            raise CommandError(
                "Legal code titles require an update. See the `update_title`"
                " command."
            )

    def purge_output_dir(self):
        if self.options["apache_only"] or self.options["rdf_only"]:
            return
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
        if self.options["apache_only"] or self.options["rdf_only"]:
            return
        LOG.info("Collecting static files")
        call_command("collectstatic", interactive=False)

    def write_robots_txt(self):
        """Create robots.txt to discourage indexing."""
        if self.options["apache_only"] or self.options["rdf_only"]:
            return
        LOG.info("Writing robots.txt")
        robots = "User-agent: *\nDisallow: /\n".encode("utf-8")
        save_bytes_to_file(robots, os.path.join(self.output_dir, "robots.txt"))

    def copy_static_wp_content_files(self):
        if self.options["apache_only"] or self.options["rdf_only"]:
            return
        hostname = socket.gethostname()
        output_dir = self.output_dir
        LOG.info("Copying WordPress content files")
        LOG.debug(f"{hostname}:{output_dir}")
        path = "wp-content"
        source = os.path.join(
            settings.PROJECT_ROOT,
            "cc_legal_tools",
            "static",
            path,
        )
        destination = os.path.join(output_dir, path)
        copytree(source, destination)

    def copy_static_cc_legal_tools_files(self):
        if self.options["apache_only"] or self.options["rdf_only"]:
            return
        hostname = socket.gethostname()
        output_dir = self.output_dir
        LOG.info("Copying static cc-legal-tools files")
        LOG.debug(f"{hostname}:{output_dir}")
        path = "cc-legal-tools"
        source = os.path.join(
            settings.PROJECT_ROOT,
            "cc_legal_tools",
            "static",
            "cc-legal-tools",
        )
        destination = os.path.join(output_dir, path)
        copytree(source, destination)

    def copy_static_rdf_files(self):
        if self.options["apache_only"]:
            return
        hostname = socket.gethostname()
        output_dir = self.output_dir
        LOG.info("Copying static RDF/XML files")
        LOG.debug(f"{hostname}:{output_dir}")
        path = "rdf"
        source = os.path.join(
            settings.PROJECT_ROOT,
            "cc_legal_tools",
            "static",
            path,
        )
        destination = os.path.join(output_dir, path)
        copytree(source, destination, dirs_exist_ok=True)

    def distill_and_symlink_rdf_meta(self):
        """
        Generate the index.rdf, images.rdf and copies the rest.
        """
        if self.options["apache_only"]:
            return
        hostname = socket.gethostname()
        output_dir = self.output_dir
        dest_dir = os.path.join(output_dir, "rdf")
        os.makedirs(dest_dir, exist_ok=True)
        LOG.debug(f"{hostname}:{output_dir}")

        # Distill RDF/XML meta files
        for meta_file in ["index.rdf", "images.rdf", "ns.html"]:
            # (schema.rdf is handled by the copy_static_rdf_files function)
            LOG.info(f"Distilling {meta_file}")
            save_url_as_static_file(
                output_dir=dest_dir,
                url=f"/rdf/{meta_file}",
                relpath=meta_file,
            )

        # Symlink RDF/XML meta files
        for meta_file in ["index.rdf", "ns.html", "schema.rdf"]:
            dest_relative = os.path.join("rdf", meta_file)
            if meta_file == "index.rdf":
                os.makedirs(
                    os.path.join(output_dir, "licenses"), exist_ok=True
                )
                symlink = os.path.join("licenses", meta_file)
                symlink_dest = f"../{dest_relative}"
                symlink_path = os.path.join(output_dir, symlink)
            elif meta_file in ["ns.html", "schema.rdf"]:
                symlink = meta_file
                symlink_dest = dest_relative
                symlink_path = os.path.join(output_dir, symlink)
            if os.path.islink(symlink_path):
                os.remove(symlink_path)
            Path(symlink_path).symlink_to(Path(symlink_dest))
            LOG.debug(f"   ^{symlink}")

    def copy_legal_code_plaintext(self):
        if self.options["apache_only"] or self.options["rdf_only"]:
            return
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

    def distill_dev_index(self):
        if self.options["apache_only"] or self.options["rdf_only"]:
            return
        hostname = socket.gethostname()
        output_dir = self.output_dir

        LOG.debug(f"{hostname}:{output_dir}")
        LOG.info("Distilling dev index")
        save_url_as_static_file(
            output_dir,
            url=reverse("dev_index"),
            relpath="index.html",
        )

    def distill_lists(self):
        if self.options["apache_only"] or self.options["rdf_only"]:
            return
        hostname = socket.gethostname()
        output_dir = self.output_dir

        LOG.debug(f"{hostname}:{output_dir}")
        LOG.info("Distilling lists")

        arguments = []
        for category in ["licenses", "publicdomain"]:
            for language_code in settings.LANGUAGES_AVAILABLE_DEEDS_UX:
                arguments.append((output_dir, category, language_code))
        self.pool.starmap(save_list, arguments)

        for category in ["licenses", "publicdomain"]:
            relpath = f"{category}/list.{settings.LANGUAGE_CODE}.html"
            symlink = "index.html"
            wrap_relative_symlink(output_dir, relpath, symlink)
            symlink = "list.html"
            wrap_relative_symlink(output_dir, relpath, symlink)

    def distill_legal_tools(self):
        hostname = socket.gethostname()
        output_dir = self.output_dir
        legal_codes = LegalCode.objects.validgroups()
        redirect_pairs_data = []
        default_languages_deeds = {}
        for group in legal_codes.keys():
            tools = set()
            LOG.debug(f"{hostname}:{output_dir}")
            if self.options["rdf_only"]:
                LOG.info(f"Distilling {group} RDF/XML")
            else:
                LOG.info(
                    f"Distilling {group} deed HTML, legal code HTML, and"
                    " RDF/XML"
                )
            legal_code_arguments = []
            deed_arguments = []
            rdf_arguments = []
            for legal_code in legal_codes[group]:
                tools.add(legal_code.tool)
                legal_code_arguments.append(
                    (output_dir, legal_code, self.options["apache_only"])
                )
            for tool in tools:
                for language_code in settings.LANGUAGES_AVAILABLE_DEEDS_UX:
                    deed_arguments.append(
                        (
                            output_dir,
                            tool,
                            language_code,
                            self.options["apache_only"],
                        )
                    )
                rdf_arguments.append((output_dir, tool))
                if (
                    tool.jurisdiction_code
                    and tool.jurisdiction_code not in default_languages_deeds
                ):
                    if tool.version not in default_languages_deeds:
                        default_languages_deeds[tool.version] = {}
                    default_languages_deeds[tool.version][
                        tool.jurisdiction_code
                    ] = get_default_language_for_jurisdiction_deed_ux(
                        tool.jurisdiction_code,
                    )

            if not self.options["rdf_only"]:
                redirect_pairs_data += self.pool.starmap(
                    save_deed, deed_arguments
                )
                redirect_pairs_data += self.pool.starmap(
                    save_legal_code, legal_code_arguments
                )
            if not self.options["apache_only"]:
                self.pool.starmap(save_rdf, rdf_arguments)

        if self.options["rdf_only"]:
            return
        LOG.info("Writing Apache2 redirects configuration")
        include_lines = [
            "# DO NOT EDIT MANUALLY",
            "#",
            "# This file was generated by the publish command.",
            "# https://github.com/creativecommons/cc-legal-tools-app",
            "#",
            "# See related Apache2 httpd documentation:",
            "# - https://httpd.apache.org/docs/2.4/mod/mod_alias.html",
            "# - https://httpd.apache.org/docs/2.4/mod/mod_rewrite.html",
            "",
        ]

        # Step 1: Language redirects
        include_lines += [
            "#" * 79,
            "# Step 1: Langauge redirects",
            "#       - Redirect alternate language codes to supported Django"
            " language codes",
            "#       - Redirect legacy bug URLs to valid URLs",
            "",
        ]
        redirect_pairs = []
        for pair_list in redirect_pairs_data:
            redirect_pairs += pair_list
        del redirect_pairs_data
        # Add RedirectMatch for ccEngine bug URLs. Entries are added for each
        # of the 4.0 licenses (versus only two regex) to increase readability.
        # https://github.com/creativecommons/cc-legal-tools-app/issues/438
        for unit in ("by", "by-nc", "by-nc-nd", "by-nc-sa", "by-nd", "by-sa"):
            # deed
            redirect_pairs.append(
                [
                    f"/licenses/{unit}/4[.]0/([^/]+)/(deed|deed[.]html)?",
                    f"/licenses/{unit}/4.0/deed.$1",
                ]
            )
            # legalcode
            redirect_pairs.append(
                [
                    f"/licenses/{unit}/4[.]0/([^/]+)/legalcode(?:[.]html)?",
                    f"/licenses/{unit}/4.0/legalcode.$1",
                ]
            )
        widths = [max(map(len, map(str, col))) for col in zip(*redirect_pairs)]
        pad = widths[0] + 2
        redirect_lines = []
        for pair in redirect_pairs:
            pcre_match = f'"^{pair[0]}$"'
            redirect_lines.append(
                f'RedirectMatch  301  {pcre_match.ljust(pad)}  "{pair[1]}"'
            )
        del redirect_pairs
        redirect_lines.sort(reverse=True)
        include_lines += redirect_lines
        del redirect_lines

        # Step 2: Redirect absent deed translations for ported licenses
        # https://github.com/creativecommons/cc-legal-tools-app/issues/236
        step2_lines = [
            "",
            "#" * 79,
            "# Step 2: Redirect absent deed translations for ported licenses",
            "# https://github.com/creativecommons/cc-legal-tools-app/issues/"
            "236",
            "",
        ]
        for ver in sorted(default_languages_deeds.keys()):
            for jur in sorted(default_languages_deeds[ver].keys()):
                default_lang = default_languages_deeds[ver][jur]
                step2_lines += [
                    "RewriteCond %{REQUEST_FILENAME} !-f",
                    "RewriteCond %{REQUEST_FILENAME}.html !-f",
                    "RewriteCond %{REQUEST_FILENAME} !-l",
                    "RewriteCond %{REQUEST_FILENAME}.html !-l",
                    f"RewriteRule licenses/([a-z+-]+)/{ver}/{jur}/deed[.].*$"
                    f" /licenses/$1/{ver}/{jur}/deed.{default_lang} [R=301,L]",
                ]
        include_lines += step2_lines
        del step2_lines

        # Step 3: Redirect absent deed translations for international/universal
        #         licenses:
        # https://github.com/creativecommons/cc-legal-tools-app/issues/236
        step3_lines = [
            "",
            "#" * 79,
            "# Step 3: Redirect absent deed translations for international/"
            "universal",
            "#         licenses",
            "# https://github.com/creativecommons/cc-legal-tools-app/issues/"
            "236",
            "",
            "RewriteCond %{REQUEST_FILENAME} !-f",
            "RewriteCond %{REQUEST_FILENAME}.html !-f",
            "RewriteCond %{REQUEST_FILENAME} !-l",
            "RewriteCond %{REQUEST_FILENAME}.html !-l",
            "RewriteRule licenses/([a-z-]+)/2.1/deed[.].*$"
            " /licenses/$1/2.0/deed.en [R=301,L]",
            "",
            "RewriteCond %{REQUEST_FILENAME} !-f",
            "RewriteCond %{REQUEST_FILENAME}.html !-f",
            "RewriteCond %{REQUEST_FILENAME} !-l",
            "RewriteCond %{REQUEST_FILENAME}.html !-l",
            "RewriteRule licenses/([a-z+-]+)/([0-9.]+)/deed[.].*$"
            " /licenses/$1/$2/deed.en [R=301,L]",
            "",
        ]
        include_lines += step3_lines
        del step3_lines

        include_lines.append("# vim: ft=apache ts=4 sw=4 sts=4 sr noet")
        include_lines.append("")
        include_lines = "\n".join(include_lines).encode("utf-8")
        include_filename = os.path.join(self.config_dir, "language-redirects")
        save_bytes_to_file(include_lines, include_filename)

    def distill_translation_branch_statuses(self):
        if self.options["rdf_only"]:
            return
        hostname = socket.gethostname()
        output_dir = self.output_dir

        LOG.debug(f"{hostname}:{output_dir}")

        tbranches = TranslationBranch.objects.filter(complete=False)
        for tbranch_id in tbranches.values_list("id", flat=True):
            LOG.info(f"Distilling Translation branch status: {tbranch_id}")
            relpath = f"dev/{tbranch_id}.html"
            LOG.debug(f"    {relpath}")
            save_url_as_static_file(
                output_dir,
                url=f"/dev/{tbranch_id}/",
                relpath=relpath,
            )

    def distill_transstats_csv(self):
        if self.options["rdf_only"]:
            return
        LOG.info("Generating translations statistics CSV")
        write_transstats_csv(DEFAULT_CSV_FILE)

    def distill_metadata_yaml(self):
        if self.options["rdf_only"]:
            return
        hostname = socket.gethostname()
        output_dir = self.output_dir

        LOG.debug(f"{hostname}:{output_dir}")
        LOG.info("Distilling metadata.yaml")

        save_url_as_static_file(
            output_dir,
            url=reverse("metadata"),
            relpath="licenses/metadata.yaml",
        )

    def distill_and_copy(self):
        self.check_titles()
        self.purge_output_dir()
        self.call_collectstatic()
        self.write_robots_txt()
        self.copy_static_wp_content_files()
        self.copy_static_cc_legal_tools_files()
        self.copy_static_rdf_files()
        self.distill_and_symlink_rdf_meta()
        self.copy_legal_code_plaintext()
        self.distill_dev_index()
        self.distill_lists()
        self.distill_legal_tools()
        # DISABLED # self.distill_transstats_csv()
        # DISABLED # self.distill_metadata_yaml()

    def checkout_publish_and_push(self):
        """Workflow for publishing and pushing active translation branches"""
        branches = self.options["branches"]
        LOG.info(
            f"Checking and updating build dirs for {len(branches)}"
            " translation branches."
        )
        for branch in branches:
            LOG.debug(f"Publishing branch {branch}")
            with git.Repo(settings.DATA_REPOSITORY_DIR) as repo:
                setup_local_branch(repo, branch)
                self.distill_and_copy()
                if repo.is_dirty(untracked_files=True):
                    # Add any changes and new files
                    commit_and_push_changes(
                        repo,
                        "Update static files generated by cc-legal-tools-app",
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

    def handle(self, *args, **options):
        LOG.setLevel(LOG_LEVELS[int(options["verbosity"])])
        init_utils_logger(LOG)
        self.options = options
        action = options["action"]
        branch = options["branch"]
        branches = options["branches"]
        self.pool = Pool()

        if options["list_args"]:
            # Hidden argparse troubleshooting option
            pprint(options)
            return

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
        active_branches = list_open_translation_branches()

        # process branch options
        if branch == ALL_TRANSLATION_BRANCHES:
            branches = active_branches
        else:
            branches = [branch]

        # process action options
        if action == "list":
            if options["verbosity"] < 2:
                LOG.setLevel(LOG_LEVELS[2])
                LOG.debug("verbosity increased to INFO to show list output")
            if branch == ALL_TRANSLATION_BRANCHES:
                if not active_branches:
                    LOG.info("There are no active translation branches")
                else:
                    LOG.info("Active translation branches:")
                    for branch in branches:
                        LOG.info(branch)
            else:
                if branch in active_branches:
                    status = "is"
                    level = logging.INFO
                else:
                    status = "isn't"
                    level = logging.WARNING
                LOG.log(
                    level,
                    f"the '{branch}' branch {status} an active translation"
                    " branch",
                )
        elif action == "dev":
            self.distill_and_copy()
        elif action == "push":
            if branch == "main":
                raise CommandError(
                    "Pushing to the main branch is prohibited. Changes to the"
                    " main branch should be done via a pull request."
                )
            elif branch == ALL_TRANSLATION_BRANCHES and not active_branches:
                LOG.info("There are no active translation branches")
            else:
                for branch in branches:
                    if branch not in active_branches:
                        raise CommandError(
                            f"the specified branch ('{branch}') is not an"
                            " active translation branch"
                        )
                self.checkout_publish_and_push()
        else:
            raise CommandError(
                "impossible action ('{action}')--please create a GitHub issue"
            )
