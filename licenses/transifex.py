"""
Deal with Transifex
"""
import os
import re
from collections import defaultdict

import git
import iso8601
import polib
import requests
import requests.auth
from django.conf import settings

from i18n import DEFAULT_LANGUAGE_CODE
from i18n.utils import get_pofile_content
from licenses.git_utils import commit_and_push_changes, setup_local_branch
from licenses.utils import b64encode_string

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
        return all([self.token == getattr(other, "token", None),])

    def __ne__(self, other):
        return not self == other

    def __call__(self, r):
        auth_str = b64encode_string(f"api:{self.token}")
        r.headers["Authorization"] = f"Basic {auth_str}"
        return r


class TransifexHelper:
    def __init__(self):
        self.project_slug = settings.TRANSIFEX["PROJECT_SLUG"]
        self.organization_slug = settings.TRANSIFEX["ORGANIZATION_SLUG"]

        api_token = settings.TRANSIFEX["API_TOKEN"]
        auth = TransifexAuthRequests(token=api_token)
        self.api_v20 = requests.Session()
        self.api_v20.auth = auth

        self.api_v25 = requests.Session()
        self.api_v25.auth = auth

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
        """Returns list of dictionaries with return data from querying resources"""
        RESOURCES_API_25 = f"organizations/{self.organization_slug}/projects/{self.project_slug}/resources/"
        return self.request25("get", RESOURCES_API_25).json()

    def files_argument(self, name, filename, content):
        """
        Return a valid value for the "files" argument to requests.put or .post
        to upload the given content as the given filename, as the given argument
        name.
        """
        return [
            (name, (os.path.basename(filename), content, "application/octet-stream"))
        ]

    def create_resource(self, resource_slug, resource_name, pofilename, pofile_content):
        # Create the resource in Transifex
        # API 2.5 does not support writing to resources so stuck with 2.0 for that.
        # data args for creating the resource
        data = dict(slug=resource_slug, name=resource_name, i18n_type=I18N_FILE_TYPE)
        # the "source messages" uploaded as the content of a pofile
        files = self.files_argument("content", pofilename, pofile_content)
        self.request20(
            "post", f"project/{self.project_slug}/resources/", data=data, files=files
        )

    def update_source_messages(self, resource_slug, pofilename, pofile_content):
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
            f"project/{self.project_slug}/resource/{resource_slug}/translation/{language_code}/",
            files=files,
        )

    def upload_messages_to_transifex(self, legalcode, pofile: polib.POFile = None):
        """
        We get the metadata from the legalcode object.
        You can omit the pofile and we'll get it using legalcode.get_pofile().
        We allow passing it in separately because it makes writing tests so much easier.
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
                    f"The resource {resource_slug} does not yet exist in Transifex. Must upload English first to create it."
                )
            self.create_resource(
                resource_slug, resource_name, pofilename, pofile_content
            )
        elif language_code == DEFAULT_LANGUAGE_CODE:
            # We're doing English, which is the source language.
            self.update_source_messages(resource_slug, pofilename, pofile_content)
        else:
            self.update_translations(
                resource_slug, language_code, pofilename, pofile_content
            )

    def get_transifex_resource_stats(self):
        fetch_resources_url = f"organizations/{self.organization_slug}/projects/{self.project_slug}/resources/"

        r = self.request25("get", fetch_resources_url)
        resource_slugs_on_transifex = [item["slug"] for item in r.json()]

        # Get fuller stats for all of the resources
        stats = {}
        for resource_slug in resource_slugs_on_transifex:
            resource_url = f"{fetch_resources_url}{resource_slug}"
            r = self.request25("get", resource_url)
            stats[resource_slug] = r.json()["stats"]
        return stats

    def check_for_translation_updates(self):
        """
        Use the Transifex API to find the last update timestamp for all our translations.
        If translations are updated, we might end up creating a branch or other actions.
        """
        from licenses.models import LegalCode

        with git.Repo(settings.TRANSLATION_REPOSITORY_DIRECTORY) as repo:
            if repo.is_dirty():
                raise Exception(
                    f"Git repo at {settings.TRANSLATION_REPOSITORY_DIRECTORY} is dirty. "
                    f"We cannot continue."
                )
            repo.remotes.origin.fetch()

            # Get fuller stats for all of the resources
            stats = self.get_transifex_resource_stats()
            resource_slugs_on_transifex = stats.keys()

            # We only have the BY* 4.0 licenses in our database so far.
            # We'd like to process one potential translation branch at a time.
            # For the BY* 4.0 licenses, there's a single translation branch for
            # each language. So identify all the languages and iterate over those.
            # (Except English)

            # Gather the files we need to update in git.
            # This is a dict with keys = branch names, and values dictionaries mapping
            # relative paths of files to update, to their contents (bytes).
            self.branches_to_update = defaultdict(_empty_branch_object)
            self.legalcodes_to_update = []

            legalcodes = LegalCode.objects.filter(
                license__version="4.0", license__license_code__startswith="by"
            ).exclude(language_code=DEFAULT_LANGUAGE_CODE)
            for legalcode in legalcodes:
                # What would its translation branch name be, if there was one?
                branch_name = legalcode.branch_name()
                language_code = legalcode.language_code

                resource_slug = legalcode.license.resource_slug
                if (
                    resource_slug not in resource_slugs_on_transifex
                    or language_code not in stats[resource_slug]
                ):
                    continue

                # We have a translation in this language for this license on Transifex.
                # When was it last updated?
                last_tx_update = iso8601.parse_date(
                    stats[resource_slug][language_code]["translated"]["last_activity"]
                )

                if legalcode.translation_last_update is None:
                    # First time: initialize, don't create branch
                    legalcode.translation_last_update = last_tx_update
                    legalcode.save()
                    continue

                if last_tx_update <= legalcode.translation_last_update:
                    continue

                # Translation has changed!
                legalcode.translation_last_update = last_tx_update
                # Don't save yet, wait til we've updated git, but remember the
                # legalcode to save it later.
                self.legalcodes_to_update.append(legalcode)
                # Download the current translations
                resource_url = (
                    f"/project/{self.project_slug}/resource/{resource_slug}"
                    f"/translation/{language_code}/"
                    f"?mode=translator&file={I18N_FILE_TYPE}"
                )
                r2 = self.request20("get", resource_url)
                pofilepath = legalcode.translation_filename()
                self.branches_to_update[branch_name][pofilepath] = r2.content  # binary
                repo.index.add([pofilepath])

            # Now update any branches we need to
            for branch_name, files in self.branches_to_update.items():
                setup_local_branch(repo, branch_name, settings.OFFICIAL_GIT_BRANCH)
                for path, content in files.items():
                    if path == LEGALCODES_KEY:
                        continue
                    abspath = os.path.join(
                        settings.TRANSLATION_REPOSITORY_DIRECTORY, path
                    )
                    pofile = polib.pofile(pofile=content.decode(), encoding="utf-8")
                    pofile.save(abspath)
                    mofilepath = re.sub(r"\.po$", ".mo", abspath)
                    pofile.save_as_mofile(mofilepath)
                    repo.index.add(abspath)
                    repo.index.add(mofilepath)

                # Commit and push
                timestamp = stats[resource_slug][language_code]["translated"][
                    "last_activity"
                ]
                commit_msg = (
                    f"Translation changes downloaded {timestamp} from Transifex"
                )
                commit_and_push_changes(repo, branch_name, commit_msg)

                # Now that we know the new changes are upstream, save the LegalCode
                # objects with their new translation_last_updates
                LegalCode.objects.bulk_update(
                    self.legalcodes_to_update, fields=["translation_last_update"],
                )
