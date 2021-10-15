"""
Deal with Transifex
"""
# Standard library
import logging
import os
from typing import Iterable

# Third-party
import dateutil.parser
import git
import polib
import requests
import requests.auth
from django.conf import settings

# First-party/Local
import licenses.models
from i18n import DEFAULT_LANGUAGE_CODE
from i18n.utils import (
    get_pofile_content,
    get_pofile_creation_date,
    get_pofile_path,
    get_pofile_revision_date,
    map_django_to_transifex_language_code,
)
from licenses.utils import b64encode_string

# API 2.0 https://docs.transifex.com/api/introduction
BASE_URL_20 = "https://www.transifex.com/api/2/"
HOST_20 = "www.transifex.com"

# API 2.5 https://docs.transifex.com/api/examples/introduction-to-api-2-5
BASE_URL_25 = "https://api.transifex.com/"
HOST_25 = "api.transifex.com"

LEGALCODES_KEY = "__LEGALCODES__"


def _empty_branch_object():
    """Return a dictionary with LEGALCODES_KEY mapped to an empty list"""
    return {LEGALCODES_KEY: []}


class TransifexAuthRequests(requests.auth.AuthBase):
    """
    Allow using transifex "basic auth" which uses no password, and expects
    the passed value to not even have the ":" separator which Basic Auth is
    supposed to have.
    """

    def __init__(self, token: str):
        self.token = token

    def __eq__(self, other):
        return all(
            [
                self.token == getattr(other, "token", None),
            ]
        )

    def __ne__(self, other):
        return not self == other

    def __call__(self, r):
        auth_str = b64encode_string(f"api:{self.token}")
        r.headers["Authorization"] = f"Basic {auth_str}"
        return r


