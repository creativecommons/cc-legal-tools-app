"""
Deal with Transifex
"""
import os
from base64 import b64encode

import polib
import requests
import requests.auth
from django.conf import settings

from i18n import DEFAULT_LANGUAGE_CODE
from i18n.utils import get_pofile_content

I18N_FILE_TYPE = "PO"

# API 2.0 https://docs.transifex.com/api/introduction
BASE_URL_20 = "https://www.transifex.com/api/2/"
HOST_20 = "www.transifex.com"

# API 2.5 https://docs.transifex.com/api/examples/introduction-to-api-2-5
BASE_URL_25 = "https://api.transifex.com/"
HOST_25 = "api.transifex.com"


def b64encode_string(s: str) -> str:
    """
    b64encode the string and return the resulting string.
    """
    # This sequence is kind of counter-intuitive, so pull it out into
    # a util function so we're not worrying about it in the rest of the logic.
    bits = s.encode()
    encoded_bits = b64encode(bits)
    encoded_string = encoded_bits.decode()
    return encoded_string


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
        # Update the source messages
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
