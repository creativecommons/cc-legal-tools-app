# Translation

(Return to primary [`../README.md`](../README.md).)


## Overview

To upload/download translation files to/from Transifex, you'll need an account
there with access to these translations. Then follow the [Authentication -
Transifex API v3][transauth]: to get an API token, and set
`TRANSIFEX["API_TOKEN"]` in your environment with its value.

The [creativecommons/cc-legal-tools-data][repodata] repository must be cloned
next to this `cc-legal-tools-app` repository. (It can be elsewhere, then you
need to set `DATA_REPOSITORY_DIR` to its location.) Be sure to clone using a
URL that starts with `git@github...` and not `https://github...`, or you won't
be able to push to it. See [`../README.md`](../README.md) for details.

~~In production, the `check_for_translation_updates` management command should
be run hourly. See [Check for Translation
Updates](#check-for-translation-updates), below.~~

Also see [Publishing changes to git repo](#publishing-changes-to-git-repo),
below.

[Babel][babel] is used for localization information.

Documentation:
- [Babel — Babel documentation][babel]
- [Translation | Django documentation | Django][djangotranslation]

[babel]: http://babel.pocoo.org/en/latest/index.html
[repodata]:https://github.com/creativecommons/cc-legal-tools-data
[transauth]: https://transifex.github.io/openapi/index.html#section/Authentication


## How the tool translation is implemented

Django Translation uses two sets of Gettext Files in the
[creativecommons/cc-legal-tools-data][repodata] repository (the [Data
Repository](#data-repository), above). See that repository for detailed
information and definitions.

Documentation:
- [Translation | Django documentation | Django][djangotranslation]
- Transifex API
  - [Introduction to API 3.0 | Transifex Documentation][api30intro]
  - [Transifex API v3][api30]
  - Python SDK: [transifex-python/transifex/api][apisdk]

[api30]: https://transifex.github.io/openapi/index.html#section/Introduction
[api30intro]: https://docs.transifex.com/api-3-0/introduction-to-api-3-0
[apisdk]: https://github.com/transifex/transifex-python/tree/devel/transifex/api
[djangotranslation]: https://docs.djangoproject.com/en/4.2/topics/i18n/translation/
[repodata]: https://github.com/creativecommons/cc-legal-tools-data


## Add translation

1. Add language to appropriate resource in Transifex
2. Ensure language is present in Django
   - If not, update `cc_legal_tools/settings/base.py`
3. Add objects for new language translation using the `add_translation`
   management
   command.
   - Examples:
        ```shell
        ./bin/manage.sh add_translation -v2 --licenses -l tlh
        ```
        ```shell
        ./bin/manage.sh add_translation -v2 --zero -l tlh
        ```
4. Synchronize repository Gettext files with Transifex
5. Compile `.mo` machine object Gettext files:
    ```shell
    ./bin/manage.sh compilemessages
    ```

Documentation:
- [Quick start guide — polib documentation][polibdocs]
- Also see How the tool translation is implemented documentation, above

[polibdocs]: https://polib.readthedocs.io/en/latest/quickstart.html


## Synchronize repository Gettext files with Transifex

- **TODO** document processes of synchronizing the repository Gettext files
  with Transifex, including the following management commands:
  - `locale_info`
  - `normalize_translations`
  - `compare_translations`
  - `pull_translation`
  - `push_translation`
  - `compilemessages`


## Check for translation updates

> :warning: **This functionality is currently disabled.**

~~The hourly run of `check_for_translation_updates` looks to see if any of the
translation files in Transifex have newer last modification times than we know
about. It performs the following process (which can also be done manually:~~

1. ~~Ensure the Data Repository ([`../README.md`](../README.md)) is in place~~
2. ~~Within the [creativecommons/cc-legal-tools-data][repodata] (the [Data
   Repository](#data-repository)):~~
   1. ~~Checkout or create the appropriate branch.~~
      - ~~For example, if a French translation file for BY 4.0 has changed, the
        branch name will be `cc4-fr`.~~
   2. ~~Download the updated `.po` portable object Gettext file from
      Transifex~~
   3. ~~Do the [Translation Update Process](#translation-update-process)
      (below)~~
      - ~~_This is important and easy to forget,_ but without it, Django will
        keep using the old translations~~
   4. ~~Commit that change and push it upstream.~~
3.~~ Within this `cc-legal-tools-app` repository:~~
   1. ~~For each branch that has been updated, Generate Static
      Files ([`../README.md`](../README.md)). Use the options to update git and
      push the changes.~~

[repodata]:https://github.com/creativecommons/cc-legal-tools-data


Documentation:
- [GitPython Documentation — GitPython documentation][gitpythondocs]
- [Requests: HTTP for Humans™ — Requests documentation][requestsdocs]

[gitpythondocs]: https://gitpython.readthedocs.io/en/stable/index.html
[requestsdocs]: https://docs.python-requests.org/en/master/