class TransifexHelper:
    def __init__(self, dryrun: bool = True, logger: logging.Logger = None):
        self.dryrun = dryrun
        self.nop = "<NOP> " if dryrun else ""
        self.log = logger if logger else logging.getLogger()

        self.project_slug = settings.TRANSIFEX["PROJECT_SLUG"]
        self.organization_slug = settings.TRANSIFEX["ORGANIZATION_SLUG"]
        self.team_id = settings.TRANSIFEX["TEAM_ID"]

        api_token = settings.TRANSIFEX["API_TOKEN"]
        auth = TransifexAuthRequests(token=api_token)
        self.api_v20 = requests.Session()
        self.api_v20.auth = auth

        self.api_v25 = requests.Session()
        self.api_v25.auth = auth

    def request20(self, method, path, **kwargs):
        func = getattr(self.api_v20, method)
        url = f"{BASE_URL_20}{path}"
        response = func(url, **kwargs)
        response.raise_for_status()
        return response

    def request25(self, method, path, **kwargs):
        func = getattr(self.api_v25, method)
        url = f"{BASE_URL_25}{path}"
        response = func(url, **kwargs)
        response.raise_for_status()
        return response

    def files_argument(self, name, filename, content):
        """
        Return a valid value for the "files" argument to requests.put or
        requests.post to upload the given content as the given filename, as the
        given argument name.
        """
        return [
            (
                name,
                (
                    os.path.basename(filename),
                    content,
                    "application/octet-stream",
                ),
            )
        ]

    def get_transifex_resource_stats(self):
        """
        Returns a dictionary of current Transifex resource stats keyed by
        resource_slug.

        Uses Transifex API 2.5: Resources
        https://docs.transifex.com/api-2-5/resources
        """
        response = self.request25(
            "get",
            f"organizations/{self.organization_slug}/projects/"
            f"{self.project_slug}/resources/",
        )
        raw_stats = response.json()
        stats = {}
        for data in raw_stats:
            resource_slug = data["slug"]
            del data["slug"]
            stats[resource_slug] = data
        return stats

    def get_transifex_translation_stats(self):
        """
        Returns dictionary of the current Transifex translation stats keyed by
        resource_slug, then transifex_code.

        Uses Transifex API 2.5: Resources
        https://docs.transifex.com/api-2-5/resources
        """
        transifex_resource_slugs = self.resource_stats.keys()

        # Get full stats for each of the resources
        stats = {}
        for resource_slug in transifex_resource_slugs:
            response = self.request25(
                "get",
                f"organizations/{self.organization_slug}/projects/"
                f"{self.project_slug}/resources/{resource_slug}",
            )
            stats[resource_slug] = response.json()["stats"]
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
        Get the updated translation. We don't write it to a file yet. We'll do
        all the updates for a branch at once in the next section.

        Uses Transifex API 2.0: Translations
        https://docs.transifex.com/api/translations

        (Transifex API 2.5 does not include a translations endpoint.)
        """
        response = self.request20(
            "get",
            f"project/{self.project_slug}/resource/{resource_slug}"
            f"/translation/{transifex_code}/",
            params={"mode": "translator", "file": "PO"},
        )
        pofile_content = response.content  # binary
        return pofile_content

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
    #     last_tx_update = dateutil.parser.parse(
    #         self.translation_stats[resource_slug][transifex_code][
    #             "translated"
    #         ]["last_activity"]
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

    def build_local_data(
        self, legal_codes: Iterable["licenses.models.LegalCode"]
    ):
        local_data = {}
        # Deeds & UX - Sources
        resource_name = settings.DEEDS_UX_RESOURCE_NAME
        resource_slug = settings.DEEDS_UX_RESOURCE_SLUG
        pofile_path = get_pofile_path(
            locale_or_legalcode="locale",
            language_code=DEFAULT_LANGUAGE_CODE,
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
        ) in settings.DEEDS_UX_PO_FILE_INFO.items():
            if language_code == DEFAULT_LANGUAGE_CODE:
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
            if language_code == DEFAULT_LANGUAGE_CODE:
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

        Uses Transifex API 2.0: Resources
        https://docs.transifex.com/api/resources

        (Except for screenshots, Transifex API 2.5 is read-only.)
        """
        transifex_code = map_django_to_transifex_language_code(language_code)
        if resource_slug in self.resource_stats.keys():
            self.log.debug(
                f"{self.nop}{resource_name} ({resource_slug})"
                f" {transifex_code}: Transifex already contains resource."
            )
            return
        # Create the resource in Transifex (API 2.5 does not support
        # writing to resources so we're stuck with 2.0 for that).
        pofile_content = get_pofile_content(pofile_obj)
        self.log.warning(
            f"{self.nop}{resource_name} ({resource_slug}) {transifex_code}:"
            f" Transifex does not yet contain resource. Creating using"
            f" {pofile_path}."
        )
        if self.dryrun:
            return
        # data args for creating the resource
        data = dict(slug=resource_slug, name=resource_name, i18n_type="PO")
        # the "source messages" uploaded as the content of a pofile
        files = self.files_argument("content", pofile_path, pofile_content)
        self.request20(
            "post",
            f"project/{self.project_slug}/resources/",
            data=data,
            files=files,
        )
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

        Uses Transifex API 2.0: Translations
        https://docs.transifex.com/api/translations

        (Transifex API 2.5 does not include a translations endpoint.)
        """
        transifex_code = map_django_to_transifex_language_code(language_code)
        if language_code == DEFAULT_LANGUAGE_CODE:
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
        elif transifex_code in self.translation_stats[resource_slug]:
            self.log.debug(
                f"{self.nop}{resource_name} ({resource_slug})"
                f" {transifex_code}: Transifex already contains translation."
            )
            return

        pofile_content = get_pofile_content(pofile_obj)
        # This 'files' arg needs a different argument name, unfortunately.
        files = self.files_argument("file", pofile_path, pofile_content)
        try:
            if not self.dryrun:
                self.request20(
                    "put",
                    f"project/{self.project_slug}/resource/{resource_slug}/"
                    f"translation/{transifex_code}/",
                    files=files,
                )
                self.clear_transifex_stats()
            self.log.info(
                f"{self.nop}{resource_name} ({resource_slug})"
                f" {transifex_code}: Transifex does not yet contain"
                f" translation. Added using {pofile_path}."
            )
        except requests.exceptions.HTTPError:
            self.log.error(
                f"{self.nop}{resource_name} ({resource_slug})"
                f" {transifex_code}: Transifex does not yet contain"
                f" translation. Adding FAILED using {pofile_path}."
            )

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
        if transifex_code == DEFAULT_LANGUAGE_CODE:
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

    def update_pofile_creation_to_match_transifex(
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

    def update_pofile_revision_to_match_transifex(
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
    ):
        pad = len(pofile_path)
        pofile_creation = get_pofile_creation_date(pofile_obj)
        pofile_revision = get_pofile_revision_date(pofile_obj)
        transifex_creation = dateutil.parser.parse(
            self.resource_stats[resource_slug]["created"]
        )
        transifex_revision = dateutil.parser.parse(
            self.resource_stats[resource_slug]["last_update"]
        )
        transifex_label = f"{transifex_code} Transifex {resource_slug}.po"
        #
        # Process creation date
        #
        if pofile_creation is None or transifex_creation < pofile_creation:
            # Normalize Local PO File revision date if its empty or invalid
            pofile_obj = self.update_pofile_creation_to_match_transifex(
                transifex_code,
                resource_slug,
                resource_name,
                pofile_path,
                pofile_obj,
                pofile_creation,
                transifex_creation,
            )
        elif transifex_creation != pofile_creation:
            self.log.error(
                f"{self.nop}{resource_name} ({resource_slug})"
                f" {transifex_code}: 'POT-Creation-Date' mismatch:"
                f"\n{transifex_label:>{pad}}: {transifex_creation}"
                f"\n{pofile_path}: {pofile_creation}"
            )
        #
        # Process revision date
        #
        if pofile_revision is None:
            # Normalize Local PO File revision date if its empty or invalid
            pofile_obj = self.update_pofile_revision_to_match_transifex(
                transifex_code,
                resource_slug,
                resource_name,
                pofile_path,
                pofile_obj,
                pofile_revision,
                transifex_revision,
            )
        elif pofile_revision != transifex_revision:
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
            # Normalize Local PO File revision date if the Local PO File
            # entries and the Transifex PO File entries are the same.
            if po_entries_are_the_same:
                pofile_obj = self.update_pofile_revision_to_match_transifex(
                    transifex_code,
                    resource_slug,
                    resource_name,
                    pofile_path,
                    pofile_obj,
                    pofile_revision,
                    transifex_revision,
                )
            else:
                self.log.error(
                    f"{self.nop}{resource_name} ({resource_slug})"
                    f" {transifex_code}: 'PO-Revision-Date' mismatch:"
                    f"\n{transifex_label:>{pad}}: {transifex_revision}"
                    f"\n{pofile_path}: {pofile_revision}"
                )
        return pofile_obj

    def normalize_translations(self):  # pragma: no cover
        legal_codes = (
            licenses.models.LegalCode.objects.valid()
            .translated()
            .exclude(language_code=DEFAULT_LANGUAGE_CODE)
        )
        repo = git.Repo(settings.DATA_REPOSITORY_DIR)
        if repo.is_dirty():
            self.log.warning(f"{self.nop}Repository is dirty.")

        # Process translation data by starting with local PO files
        # (includes both Deeds & UX and Legal Codes)
        local_data = self.build_local_data(legal_codes)
        # Resources & Sources
        for resource_slug, resource in local_data.items():
            language_code = DEFAULT_LANGUAGE_CODE
            transifex_code = map_django_to_transifex_language_code(
                language_code
            )
            resource_name = resource["name"]
            pofile_path = resource["pofile_path"]
            pofile_obj = resource["pofile_obj"]

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
            pofile_obj = self.normalize_pofile_dates(
                transifex_code,
                resource_slug,
                resource_name,
                pofile_path,
                pofile_obj,
            )
            # # UpdateSource
            # # We're doing English, which is the source language.
            # self.log.info(
            # f"{self.nop}{resource_name} ({resource_slug}) {transifex_code}:"
            # f" Transifex: updating source (all msgid entries) using"
            # f" {pofile_path}."
            # )
            # if self.dryrun:
            #     return
            # # https://docs.transifex.com/api/resources
            # #
            # # Update the source messages on Transifex from our local .pofile.
            # files = self.files_argument(
            #    "content", pofile_path, pofile_content
            # )
            # self.request20(
            # "put",
            # f"project/{self.project_slug}/resource/{resource_slug}"
            # "/content/",
            # files=files,
            # )

            # Translations
            for language_code, translation in resource["translations"].items():
                transifex_code = map_django_to_transifex_language_code(
                    language_code
                )
                pofile_path = translation["pofile_path"]
                pofile_obj = translation["pofile_obj"]

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
                        " Language notyet supported by Transifex. Aborting"
                        " translation langauge processing."
                    )
                    continue

                # Normalize Creation and Revision dates in local PO files
                pofile_obj = self.normalize_pofile_dates(
                    transifex_code,
                    resource_slug,
                    resource_name,
                    pofile_path,
                    pofile_obj,
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
        #     .exclude(language_code=DEFAULT_LANGUAGE_CODE)
        # )
        # with git.Repo(settings.DATA_REPOSITORY_DIR) as repo:
        #     return (
        #         self.check_for_translation_updates_with_repo_and_legal_codes(
        #             repo, legal_codes, update_repo
        #         )
        #     )
