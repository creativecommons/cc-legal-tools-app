"""
Interface with Transifex
"""
# Standard library
import difflib
import logging
from typing import Iterable

# Third-party
import git
import polib
import requests
from django.conf import settings
from transifex.api import transifex_api

# First-party/Local
import legal_tools.models
from i18n.utils import (
    get_pofile_content,
    get_pofile_creation_date,
    get_pofile_path,
    get_pofile_revision_date,
    load_deeds_ux_translations,
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

    def upload_resource_to_transifex(
        self,
        resource_slug,
        language_code,
        transifex_code,
        resource_name,
        pofile_path,
        pofile_obj,
        push_overwrite=False,
    ):
        """
        Upload resource to Transifex (defaults to only uploading if resource
        does not yet exist on Transifex).

        Uses transifex-python
        https://github.com/transifex/transifex-python/tree/devel/transifex/api

        Uses Transifex API 3.0: Resources
        https://transifex.github.io/openapi/index.html#tag/Resources

        Uses Transifex API 3.0: Resource Strings
        https://transifex.github.io/openapi/index.html#tag/Resource-Strings
        """
        if not push_overwrite:
            if resource_slug in self.resource_stats.keys():
                self.log.debug(
                    f"{self.nop}{resource_slug} {language_code}"
                    f" ({transifex_code}):: Transifex already contains"
                    " resource."
                )
                return

        self.log.warning(
            f"{self.nop}{resource_slug} {language_code} ({transifex_code}):"
            f" Uploading resource to Transifex using: {pofile_path}."
        )
        if self.dryrun:
            return

        if resource_slug not in self.resource_stats.keys():
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
            # Remove message strings (only upload message ids for resources)
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

    def upload_translation_to_transifex_resource(
        self,
        resource_slug,
        language_code,
        transifex_code,
        pofile_path,
        pofile_obj,
        push_overwrite=False,
    ):
        """
        Upload translation to Transifex resource (defaults to only uploading
        if translation does not yet exist on Transifex).

        Uses transifex-python
        https://github.com/transifex/transifex-python/tree/devel/transifex/api

        Uses Transifex API 3.0: Resources Translations
        https://transifex.github.io/openapi/index.html#tag/Resource-Translations
        """
        if not push_overwrite:
            if language_code == settings.LANGUAGE_CODE:
                raise ValueError(
                    f"{self.nop}{resource_slug} {language_code}"
                    f" ({transifex_code}): This function,"
                    " upload_translation_to_transifex_resource(), is for"
                    " translations, not sources."
                )
            elif resource_slug not in self.resource_stats.keys():
                raise ValueError(
                    f"{self.nop}{resource_slug} {language_code}"
                    f" ({transifex_code}): Transifex does not yet contain"
                    " resource. The upload_resource_to_transifex() function"
                    " must be called before this one "
                    " [upload_translation_to_transifex_resource()]."
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
                    f"{self.nop}{resource_slug} {language_code}"
                    f" ({transifex_code}): Transifex already contains"
                    " translation."
                )
                return

        pofile_content = get_pofile_content(pofile_obj)
        language = self.api.Language.get(code=transifex_code)
        resource = self.api.Resource.get(
            project=self.api_project, slug=resource_slug
        )
        self.log.info(
            f"{self.nop}{resource_slug} {language_code} ({transifex_code}):"
            f" Uploading translation to Transifex using: {pofile_path}."
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
    #     resource_slug = legal_code.tool.resource_slug
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
    #     version = legal_codes[0].tool.version
    #
    #     self.log.info(f"Updating branch {branch_name}")
    #
    #     setup_local_branch(repo, branch_name)
    #
    #     # Track the translation update using a TranslationBranch object
    #     # First-party/Local
    #     from legal_tools.models import TranslationBranch
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
    #     from legal_tools.models import LegalCode
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
        resource_slug,
        language_code,
        transifex_code,
        pofile_path,
        pofile_obj,
        pofile_creation,
        transifex_creation,
    ):
        pad = len(pofile_path)
        label = f"Transifex {resource_slug} {transifex_code}"
        self.log.info(
            f"{self.nop}{resource_slug} {language_code} ({transifex_code}):"
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
        resource_slug,
        language_code,
        transifex_code,
        pofile_path,
        pofile_obj,
        pofile_revision,
        transifex_revision,
    ):
        pad = len(pofile_path)
        label = f"Transifex {resource_slug} {transifex_code}"
        self.log.info(
            f"{self.nop}{resource_slug} {language_code} ({transifex_code}):"
            " Correcting PO file 'PO-Revision-Date' to match Transifex:"
            f"\n{pofile_path}: {pofile_revision}"
            f"\n{label:>{pad}}: {transifex_revision}"
        )
        if self.dryrun:
            return pofile_obj
        pofile_obj.metadata["PO-Revision-Date"] = str(transifex_revision)
        pofile_obj.save(pofile_path)
        return pofile_obj

    def normalize_pofile_dates(
        self,
        resource_slug,
        language_code,
        transifex_code,
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
        if transifex_creation != pofile_creation:
            # Normalize Local PO File creation date to match Transifex
            # (Transifex API 3.0 does not allow for modifcation of Transifex
            #  creation datetimes)
            pofile_obj = self.update_pofile_creation_datetime(
                resource_slug,
                language_code,
                transifex_code,
                pofile_path,
                pofile_obj,
                pofile_creation,
                transifex_creation,
            )

        # Process revision date
        if pofile_revision is None:
            # Normalize Local PO File revision date if its empty or invalid
            pofile_obj = self.update_pofile_revision_datetime(
                resource_slug,
                language_code,
                transifex_code,
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
            for index, pofile_entry in enumerate(pofile_obj):
                if pofile_entry != transifex_pofile_obj[index]:
                    po_entries_are_the_same = False
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
                    resource_slug,
                    language_code,
                    transifex_code,
                    pofile_path,
                    pofile_obj,
                    pofile_revision,
                    transifex_revision,
                )
            else:
                pofile_translated = len(pofile_obj.translated_entries())
                pofile_untranslated = len(pofile_obj.untranslated_entries())
                t_stats = self.translation_stats[resource_slug][transifex_code]
                transifex_translated = t_stats["translated_strings"]
                transifex_untranslated = t_stats["untranslated_strings"]
                self.log.error(
                    f"{self.nop}{resource_slug} {language_code}"
                    f" ({transifex_code}): 'PO-Revision-Date' mismatch:"
                    # Transifex
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

    def resources_metadata_identical(
        self,
        resource_slug,
        language_code,
        transifex_code,
        pofile_path,
        pofile_creation,
        pofile_revision,
        pofile_string_count,
        transifex_creation,
        transifex_revision,
        transifex_string_count,
    ):
        differ = []
        if pofile_creation != transifex_creation:
            differ.append(
                f"\n    PO File creation:   {pofile_creation}"
                f"\n    Transifex creation: {transifex_creation}"
            )
        if pofile_revision != transifex_revision:
            differ.append(
                f"\n    PO File revision:   {pofile_revision}"
                f"\n    Transifex revision: {transifex_revision}"
            )
        if pofile_string_count != transifex_string_count:
            differ.append(
                f"\n    PO File string count:   {pofile_string_count:>4}"
                f"\n    Transifex string count: {transifex_string_count:>4}"
            )
        if differ:
            differ = "".join(differ)
            self.log.error(
                f"{self.nop}{resource_slug} {language_code}"
                f" ({transifex_code}): Resources differ:"
                f"\n  PO File path: {pofile_path}{differ}"
            )
            return False
        else:
            self.log.debug(
                f"{self.nop}{resource_slug} {language_code}"
                f" ({transifex_code}): Resources appear to be identical"
                " based on metadata"
            )
            return True

    def translations_metadata_identical(
        self,
        resource_slug,
        language_code,
        transifex_code,
        pofile_path,
        pofile_creation,
        pofile_revision,
        pofile_translated,
        transifex_creation,
        transifex_revision,
        transifex_translated,
    ):
        differ = []
        if pofile_creation != transifex_creation:
            differ.append(
                f"\n    PO File creation:   {pofile_creation}"
                f"\n    Transifex creation: {transifex_creation}"
            )
        if pofile_revision != transifex_revision:
            differ.append(
                f"\n    PO File revision:   {pofile_revision}"
                f"\n    Transifex revision: {transifex_revision}"
            )
        if pofile_translated != transifex_translated:
            differ.append(
                f"\n    PO File translated entries:   {pofile_translated:>4}"
                f"\n    Transifex translated entries:"
                f" {transifex_translated:>4}"
            )
        if differ:
            differ = "".join(differ)
            self.log.error(
                f"{self.nop}{resource_slug} {language_code}"
                f" ({transifex_code}): Translations differ:"
                f"\n  PO File path: {pofile_path}{differ}"
            )
            return False
        else:
            self.log.debug(
                f"{self.nop}{resource_slug} {language_code}"
                f" ({transifex_code}): Translations appear to be identical"
                " based on metadata"
            )
            return True

    def safesync_pofile(
        self,
        resource_slug,
        language_code,
        transifex_code,
        pofile_path,
        pofile_obj,
    ):
        transifex_pofile_content = self.transifex_get_pofile_content(
            resource_slug, transifex_code
        )
        transifex_pofile_obj = polib.pofile(
            pofile=transifex_pofile_content.decode(), encoding="utf-8"
        )
        changes = []
        for index, entry in enumerate(pofile_obj):
            pofile_entry = entry
            transifex_entry = transifex_pofile_obj[index]
            if pofile_entry != transifex_entry:
                # Prep msgids for display
                if len(pofile_entry.msgid) > 60:  # pragma: no cover
                    p_msgid = f"{pofile_entry.msgid[:62]}..."
                else:  # pragma: no cover
                    p_msgid = pofile_entry.msgid
                if len(pofile_entry.msgid) > 60:  # pragma: no cover
                    t_msgid = f"{transifex_entry.msgid[:62]}..."
                else:  # pragma: no cover
                    t_msgid = transifex_entry.msgid

                # Ensure we're comparing the same entries
                if pofile_entry.msgid != transifex_entry.msgid:
                    self.log.critical(
                        f"{self.nop}{resource_slug} {language_code}"
                        f" ({transifex_code}) Local PO File msgid and"
                        " Transifex msgid do not match:"
                        f"\n    PO File: '{p_msgid}'"
                        f"\n  Transifex: '{t_msgid}'"
                    )
                    continue

                # Skip if local PO FILE entry is translated (even though it
                # differs from Transifex)
                if (
                    pofile_entry.msgstr is not None
                    and pofile_entry.msgstr != ""
                ):
                    continue

                # Add missing translation
                changes.append(f"msgid {index:>4}: '{p_msgid}'")
                if not self.dryrun:
                    pofile_entry.msgstr = transifex_entry.msgstr

        if changes:
            changes = "\n  ".join(changes)
            self.log.info(
                f"{self.nop}{resource_slug} {language_code}"
                f" ({transifex_code}) Adding translation from Transifex to"
                " PO File:"
                f"\n  {changes}"
            )
            if not self.dryrun:
                pofile_obj.save(pofile_path)
        return pofile_obj

    def diff_entry(
        self,
        resource_name,
        resource_slug,
        language_code,
        transifex_code,
        pofile_path,
        pofile_entry,
        transifex_entry,
        colordiff=False,
    ):
        """Display entries as a colorized unified diff."""
        diff = list(
            difflib.unified_diff(
                str(pofile_entry).split("\n"),
                str(transifex_entry).split("\n"),
                fromfile=f"{resource_name} PO File {pofile_path}",
                tofile=(
                    f"{resource_name} Transifex {resource_slug}"
                    f" {language_code} ({transifex_code})"
                ),
                # Number of lines of context (n) is set very high to ensure
                # that the all comments and the entire msgid are shown
                n=999,
            )
        )
        if colordiff:  # pragma: no cover
            rst = "\033[0m"
            for i, line in enumerate(diff):
                if line.startswith("---"):
                    diff[i] = f"\033[91m{line.rstrip()}{rst}"
                elif line.startswith("+++"):
                    diff[i] = f"\033[92m{line.rstrip()}{rst}"
                elif line.startswith("@"):
                    diff[i] = f"\033[36m{line.rstrip()}{rst}"
                elif line.startswith("-"):
                    diff[i] = f"\033[31m{line}{rst}"
                elif line.startswith("+"):
                    diff[i] = f"\033[32m{line}{rst}"
                else:
                    diff[i] = f"\033[90m{line}{rst}"
        diff = "\n".join(diff)
        self.log.warn(f"\n{diff}")

    def diff_translations(
        self,
        resource_name,
        resource_slug,
        language_code,
        transifex_code,
        pofile_path,
        pofile_obj,
        colordiff,
    ):
        transifex_pofile_content = self.transifex_get_pofile_content(
            resource_slug, transifex_code
        )
        transifex_pofile_obj = polib.pofile(
            pofile=transifex_pofile_content.decode(), encoding="utf-8"
        )
        for index, entry in enumerate(pofile_obj):
            pofile_entry = entry
            transifex_entry = transifex_pofile_obj[index]
            if pofile_entry != transifex_entry:
                self.diff_entry(
                    resource_name,
                    resource_slug,
                    language_code,
                    transifex_code,
                    pofile_path,
                    pofile_entry,
                    transifex_entry,
                    colordiff,
                )

    def save_transifex_to_pofile(
        self,
        resource_slug,
        language_code,
        transifex_code,
        pofile_path,
        pofile_obj,
    ):
        # Get Transifex PO File
        transifex_pofile_content = self.transifex_get_pofile_content(
            resource_slug, transifex_code
        )
        transifex_obj = polib.pofile(
            pofile=transifex_pofile_content.decode(), encoding="utf-8"
        )

        # Overrite local PO File
        self.log.info(
            f"{self.nop}{resource_slug} {language_code} ({transifex_code}):"
            " overwriting local translation with Transifex translation:"
            f" {pofile_path}"
        )
        if not self.dryrun:
            transifex_obj.save(pofile_path)
        return transifex_obj

    def check_data_repo_is_clean(self, repo=None):
        if not repo:
            repo = git.Repo(settings.DATA_REPOSITORY_DIR)
        if repo.is_dirty():
            self.log.warning(f"{self.nop}Repository is dirty.")
            return False
        return True

    def get_local_data(self, limit_domain, limit_language):
        self.log.debug(
            f"limit_domain: {limit_domain}, limit_language: {limit_language}"
        )

        # Deeds & UX
        deeds_ux = {}
        if not limit_domain or limit_domain == "deeds_ux":
            deeds_ux = settings.DEEDS_UX_PO_FILE_INFO
            if limit_language:
                deeds_ux = {limit_language: deeds_ux[limit_language]}

        # Legal Codes
        valid_domains = []
        if limit_domain and limit_domain != "deeds_ux":
            for legal_code in (
                legal_tools.models.LegalCode.objects.valid()
                .translated()
                .filter(language_code=settings.LANGUAGE_CODE)
            ):
                valid_domains.append(legal_code.translation_domain)
            valid_domains = sorted(list(set(valid_domains)))
            self.log.debug(
                f"valid legal code translation domains: {valid_domains}"
            )
        legal_codes = []
        if (
            not limit_domain
            or limit_domain == "legal_code"
            or limit_domain in valid_domains
        ):
            if limit_language:
                legal_codes = list(
                    legal_tools.models.LegalCode.objects.valid()
                    .translated()
                    .exclude(language_code=settings.LANGUAGE_CODE)
                    .filter(language_code=limit_language)
                )
            else:
                legal_codes = list(
                    legal_tools.models.LegalCode.objects.valid()
                    .translated()
                    .exclude(language_code=settings.LANGUAGE_CODE)
                )
        if limit_domain and limit_domain in valid_domains:
            legal_codes_selected = []
            for legal_code in legal_codes:
                if limit_domain == legal_code.translation_domain:
                    legal_codes_selected.append(legal_code)
            legal_codes = legal_codes_selected

        # Build local data and return
        local_data = self.build_local_data(deeds_ux, legal_codes)
        return local_data

    def build_local_data(
        self,
        deeds_ux: dict,
        legal_codes: Iterable["legal_tools.models.LegalCode"],
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
            resource_name = legal_code.tool.identifier()
            resource_slug = legal_code.tool.resource_slug
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
            resource_slug = legal_code.tool.resource_slug
            language_code = legal_code.language_code
            if language_code == settings.LANGUAGE_CODE:
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

    def resource_present(self, resource_slug, resource_name):
        if resource_slug not in self.resource_stats:
            self.log.critical(
                f"{resource_name} ({resource_slug}) has not yet been"
                " added to Transifex. Aborting resource processing."
            )
            return False
        else:
            return True

    def translation_supported(
        self,
        resource_slug,
        resource_name,
        transifex_code,
    ):
        if transifex_code not in self.translation_stats[resource_slug]:
            self.log.critical(
                f"{resource_name} ({resource_slug}) {transifex_code}:"
                " Language not yet supported by Transifex. Aborting"
                " translation language processing."
            )
            return False
        else:
            return True

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
            self.upload_resource_to_transifex(
                resource_slug,
                language_code,
                transifex_code,
                resource_name,
                pofile_path,
                pofile_obj,
                push_overwrite=False,
            )

            if not self.resource_present(resource_slug, resource_name):
                continue

            r_stats = self.resource_stats[resource_slug]
            transifex_creation = parse_date(r_stats["datetime_created"])
            transifex_revision = parse_date(r_stats["datetime_modified"])

            pofile_obj = self.normalize_pofile_dates(
                resource_slug,
                language_code,
                transifex_code,
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
                pofile_translated = len(pofile_obj.translated_entries())

                # Normalize deterministic metadata
                pofile_obj = self.normalize_pofile_metadata(
                    language_code,
                    transifex_code,
                    resource_slug,
                    resource_name,
                    pofile_path,
                    pofile_obj,
                )

                if not self.translation_supported(
                    resource_slug, resource_name, transifex_code
                ):
                    continue

                # Ensure translation is on Transifex
                self.upload_translation_to_transifex_resource(
                    resource_slug,
                    language_code,
                    transifex_code,
                    pofile_path,
                    pofile_obj,
                    push_overwrite=False,
                )

                t_stats = self.translation_stats[resource_slug][transifex_code]
                # transifex_creation is a resource stat and is set above
                transifex_revision = parse_date(
                    t_stats["last_translation_update"]
                )
                transifex_translated = t_stats["translated_strings"]

                # Compare metadata
                if not self.translations_metadata_identical(
                    resource_slug,
                    language_code,
                    transifex_code,
                    pofile_path,
                    pofile_creation,
                    pofile_revision,
                    pofile_translated,
                    transifex_creation,
                    transifex_revision,
                    transifex_translated,
                ):
                    # Add missing translations to local PO File
                    pofile_obj = self.safesync_pofile(
                        resource_slug,
                        language_code,
                        transifex_code,
                        pofile_path,
                        pofile_obj,
                    )

                # Normalize Creation and Revision dates in local PO File
                pofile_obj = self.normalize_pofile_dates(
                    resource_slug,
                    language_code,
                    transifex_code,
                    pofile_path,
                    pofile_obj,
                    pofile_creation,
                    pofile_revision,
                    transifex_creation,
                    transifex_revision,
                )

    def compare_translations(
        self, limit_domain, limit_language, force, colordiff
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
            pofile_string_count = len(
                [e for e in pofile_obj if not e.obsolete]
            )

            if not self.resource_present(resource_slug, resource_name):
                continue

            r_stats = self.resource_stats[resource_slug]
            transifex_creation = parse_date(r_stats["datetime_created"])
            transifex_revision = parse_date(r_stats["datetime_modified"])
            transifex_string_count = r_stats["string_count"]

            metadata_identical = self.resources_metadata_identical(
                resource_slug,
                language_code,
                transifex_code,
                pofile_path,
                pofile_creation,
                pofile_revision,
                pofile_string_count,
                transifex_creation,
                transifex_revision,
                transifex_string_count,
            )
            if force or not metadata_identical:
                self.log.critical("resource diff not yet implimented")

            # Translations
            for language_code, translation in resource["translations"].items():
                transifex_code = map_django_to_transifex_language_code(
                    language_code
                )
                pofile_path = translation["pofile_path"]
                pofile_obj = translation["pofile_obj"]
                pofile_creation = translation["creation_date"]
                pofile_revision = translation["revision_date"]
                pofile_translated = len(pofile_obj.translated_entries())

                if not self.translation_supported(
                    resource_slug, resource_name, transifex_code
                ):
                    continue

                t_stats = self.translation_stats[resource_slug][transifex_code]
                # transifex_creation is a resource stat and is set above
                transifex_revision = parse_date(
                    t_stats["last_translation_update"]
                )
                transifex_translated = t_stats["translated_strings"]

                metadata_identical = self.translations_metadata_identical(
                    resource_slug,
                    language_code,
                    transifex_code,
                    pofile_path,
                    pofile_creation,
                    pofile_revision,
                    pofile_translated,
                    transifex_creation,
                    transifex_revision,
                    transifex_translated,
                )
                if force or not metadata_identical:
                    self.diff_translations(
                        resource_name,
                        resource_slug,
                        language_code,
                        transifex_code,
                        pofile_path,
                        pofile_obj,
                        colordiff,
                    )

    def pull_translation(
        self, limit_domain, limit_language
    ):  # pragma: no cover
        self.check_data_repo_is_clean()
        local_data = self.get_local_data(limit_domain, limit_language)

        # Resources & Sources
        for resource_slug, resource in local_data.items():
            resource_name = resource["name"]

            if not self.resource_present(resource_slug, resource_name):
                continue

            # Translations
            for language_code, translation in resource["translations"].items():
                transifex_code = map_django_to_transifex_language_code(
                    language_code
                )
                pofile_path = translation["pofile_path"]
                pofile_obj = translation["pofile_obj"]

                if not self.translation_supported(
                    resource_slug, resource_name, transifex_code
                ):
                    continue

                pofile_obj = self.save_transifex_to_pofile(
                    resource_slug,
                    language_code,
                    transifex_code,
                    pofile_path,
                    pofile_obj,
                )

        # Normalize newly updated local PO File
        if not self.dryrun:
            if limit_domain and limit_domain == "deeds_ux":
                load_deeds_ux_translations()
            self.normalize_translations(limit_domain, limit_language)

    def push_translation(
        self, limit_domain, limit_language
    ):  # pragma: no cover
        self.check_data_repo_is_clean()
        local_data = self.get_local_data(limit_domain, limit_language)

        # Resources & Sources
        for resource_slug, resource in local_data.items():
            resource_name = resource["name"]

            if not self.resource_present(resource_slug, resource_name):
                continue

            # Translations
            for language_code, translation in resource["translations"].items():
                transifex_code = map_django_to_transifex_language_code(
                    language_code
                )
                pofile_path = translation["pofile_path"]
                pofile_obj = translation["pofile_obj"]

                if not self.translation_supported(
                    resource_slug, resource_name, transifex_code
                ):
                    continue

                self.upload_translation_to_transifex_resource(
                    resource_slug,
                    language_code,
                    transifex_code,
                    pofile_path,
                    pofile_obj,
                    push_overwrite=True,
                )

        # Normalize local PO File to match newly updated Transifex translation
        if not self.dryrun:
            if limit_domain == "deeds_ux":
                load_deeds_ux_translations()
            self.normalize_translations(limit_domain, limit_language)

    def push_resource(self, limit_domain):  # pragma: no cover
        language_code = settings.LANGUAGE_CODE
        self.check_data_repo_is_clean()
        local_data = self.get_local_data(limit_domain, language_code)

        resource_slug = limit_domain
        transifex_code = map_django_to_transifex_language_code(language_code)
        resource_name = local_data[resource_slug]["name"]
        pofile_path = local_data[resource_slug]["pofile_path"]
        pofile_obj = local_data[resource_slug]["pofile_obj"]

        self.upload_resource_to_transifex(
            resource_slug,
            language_code,
            transifex_code,
            resource_name,
            pofile_path,
            pofile_obj,
            push_overwrite=True,
        )

        # Normalize local PO File to match newly updated Transifex translation
        if not self.dryrun:
            if limit_domain == "deeds_ux":
                load_deeds_ux_translations()
            # self.normalize_translations(limit_domain, limit_language)

    def check_for_translation_updates_with_repo_and_legal_codes(
        self,
        repo: git.Repo,
        legal_codes: Iterable["legal_tools.models.LegalCode"],
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
        #             f"No changes for {legal_code.tool.identifier()}"
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
        #     legal_tools.models.LegalCode.objects.valid()
        #     .translated()
        #     .exclude(language_code=settings.LANGUAGE_CODE)
        # )
        # with git.Repo(settings.DATA_REPOSITORY_DIR) as repo:
        #     return (
        #         self.check_for_translation_updates_with_repo_and_legal_codes(
        #             repo, legal_codes, update_repo
        #         )
        #     )
