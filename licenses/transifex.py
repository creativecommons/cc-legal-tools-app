"""
Deal with Transifex
"""
# Standard library
import logging
from typing import Iterable

# Third-party
import git
import polib
import requests
from django.conf import settings
from transifex.api import transifex_api

# First-party/Local
import licenses.models
from i18n.utils import (
    get_pofile_content,
    get_pofile_creation_date,
    get_pofile_path,
    get_pofile_revision_date,
    map_django_to_transifex_language_code,
    parse_date,
)

LEGALCODES_KEY = "__LEGALCODES__"


def _empty_branch_object():
    """Return a dictionary with LEGALCODES_KEY mapped to an empty list"""
    return {LEGALCODES_KEY: []}


class TransifexHelper:
    def __init__(self, dryrun: bool = True, logger: logging.Logger = None):
        self.dryrun = dryrun
        self.nop = "<NOP> " if dryrun else ""
        self.log = logger if logger else logging.getLogger()

        self.organization_slug = settings.TRANSIFEX["ORGANIZATION_SLUG"]
        self.project_slug = settings.TRANSIFEX["PROJECT_SLUG"]
        self.team_id = settings.TRANSIFEX["TEAM_ID"]
        self.project_id = f"o:{self.organization_slug}:p:{self.project_slug}"

        self.api = transifex_api
        self.api.setup(auth=settings.TRANSIFEX["API_TOKEN"])
        self.api_organization = self.api.Organization.get(
            slug=self.organization_slug
        )
        # The Transifex API requires project slugs to be lowercase
        # (^[a-z0-9._-]+$'), but the web interfaces does not (did not?). Our
        # project slug is uppercase.
        # https://transifex.github.io/openapi/#tag/Projects
        for project in self.api_organization.fetch(
            "projects"
        ):  # pragma: no cover
            # TODO: remove coveragepy exclusion after upgrade to Python 3.10
            # https://github.com/nedbat/coveragepy/issues/198
            if project.attributes["slug"] == self.project_slug:
                self.api_project = project
                break
        for i18n_format in self.api.I18nFormat.filter(
            organization=self.api_organization
        ):  # pragma: no cover
            # TODO: remove coveragepy exclusion after upgrade to Python 3.10
            # https://github.com/nedbat/coveragepy/issues/198
            if i18n_format.id == "PO":
                self.api_i18n_format = i18n_format
                break

    def get_transifex_resource_stats(self):
        """
        Returns a dictionary of current Transifex resource stats keyed by
        resource_slug.

        Uses transifex-python
        https://github.com/transifex/transifex-python/tree/devel/transifex/api

        Uses Transifex API 3.0: Resources
        https://transifex.github.io/openapi/#tag/Resources
        """
        self.api_project.reload()
        stats = {}
        resources = sorted(
            self.api_project.fetch("resources").all(), key=lambda x: x.id
        )
        for resource in resources:
            resource_slug = resource.attributes["slug"]
            if resource_slug in ["cc-search", "deeds-choosers"]:
                continue
            stats[resource_slug] = resource.attributes
        return stats

    def get_transifex_translation_stats(self):
        """
        Returns dictionary of the current Transifex translation stats keyed by
        resource_slug then transifex_code.

        Uses transifex-python
        https://github.com/transifex/transifex-python/tree/devel/transifex/api

        Uses Transifex API 3.0: Statistics
        https://transifex.github.io/openapi/#tag/Statistics
        """
        self.api_project.reload()
        stats = {}
        languages_stats = sorted(
            self.api.ResourceLanguageStats.filter(
                project=self.api_project
            ).all(),
            key=lambda x: x.id,
        )
        for l_stats in languages_stats:
            resource_slug = l_stats.related["resource"].id.split(":")[-1]
            transifex_code = l_stats.related["language"].id.split(":")[-1]
            if resource_slug in ["cc-search", "deeds-choosers"]:
                continue
            if resource_slug not in stats:
                stats[resource_slug] = {}
            stats[resource_slug][transifex_code] = l_stats.attributes
        return stats

    @property
    def resource_stats(self):
        # Return cached stats. We create a new TransifexHelper whenever we
        # start doing some stuff with Transifex, so this won't have time to get
        # stale.
        if not hasattr(self, "_resource_stats"):
            self._resource_stats = self.get_transifex_resource_stats()
        return self._resource_stats

    @property
    def translation_stats(self):
        # Return cached stats. We create a new TransifexHelper whenever we
        # start doing some stuff with Transifex, so this won't have time to get
        # stale.
        if not hasattr(self, "_translation_stats"):
            self._translation_stats = self.get_transifex_translation_stats()
        return self._translation_stats

    def clear_transifex_stats(self):
        if hasattr(self, "_resource_stats"):
            delattr(self, "_resource_stats")
        if hasattr(self, "_translation_stats"):
            delattr(self, "_translation_stats")

    def transifex_get_pofile_content(
        self, resource_slug, transifex_code
    ) -> bytes:
        """
        Get the Gettext portable object file (PO file) from Transifex for a
        given translation.

        Uses transifex-python
        https://github.com/transifex/transifex-python/tree/devel/transifex/api

        Uses Transifex API 3.0: Resource Translations
        https://transifex.github.io/openapi/#tag/Resource-Translations
        """
        resource = self.api.Resource.get(
            project=self.api_project, slug=resource_slug
        )
        i18n_type = resource.attributes["i18n_type"]
        if i18n_type != "PO":
            raise ValueError(
                f"Transifex {resource_slug} file format is not 'PO'. It is:"
                f" {i18n_type}"
            )
        if transifex_code == settings.LANGUAGE_CODE:
            # Download source file
            url = self.api.ResourceStringsAsyncDownload.download(
                resource=resource,
                content_encoding="text",
                file_type="default",
            )
        else:
            # Download translation file
            language = self.api.Language.get(code=transifex_code)
            url = self.api.ResourceTranslationsAsyncDownload.download(
                resource=resource,
                language=language,
                mode="translator",
            )
        pofile_content = requests.get(url).content  # binary
        return pofile_content

    def add_resource_to_transifex(
        self,
        language_code,
        resource_slug,
        resource_name,
        pofile_path,
        pofile_obj,
    ):
        """
        Add resource to Transifex

        Uses transifex-python
        https://github.com/transifex/transifex-python/tree/devel/transifex/api

        Uses Transifex API 3.0: Resources
        https://transifex.github.io/openapi/index.html#tag/Resources

        Uses Transifex API 3.0: Resource Strings
        https://transifex.github.io/openapi/index.html#tag/Resource-Strings
        """
        transifex_code = map_django_to_transifex_language_code(language_code)

        if resource_slug in self.resource_stats.keys():
            self.log.debug(
                f"{self.nop}{resource_name} ({resource_slug})"
                f" {transifex_code}: Transifex already contains resource."
            )
            return

        self.log.warning(
            f"{self.nop}{resource_name} ({resource_slug}) {transifex_code}:"
            f" Transifex does not yet contain resource. Creating using"
            f" {pofile_path}."
        )
        if self.dryrun:
            return

        # Create Resource
        self.api.Resource.create(
            name=resource_name,
            slug=resource_slug,
            relationships={
                "i18n_format": self.api_i18n_format,
                "project": self.api_project,
            },
        )

        # Upload Source Strings to Resource
        resource = self.api.Resource.get(
            project=self.api_project, slug=resource_slug
        )
        for entry in pofile_obj:
            # Remove message strings
            entry.msgstr = ""
        pofile_content = get_pofile_content(pofile_obj)
        result = self.api.ResourceStringsAsyncUpload.upload(
            resource=resource,
            content=pofile_content,
        )
        results = ""
        for key, value in result.items():
            results = f"{results}\n     {key}: {value}"
        self.log.info(f"Resource upload results:{results}")
        if not result["strings_created"]:
            self.log.critical("Resource upload failed")
        elif result["strings_skipped"]:
            self.log.warning("Resource strings skipped")
            self.clear_transifex_stats()
        else:
            self.clear_transifex_stats()

    def add_translation_to_transifex_resource(
        self,
        language_code,
        resource_slug,
        resource_name,
        pofile_path,
        pofile_obj,
    ):
        """
        Add translation to Transifex resource.

        Uses transifex-python
        https://github.com/transifex/transifex-python/tree/devel/transifex/api

        Uses Transifex API 3.0: Resources Translations
        https://transifex.github.io/openapi/index.html#tag/Resource-Translations
        """
        transifex_code = map_django_to_transifex_language_code(language_code)
        if language_code == settings.LANGUAGE_CODE:
            raise ValueError(
                f"{self.nop}{resource_name} ({resource_slug})"
                f" {transifex_code}: This function,"
                " add_translation_to_transifex_resource(), is for"
                " translations, not sources."
            )
        elif resource_slug not in self.resource_stats.keys():
            raise ValueError(
                f"{self.nop}{resource_name} ({resource_slug})"
                f" {transifex_code}: Transifex does not yet contain resource."
                " The add_resource_to_transifex() function must be called"
                " before this one: add_translation_to_transifex_resource()."
            )
        elif (
            resource_slug in self.translation_stats
            and transifex_code in self.translation_stats[resource_slug]
            and self.translation_stats[resource_slug][transifex_code].get(
                "translated_strings", 0
            )
            > 0
        ):
            self.log.debug(
                f"{self.nop}{resource_name} ({resource_slug})"
                f" {transifex_code}: Transifex already contains translation."
            )
            return

        pofile_content = get_pofile_content(pofile_obj)
        language = self.api.Language.get(code=transifex_code)
        resource = self.api.Resource.get(
            project=self.api_project, slug=resource_slug
        )
        self.log.info(
            f"{self.nop}{resource_name} ({resource_slug})"
            f" {transifex_code}: Transifex does not yet contain"
            f" translation. Added using {pofile_path}."
        )
        if not self.dryrun:
            result = self.api.ResourceTranslationsAsyncUpload.upload(
                content=pofile_content,
                language=language.id,
                resource=resource,
            )
            results = ""
            for key, value in result.items():
                results = f"{results}\n     {key}: {value}"
            self.log.info(f"Resource upload results:{results}")
            if (
                not result["translations_created"]
                and not result["translations_updated"]
            ):
                self.log.critical("Translation upload failed")
            else:
                self.clear_transifex_stats()

    # def update_branch_for_legal_code(self, repo, legal_code, branch_object):
    #     """
    #     Pull down the latest translation for the legal_code and update
    #     the local .po and .mo files. Assumes the correct branch has
    #     already been checked out.  Adds the updated files to the index.
    #     """
    #     transifex_code = map_django_to_transifex_language_code(
    #         legal_code.language_code
    #     )
    #     resource_slug = legal_code.license.resource_slug
    #     self.log.info(
    #         f"\tUpdating {resource_slug} {legal_code.language_code}"
    #     )
    #     last_tx_update = dateutil.parser.isoparse(
    #         self.translation_stats[resource_slug][transifex_code][
    #             "last_translation_update"
    #         ]
    #     )
    #     legal_code.translation_last_update = last_tx_update
    #
    #     branch_object.legal_codes.add(legal_code)
    #     if (
    #         branch_object.last_transifex_update is None
    #         or branch_object.last_transifex_update < last_tx_update
    #     ):
    #         branch_object.last_transifex_update = last_tx_update
    #
    #     # Get the updated translation. We don't write it to a file yet.
    #     # We'll do all the updates for a branch at once in the next section.
    #     pofile_path = legal_code.translation_filename()
    #     pofile_content = self.transifex_get_pofile_content(
    #         resource_slug, transifex_code
    #     )
    #     filenames = save_content_as_pofile_and_mofile(
    #         pofile_path, pofile_content
    #     )
    #     relpaths = [
    #         os.path.relpath(filename, settings.DATA_REPOSITORY_DIR)
    #         for filename in filenames
    #     ]
    #     repo.index.add(relpaths)

    # def handle_updated_translation_branch(self, repo, legal_codes):
    #     # Legalcodes whose translations have been updated and all belong to
    #     # the same translation branch.
    #     # If we update the branch, we'll also publish updates to its static
    #     # files.
    #     if not legal_codes:
    #         return
    #     branch_name = legal_codes[0].branch_name()
    #     language_code = legal_codes[0].language_code
    #     version = legal_codes[0].license.version
    #
    #     self.log.info(f"Updating branch {branch_name}")
    #
    #     setup_local_branch(repo, branch_name)
    #
    #     # Track the translation update using a TranslationBranch object
    #     # First-party/Local
    #     from licenses.models import TranslationBranch
    #
    #     branch_object, _ = TranslationBranch.objects.get_or_create(
    #         branch_name=branch_name,
    #         language_code=language_code,
    #         version=version,
    #         complete=False,
    #     )
    #     for legal_code in legal_codes:
    #         self.update_branch_for_legal_code(
    #             repo, legal_code, branch_object
    #         )
    #
    #     self.log.info("Publishing static files")
    #     call_command("publish", branch_name=branch_name)
    #     repo.index.add(
    #         [
    #             os.path.relpath(
    #                 settings.DISTILL_DIR,
    #                 settings.DATA_REPOSITORY_DIR,
    #             )
    #         ]
    #     )
    #
    #     # Commit and push this branch
    #     self.log.info("Committing and pushing")
    #     commit_and_push_changes(
    #         repo, "Translation changes from Transifex.", "", push=True
    #     )
    #
    #     self.log.info(
    #         f"Updated branch {branch_name} with updated translations and"
    #         " pushed",
    #     )
    #
    #     # Don't need local branch anymore
    #     kill_branch(repo, branch_name)
    #
    #     # Now that we know the new changes are upstream, save the LegalCode
    #     # objects with their new translation_last_updates, and the branch
    #     # object.
    #     # First-party/Local
    #     from licenses.models import LegalCode
    #
    #     LegalCode.objects.bulk_update(
    #         legal_codes,
    #         fields=["translation_last_update"],
    #     )
    #     branch_object.save()
    #
    # def handle_legal_codes_with_updated_translations(
    #     self, repo, legal_codes_with_updated_translations
    # ):
    #     # Group by branches
    #     legal_codes_by_branchname = defaultdict(list)
    #     for legal_code in legal_codes_with_updated_translations:
    #         branch_name = legal_code.branch_name()
    #         legal_codes_by_branchname[branch_name].append(legal_code)
    #     branch_names = list(legal_codes_by_branchname.keys())
    #
    #     # For each branch, get the changes and process them.
    #     for branch_name, legal_codes in legal_codes_by_branchname.items():
    #         self.handle_updated_translation_branch(repo, legal_codes)
    #     # Return the list of updated branch names
    #     return branch_names

    def normalize_pofile_language(
        self,
        language_code,
        transifex_code,
        resource_slug,
        resource_name,
        pofile_path,
        pofile_obj,
    ):
        keys = {
            "Language": transifex_code,
            "Language-Django": language_code,
            "Language-Transifex": transifex_code,
        }

        all_present_and_correct = True
        for key, value in keys.items():
            if pofile_obj.metadata.get(key, "") != value:
                all_present_and_correct = False
        if all_present_and_correct:
            return pofile_obj

        for key, value in keys.items():
            if pofile_obj.metadata.get(key, "") != value:
                self.log.info(
                    f"{self.nop}{resource_name} ({resource_slug})"
                    f" {transifex_code}:"
                    f" Correcting PO file '{key}':"
                    f"\n{pofile_path}: New Value: '{transifex_code}'"
                )
            if not self.dryrun:
                pofile_obj.metadata[key] = value
        if self.dryrun:
            return pofile_obj
        pofile_obj.save(pofile_path)
        return pofile_obj

    def normalize_pofile_language_team(
        self,
        transifex_code,
        resource_slug,
        resource_name,
        pofile_path,
        pofile_obj,
    ):
        key = "Language-Team"
        if transifex_code == settings.LANGUAGE_CODE:
            translation_team = (
                f"https://www.transifex.com/{self.organization_slug}/"
                f"{self.project_slug}/"
            )
        else:
            translation_team = (
                f"https://www.transifex.com/{self.organization_slug}/teams/"
                f"{self.team_id}/{transifex_code}/"
            )
        if (
            key in pofile_obj.metadata
            and pofile_obj.metadata[key] == translation_team
        ):
            return pofile_obj

        self.log.info(
            f"{self.nop}{resource_name} ({resource_slug}) {transifex_code}:"
            f" Correcting PO file '{key}':"
            f"\n{pofile_path}: New Value: '{translation_team}'"
        )
        if self.dryrun:
            return pofile_obj
        pofile_obj.metadata[key] = translation_team
        pofile_obj.save(pofile_path)
        return pofile_obj

    def normalize_pofile_last_translator(
        self,
        transifex_code,
        resource_slug,
        resource_name,
        pofile_path,
        pofile_obj,
    ):
        key = "Last-Translator"
        filler_data = "FULL NAME <EMAIL@ADDRESS>"
        if key not in pofile_obj.metadata:
            return pofile_obj
        last_translator = pofile_obj.metadata[key]
        if last_translator != filler_data:
            return pofile_obj

        self.log.info(
            f"{self.nop}{resource_name} ({resource_slug}) {transifex_code}:"
            f" Correcting PO file '{key}':"
            f"\n{pofile_path}: Removing: '{filler_data}'"
        )
        if self.dryrun:
            return pofile_obj
        del pofile_obj.metadata[key]
        pofile_obj.save(pofile_path)
        return pofile_obj

    def normalize_pofile_project_id(
        self,
        transifex_code,
        resource_slug,
        resource_name,
        pofile_path,
        pofile_obj,
    ):
        key = "Project-Id-Version"
        if pofile_obj.metadata.get(key, None) == resource_slug:
            return pofile_obj

        self.log.info(
            f"{self.nop}{resource_name} ({resource_slug}) {transifex_code}:"
            f" Correcting PO file '{key}':"
            f"\n{pofile_path}: New value: '{resource_slug}'"
        )
        if self.dryrun:
            return pofile_obj
        pofile_obj.metadata[key] = resource_slug
        pofile_obj.save(pofile_path)
        return pofile_obj

    def normalize_pofile_metadata(
        self,
        language_code,
        transifex_code,
        resource_slug,
        resource_name,
        pofile_path,
        pofile_obj,
    ):
        pofile_obj = self.normalize_pofile_language(
            language_code,
            transifex_code,
            resource_slug,
            resource_name,
            pofile_path,
            pofile_obj,
        )
        pofile_obj = self.normalize_pofile_language_team(
            transifex_code,
            resource_slug,
            resource_name,
            pofile_path,
            pofile_obj,
        )
        pofile_obj = self.normalize_pofile_last_translator(
            transifex_code,
            resource_slug,
            resource_name,
            pofile_path,
            pofile_obj,
        )
        pofile_obj = self.normalize_pofile_project_id(
            transifex_code,
            resource_slug,
            resource_name,
            pofile_path,
            pofile_obj,
        )
        return pofile_obj

    def update_pofile_creation_datetime(
        self,
        transifex_code,
        resource_slug,
        resource_name,
        pofile_path,
        pofile_obj,
        pofile_creation,
        transifex_creation,
    ):
        pad = len(pofile_path)
        label = f"Transifex {resource_slug} {transifex_code}"
        self.log.info(
            f"{self.nop}{resource_name} ({resource_slug}) {transifex_code}:"
            " Correcting PO file 'POT-Creation-Date' to match Transifex:"
            f"\n{pofile_path}: {pofile_creation}"
            f"\n{label:>{pad}}: {transifex_creation}"
        )
        if self.dryrun:
            return pofile_obj
        pofile_obj.metadata["POT-Creation-Date"] = str(transifex_creation)
        pofile_obj.save(pofile_path)
        return pofile_obj

    def update_pofile_revision_datetime(
        self,
        transifex_code,
        resource_slug,
        resource_name,
        pofile_path,
        pofile_obj,
        pofile_revision,
        transifex_revision,
    ):
        pad = len(pofile_path)
        label = f"Transifex {resource_slug} {transifex_code}"
        self.log.info(
            f"{self.nop}{resource_name} ({resource_slug}) {transifex_code}:"
            " Correcting PO file 'PO-Revision-Date' to match Transifex:"
            f"\n{label:>{pad}}: {transifex_revision}"
            f"\n{pofile_path}: {pofile_revision}"
        )
        if self.dryrun:
            return pofile_obj
        pofile_obj.metadata["PO-Revision-Date"] = str(transifex_revision)
        pofile_obj.save(pofile_path)
        return pofile_obj

    def normalize_pofile_dates(
        self,
        transifex_code,
        resource_slug,
        resource_name,
        pofile_path,
        pofile_obj,
        pofile_creation,
        pofile_revision,
        transifex_creation,
        transifex_revision,
    ):
        """
        Normalize PO File metadata datetime fields. As the Transifex API does
        not allow us to modify datetime metadata in Transifex, we update the PO
        Files whenever it is safe to do so (whenever it won't indicate a false
        content equality).
        """
        pad = len(pofile_path)
        transifex_label = f"{transifex_code} Transifex {resource_slug}.po"

        # Process creation date
        if transifex_creation != pofile_creation
        ):
            # Normalize Local PO File creation date to match Transifex
            # (Transifex API 3.0 does not allow for modifcation of Transifex
            #  creation datetimes)
            pofile_obj = self.update_pofile_creation_datetime(
                transifex_code,
                resource_slug,
                resource_name,
                pofile_path,
                pofile_obj,
                pofile_creation,
                transifex_creation,
            )

        # Process revision date
        if pofile_revision is None:
            # Normalize Local PO File revision date if its empty or invalid
            pofile_obj = self.update_pofile_revision_datetime(
                transifex_code,
                resource_slug,
                resource_name,
                pofile_path,
                pofile_obj,
                pofile_revision,
                transifex_revision,
            )
        elif transifex_revision != pofile_revision:
            # Determine if Local PO File and Transifex PO File are the same
            transifex_pofile_content = self.transifex_get_pofile_content(
                resource_slug, transifex_code
            )
            transifex_pofile_obj = polib.pofile(
                pofile=transifex_pofile_content.decode(), encoding="utf-8"
            )
            po_entries_are_the_same = True
            for index, entry in enumerate(pofile_obj):
                if pofile_obj[index] != transifex_pofile_obj[index]:
                    po_entries_are_the_same = False
                    # self.log.debug(
                    # "\n=== Local =======\n"
                    # f"{pofile_obj[index]}"
                    # "\n=== Transifex ===\n"
                    # f"{transifex_pofile_obj[index]}"
                    # )
                    break
            if po_entries_are_the_same:
                # Normalize Local PO File revision date if the Local PO File
                # entries and the Transifex PO File entries are the same.
                #
                # As of 2021-10-21, the Python SDK for the Transifex API 3.0
                # only allows modification of ResourceTranslation attributes
                # strings, reviewed, and proofread (*not* datetime_translated).
                # We can only normalize dates in one direction (normalize PO
                # Files).
                pofile_obj = self.update_pofile_revision_datetime(
                    transifex_code,
                    resource_slug,
                    resource_name,
                    pofile_path,
                    pofile_obj,
                    pofile_revision,
                    transifex_revision,
                )
            else:
                pofile_translated = len(pofile_obj.translated_entries())
                pofile_untranslated = len(pofile_obj.untranslated_entries())
                transifex_untranslated = self.translation_stats[resource_slug][
                    transifex_code
                ]["untranslated_strings"]
                transifex_translated = self.translation_stats[resource_slug][
                    transifex_code
                ]["translated_strings"]
                self.log.error(
                    f"{self.nop}{resource_name} ({resource_slug})"
                    # Transifex
                    f" {transifex_code}: 'PO-Revision-Date' mismatch:"
                    f"\n{transifex_label:>{pad}}: {transifex_revision}"
                    f"\n{'translated strings':>{pad}}:"
                    f" {transifex_translated}"
                    f"\n{'untranslated strings':>{pad}}:"
                    f" {transifex_untranslated}"
                    # Local PO File
                    f"\n{pofile_path}: {pofile_revision}"
                    f"\n{'translated strings':>{pad}}:"
                    f" {pofile_translated}"
                    f"\n{'untranslated strings':>{pad}}:"
                    f" {pofile_untranslated}"
                )

        return pofile_obj

    def check_data_repo_is_clean(self, repo=None):
        if not repo:
            repo = git.Repo(settings.DATA_REPOSITORY_DIR)
        if repo.is_dirty():
            self.log.warning(f"{self.nop}Repository is dirty.")
            return False
        return True

    def get_local_data(self, limit_domain, limit_language):
        deeds_ux = {}
        if not limit_domain or limit_domain == "deeds_ux":
            deeds_ux = settings.DEEDS_UX_PO_FILE_INFO

        legal_codes = []
        if not limit_domain or limit_domain == "legal_code":
            legal_codes = list(
                licenses.models.LegalCode.objects.valid()
                .translated()
                .exclude(language_code=settings.LANGUAGE_CODE)
            )

        local_data = self.build_local_data(
            deeds_ux, legal_codes, limit_language
        )
        return local_data

    def build_local_data(
        self,
        deeds_ux: dict,
        legal_codes: Iterable["licenses.models.LegalCode"],
        limit_language,
    ):
        local_data = {}

        if deeds_ux:
            # Deeds & UX - Sources
            resource_name = settings.DEEDS_UX_RESOURCE_NAME
            resource_slug = settings.DEEDS_UX_RESOURCE_SLUG
            pofile_path = get_pofile_path(
                locale_or_legalcode="locale",
                language_code=settings.LANGUAGE_CODE,
                translation_domain="django",
            )
            pofile_obj = polib.pofile(pofile_path)
            creation_date = get_pofile_creation_date(pofile_obj)
            revision_date = get_pofile_revision_date(pofile_obj)
            local_data[resource_slug] = {
                "name": resource_name,
                "pofile_path": pofile_path,
                "pofile_obj": pofile_obj,
                "creation_date": creation_date,
                "revision_date": revision_date,
                "translations": {},
            }

        # Deeds & UX - Translations
        for (
            language_code,
            language_data,
        ) in deeds_ux.items():
            if language_code == settings.LANGUAGE_CODE:
                continue
            if limit_language and limit_language != language_code:
                continue
            pofile_path = get_pofile_path(
                locale_or_legalcode="locale",
                language_code=language_code,
                translation_domain="django",
            )
            pofile_obj = polib.pofile(pofile_path)
            creation_date = language_data["creation_date"]
            revision_date = language_data["revision_date"]
            local_data[resource_slug]["translations"][language_code] = {
                "pofile_path": pofile_path,
                "pofile_obj": pofile_obj,
                "creation_date": creation_date,
                "revision_date": revision_date,
            }

        # Legal Code - Sources
        for legal_code in legal_codes:
            resource_name = legal_code.license.identifier()
            resource_slug = legal_code.license.resource_slug
            if resource_slug in local_data:
                continue
            pofile_path = legal_code.get_english_pofile_path()
            pofile_obj = polib.pofile(pofile_path)
            creation_date = get_pofile_creation_date(pofile_obj)
            revision_date = get_pofile_revision_date(pofile_obj)
            local_data[resource_slug] = {
                "name": resource_name,
                "pofile_path": pofile_path,
                "pofile_obj": pofile_obj,
                "creation_date": creation_date,
                "revision_date": revision_date,
                "translations": {},
            }

        # Legal Code - Translations
        for legal_code in legal_codes:
            resource_slug = legal_code.license.resource_slug
            language_code = legal_code.language_code
            if language_code == settings.LANGUAGE_CODE:
                continue
            if limit_language and limit_language != language_code:
                continue
            pofile_path = legal_code.translation_filename()
            pofile_obj = polib.pofile(pofile_path)
            creation_date = get_pofile_creation_date(pofile_obj)
            revision_date = get_pofile_revision_date(pofile_obj)
            local_data[resource_slug]["translations"][language_code] = {
                "pofile_path": pofile_path,
                "pofile_obj": pofile_obj,
                "creation_date": creation_date,
                "revision_date": revision_date,
            }

        return local_data

    def normalize_translations(
        self, limit_domain, limit_language
    ):  # pragma: no cover
        self.check_data_repo_is_clean()
        local_data = self.get_local_data(limit_domain, limit_language)

        # Resources & Sources
        for resource_slug, resource in local_data.items():
            language_code = settings.LANGUAGE_CODE
            transifex_code = map_django_to_transifex_language_code(
                language_code
            )
            resource_name = resource["name"]

            pofile_path = resource["pofile_path"]
            pofile_obj = resource["pofile_obj"]
            pofile_creation = resource["creation_date"]
            pofile_revision = resource["revision_date"]

            # Normalize deterministic metadata
            pofile_obj = self.normalize_pofile_metadata(
                language_code,
                transifex_code,
                resource_slug,
                resource_name,
                pofile_path,
                pofile_obj,
            )

            # Ensure Resource is on Transifex
            self.add_resource_to_transifex(
                language_code,
                resource_slug,
                resource_name,
                pofile_path,
                pofile_obj,
            )

            if resource_slug not in self.resource_stats:
                self.log.critical(
                    f"{resource_name} ({resource_slug}) has not yet been"
                    " added to Transifex. Aborting resource processing."
                )
                continue

            transifex_creation = parse_date(
                self.resource_stats[resource_slug]["datetime_created"]
            )
            transifex_revision = parse_date(
                self.resource_stats[resource_slug]["datetime_modified"]
            )

            pofile_obj = self.normalize_pofile_dates(
                transifex_code,
                resource_slug,
                resource_name,
                pofile_path,
                pofile_obj,
                pofile_creation,
                pofile_revision,
                transifex_creation,
                transifex_revision,
            )

            # Translations
            for language_code, translation in resource["translations"].items():
                transifex_code = map_django_to_transifex_language_code(
                    language_code
                )
                pofile_path = translation["pofile_path"]
                pofile_obj = translation["pofile_obj"]
                pofile_creation = translation["creation_date"]
                pofile_revision = translation["revision_date"]

                # Normalize deterministic metadata
                pofile_obj = self.normalize_pofile_metadata(
                    language_code,
                    transifex_code,
                    resource_slug,
                    resource_name,
                    pofile_path,
                    pofile_obj,
                )

                # Ensure translation is on Transifex
                self.add_translation_to_transifex_resource(
                    language_code,
                    resource_slug,
                    resource_name,
                    pofile_path,
                    pofile_obj,
                )
                if transifex_code not in self.translation_stats[resource_slug]:
                    self.log.critical(
                        f"{resource_name} ({resource_slug}) {transifex_code}:"
                        " Language not yet supported by Transifex. Aborting"
                        " translation language processing."
                    )
                    continue

                transifex_creation = parse_date(
                    self.resource_stats[resource_slug]["datetime_created"]
                )
                transifex_revision = parse_date(
                    self.translation_stats[resource_slug][transifex_code][
                        "last_translation_update"
                    ]
                )

                # Normalize Creation and Revision dates in local PO files
                pofile_obj = self.normalize_pofile_dates(
                    transifex_code,
                    resource_slug,
                    resource_name,
                    pofile_path,
                    pofile_obj,
                    pofile_creation,
                    pofile_revision,
                    transifex_creation,
                    transifex_revision,
                )

    def check_for_translation_updates_with_repo_and_legal_codes(
        self,
        repo: git.Repo,
        legal_codes: Iterable["licenses.models.LegalCode"],
        update_repo=False,
    ):  # pragma: no cover
        """
        Use the Transifex API to find the last update timestamp for all our
        translations.  If translations are updated, we'll create a branch if
        there isn't already one for that translation, then update it with the
        updated translations, rebuild the HTML, commit all the changes, and
        push it upstream.

        Return a list of the names of all local branches that have been
        updated, that can be used e.g. to run publish on those branches.
        """
        pass
        # self.log.info(f"{self.nop}Check if repo is dirty")
        # if repo.is_dirty():
        #     if update_repo:
        #         raise git.exc.RepositoryDirtyError(
        #             settings.DATA_REPOSITORY_DIR,
        #             "Repository is dirty. We cannot continue.",
        #         )
        #     else:
        #         self.log.warning(f"{self.nop}Repository is dirty.")
        # if update_repo:
        #     self.log.info(f"{self.nop}Fetch to update repo.")
        #     if not self.dryrun:
        #         repo.remotes.origin.fetch()
        #
        # self.branches_to_update = defaultdict(_empty_branch_object)
        # self.legal_codes_to_update = []
        # self.branch_objects_to_update = []
        # legal_codes_with_updated_translations = []
        #
        #     # TODO: loop through legal codes
        #
        #     if legal_code.translation_last_update is None:
        #         # First time: initialize, don't create branch
        #         legal_code.translation_last_update = last_tx_update
        #         legal_code.save()
        #         self.log.info(
        #             f"{resource_name} ({resource_slug}) {transifex_code}:"
        #             f" Django {language_code} last update time initialized:"
        #             f" {last_tx_update}."
        #         )
        #         continue
        #
        #     if last_tx_update <= legal_code.translation_last_update:
        #         # No change
        #         self.log.debug(
        #             f"No changes for {legal_code.license.identifier()}"
        #         )
        #         continue
        #
        #     # Translation has changed!
        #     self.log.info(f"Translation has changed for {legal_code}")
        #     legal_codes_with_updated_translations.append(legal_code)
        #
        # return self.handle_legal_codes_with_updated_translations(
        #     repo, legal_codes_with_updated_translations
        # )

    def check_for_translation_updates(
        self,
        update_repo=False,
    ):  # pragma: no cover
        """
        This function wraps
        check_for_translation_updates_with_repo_and_legal_codes() to make
        testing easier. Otherwise, there's no need or reason for it.
        """
        pass
        # legal_codes = (
        #     licenses.models.LegalCode.objects.valid()
        #     .translated()
        #     .exclude(language_code=settings.LANGUAGE_CODE)
        # )
        # with git.Repo(settings.DATA_REPOSITORY_DIR) as repo:
        #     return (
        #         self.check_for_translation_updates_with_repo_and_legal_codes(
        #             repo, legal_codes, update_repo
        #         )
        #     )
