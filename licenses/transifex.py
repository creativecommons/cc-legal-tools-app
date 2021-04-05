"""
Deal with Transifex
"""
# Standard library
import logging
import os
from collections import defaultdict
from typing import Iterable

# Third-party
import git
import iso8601
import polib
import requests
import requests.auth
from django.conf import settings
from django.core.management import call_command

# First-party/Local
import licenses.models
from i18n import DEFAULT_LANGUAGE_CODE
from i18n.utils import get_pofile_content, save_content_as_pofile_and_mofile
from licenses.git_utils import (
    commit_and_push_changes,
    kill_branch,
    setup_local_branch,
)
from licenses.utils import b64encode_string

logger = logging.getLogger(__name__)

I18N_FILE_TYPE = "PO"

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
    def __init__(self, verbosity=1):
        """
        Important! Unless verbosity>1, only output errors.
        Use .say(1, "ERROR") and .say(2, "INFO")
        """
        self.verbosity = verbosity
        self.project_slug = settings.TRANSIFEX["PROJECT_SLUG"]
        self.organization_slug = settings.TRANSIFEX["ORGANIZATION_SLUG"]

        api_token = settings.TRANSIFEX["API_TOKEN"]
        auth = TransifexAuthRequests(token=api_token)
        self.api_v20 = requests.Session()
        self.api_v20.auth = auth

        self.api_v25 = requests.Session()
        self.api_v25.auth = auth

    def say(self, verbosity, msg):
        """
        If verbosity is at least 'verbosity', print msg
        """
        if self.verbosity >= verbosity:
            print(msg)

    def request20(self, method, path, **kwargs):
        func = getattr(self.api_v20, method)
        url = f"{BASE_URL_20}{path}"
        r = func(url, **kwargs)
        r.raise_for_status()
        return r

    def request25(self, method, path, **kwargs):
        func = getattr(self.api_v25, method)
        url = f"{BASE_URL_25}{path}"
        r = func(url, **kwargs)
        r.raise_for_status()
        return r

    def get_transifex_resources(self):
        """
        Returns list of dictionaries with return data from querying resources
        """
        RESOURCES_API_25 = (
            f"organizations/{self.organization_slug}/projects/"
            f"{self.project_slug}/resources/"
        )
        return self.request25("get", RESOURCES_API_25).json()

    def files_argument(self, name, filename, content):
        """
        Return a valid value for the "files" argument to requests.put or .post
        to upload the given content as the given filename, as the given
        argument name.
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

    def create_resource(
        self, resource_slug, resource_name, pofilename, pofile_content
    ):
        # Create the resource in Transifex
        # API 2.5 does not support writing to resources so stuck with 2.0 for
        # that.
        # data args for creating the resource
        data = dict(
            slug=resource_slug, name=resource_name, i18n_type=I18N_FILE_TYPE
        )
        # the "source messages" uploaded as the content of a pofile
        files = self.files_argument("content", pofilename, pofile_content)
        self.request20(
            "post",
            f"project/{self.project_slug}/resources/",
            data=data,
            files=files,
        )

    def update_source_messages(
        self, resource_slug, pofilename, pofile_content
    ):
        # Update the source messages on Transifex from our local .pofile.
        files = self.files_argument("content", pofilename, pofile_content)
        self.request20(
            "put",
            f"project/{self.project_slug}/resource/{resource_slug}/content/",
            files=files,
        )

    def update_translations(
        self, resource_slug, language_code, pofilename, pofile_content
    ):
        # This 'files' arg needs a different argument name, unfortunately.
        files = self.files_argument("file", pofilename, pofile_content)
        self.request20(
            "put",
            f"project/{self.project_slug}/resource/{resource_slug}/"
            f"translation/{language_code}/",
            files=files,
        )

    def upload_messages_to_transifex(
        self, legalcode, pofile: polib.POFile = None
    ):
        """
        We get the metadata from the legalcode object.
        You can omit the pofile and we'll get it using legalcode.get_pofile().
        We allow passing it in separately because it makes writing tests so
        much easier.
        """
        language_code = legalcode.language_code
        resource_slug = legalcode.license.resource_slug
        resource_name = legalcode.license.resource_name
        pofilename = legalcode.translation_filename()

        resources = self.get_transifex_resources()
        resource_slugs = [item["slug"] for item in resources]

        if pofile is None:
            pofile = legalcode.get_pofile()

        pofile_content = get_pofile_content(pofile)

        if resource_slug not in resource_slugs:
            if language_code != DEFAULT_LANGUAGE_CODE:
                raise ValueError(
                    f"The resource {resource_slug} does not yet exist in"
                    " Transifex. Must upload English first to create it."
                )
            self.create_resource(
                resource_slug, resource_name, pofilename, pofile_content
            )
        elif language_code == DEFAULT_LANGUAGE_CODE:
            # We're doing English, which is the source language.
            self.update_source_messages(
                resource_slug, pofilename, pofile_content
            )
        else:
            self.update_translations(
                resource_slug, language_code, pofilename, pofile_content
            )

    def get_transifex_resource_stats(self):
        fetch_resources_url = (
            f"organizations/{self.organization_slug}/projects/"
            f"{self.project_slug}/resources/"
        )

        r = self.request25("get", fetch_resources_url)
        resource_slugs_on_transifex = [item["slug"] for item in r.json()]

        # Get fuller stats for all of the resources
        stats = {}
        for resource_slug in resource_slugs_on_transifex:
            resource_url = f"{fetch_resources_url}{resource_slug}"
            r = self.request25("get", resource_url)
            stats[resource_slug] = r.json()["stats"]
        return stats

    @property
    def stats(self):
        # Return cached stats. We create a new TransifexHelper whenever we
        # start doing
        # some stuff with Transifex, so this won't have time to get stale.
        if not hasattr(self, "_stats"):
            self._stats = self.get_transifex_resource_stats()
        return self._stats

    def clear_transifex_stats(self):
        if hasattr(self, "_stats"):
            delattr(self, "_stats")

    def transifex_get_pofile_content(
        self, resource_slug, language_code
    ) -> bytes:
        resource_url = (
            f"project/{self.project_slug}/resource/{resource_slug}"
            f"/translation/{language_code}/"
            f"?mode=translator&file={I18N_FILE_TYPE}"
        )
        # Get the updated translation. We don't write it to a file yet.
        # We'll do all the updates for a branch at once in the next section.
        r2 = self.request20("get", resource_url)
        pofile_content = r2.content  # binary
        return pofile_content

    def update_branch_for_legalcode(self, repo, legalcode, branch_object):
        """
        Pull down the latest translation for the legalcode and update
        the local .po and .mo files. Assumes the correct branch has
        already been checked out.  Adds the updated files to the index.
        """
        resource_slug = legalcode.license.resource_slug
        self.say(2, f"\tUpdating {resource_slug} {legalcode.language_code}")
        last_tx_update = iso8601.parse_date(
            self.stats[resource_slug][legalcode.language_code]["translated"][
                "last_activity"
            ]
        )
        legalcode.translation_last_update = last_tx_update

        branch_object.legalcodes.add(legalcode)
        if (
            branch_object.last_transifex_update is None
            or branch_object.last_transifex_update < last_tx_update
        ):
            branch_object.last_transifex_update = last_tx_update

        # Get the updated translation. We don't write it to a file yet.
        # We'll do all the updates for a branch at once in the next section.
        pofile_path = legalcode.translation_filename()
        pofile_content = self.transifex_get_pofile_content(
            resource_slug, legalcode.language_code
        )
        filenames = save_content_as_pofile_and_mofile(
            pofile_path, pofile_content
        )
        relpaths = [
            os.path.relpath(
                filename, settings.TRANSLATION_REPOSITORY_DIRECTORY
            )
            for filename in filenames
        ]
        repo.index.add(relpaths)

    def handle_updated_translation_branch(self, repo, legalcodes):
        # Legalcodes whose translations have been updated and all belong to the
        # same translation branch.
        # If we update the branch, we'll also publish updates to its static
        # files.
        if not legalcodes:
            return
        branch_name = legalcodes[0].branch_name()
        language_code = legalcodes[0].language_code
        version = legalcodes[0].license.version

        self.say(2, f"Updating branch {branch_name}")

        setup_local_branch(repo, branch_name)

        # Track the translation update using a TranslationBranch object
        # First-party/Local
        from licenses.models import TranslationBranch

        branch_object, _ = TranslationBranch.objects.get_or_create(
            branch_name=branch_name,
            language_code=language_code,
            version=version,
            complete=False,
        )
        for legalcode in legalcodes:
            self.update_branch_for_legalcode(repo, legalcode, branch_object)

        self.say(2, "Publishing static files")
        call_command("publish", branch_name=branch_name)
        repo.index.add(
            [
                os.path.relpath(
                    settings.DISTILL_DIR,
                    settings.TRANSLATION_REPOSITORY_DIRECTORY,
                )
            ]
        )

        # Commit and push this branch
        self.say(2, "Committing and pushing")
        commit_and_push_changes(
            repo, "Translation changes from Transifex.", "", push=True
        )

        self.say(
            2,
            f"Updated branch {branch_name} with updated translations and"
            " pushed",
        )

        # Don't need local branch anymore
        kill_branch(repo, branch_name)

        # Now that we know the new changes are upstream, save the LegalCode
        # objects with their new translation_last_updates, and the branch
        # object.
        # First-party/Local
        from licenses.models import LegalCode

        LegalCode.objects.bulk_update(
            legalcodes,
            fields=["translation_last_update"],
        )
        branch_object.save()

    def handle_legalcodes_with_updated_translations(
        self, repo, legalcodes_with_updated_translations
    ):
        # Group by branches
        legalcodes_by_branchname = defaultdict(list)
        for legalcode in legalcodes_with_updated_translations:
            branch_name = legalcode.branch_name()
            legalcodes_by_branchname[branch_name].append(legalcode)
        branch_names = list(legalcodes_by_branchname.keys())

        # For each branch, get the changes and process them.
        for branch_name, legalcodes in legalcodes_by_branchname.items():
            self.handle_updated_translation_branch(repo, legalcodes)
        # Return the list of updated branch names
        return branch_names

    def check_for_translation_updates(self):
        # This calling of a second function is just to make testing easier.
        # There's otherwise no need or reason for it.
        # First-party/Local
        from licenses.models import LegalCode

        legalcodes = (
            LegalCode.objects.valid()
            .translated()
            .exclude(language_code=DEFAULT_LANGUAGE_CODE)
        )
        with git.Repo(settings.TRANSLATION_REPOSITORY_DIRECTORY) as repo:
            return self.check_for_translation_updates_with_repo_and_legalcodes(
                repo, legalcodes
            )

    def check_for_translation_updates_with_repo_and_legalcodes(
        self, repo: git.Repo, legalcodes: Iterable["licenses.models.LegalCode"]
    ):
        """
        Use the Transifex API to find the last update timestamp for all our
        translations.  If translations are updated, we'll create a branch if
        there isn't already one for that translation, then update it with the
        updated translations, rebuild the HTML, commit all the changes, and
        push it upstream.

        Return a list of the names of all local branches that have been
        updated, that can be used e.g. to run publish on those branches.
        """
        self.say(3, "check if repo is dirty")
        if repo.is_dirty():
            raise Exception(
                f"Git repo at {settings.TRANSLATION_REPOSITORY_DIRECTORY} is"
                " dirty. We cannot continue."
            )
        self.say(2, "Fetch to update repo")
        repo.remotes.origin.fetch()
        resource_slugs_on_transifex = self.stats.keys()

        # We only have the BY* 4.0 licenses in our database so far.
        # We'd like to process one potential translation branch at a time.
        # For the BY* 4.0 licenses, there's a single translation branch for
        # each language. So identify all the languages and iterate over those.
        # (Except English)

        # Gather the files we need to update in git.
        # This is a dict with keys = branch names, and values dictionaries
        # mapping relative paths of files to update, to their contents
        # (bytes).
        self.branches_to_update = defaultdict(_empty_branch_object)
        self.legalcodes_to_update = []
        self.branch_objects_to_update = []

        legalcodes_with_updated_translations = []

        for legalcode in legalcodes:
            language_code = legalcode.language_code
            resource_slug = legalcode.license.resource_slug
            if resource_slug not in resource_slugs_on_transifex:
                self.say(
                    2, f"Transifex has no resource {resource_slug}. Creating."
                )

                # Create the resource
                english_pofile = legalcode.get_english_pofile()
                pofile_content = get_pofile_content(english_pofile)
                self.create_resource(
                    resource_slug=resource_slug,
                    resource_name=legalcode.license.fat_code(),
                    pofilename=os.path.basename(
                        legalcode.translation_filename()
                    ),
                    pofile_content=pofile_content,
                )
                self.clear_transifex_stats()

            if language_code not in self.stats[resource_slug]:
                self.say(
                    2,
                    f"Transifex has no {language_code} translation for"
                    f" {resource_slug}",
                )  # pragma: no cover

                # Upload the language
                self.upload_messages_to_transifex(legalcode)
                self.clear_transifex_stats()

            # We have a translation in this language for this license on
            # Transifex.
            # When was it last updated?
            last_activity = self.stats[resource_slug][language_code][
                "translated"
            ]["last_activity"]
            last_tx_update = (
                iso8601.parse_date(last_activity) if last_activity else None
            )

            if legalcode.translation_last_update is None:
                # First time: initialize, don't create branch
                legalcode.translation_last_update = last_tx_update
                legalcode.save()
                self.say(2, f"Initialized last update time for {legalcode}")
                continue

            if last_tx_update <= legalcode.translation_last_update:
                # No change
                self.say(3, f"No changes for {legalcode}")
                continue

            # Translation has changed!
            self.say(2, f"Translation has changed for {legalcode}")
            legalcodes_with_updated_translations.append(legalcode)

        return self.handle_legalcodes_with_updated_translations(
            repo, legalcodes_with_updated_translations
        )
