# cc-legal-tools-app

**Creative Commons (CC) Legal Tools Application.** This repository contains the
application that manages the license tools and public domain tools (static
HTML, internationalization and localization files, etc.). It consumes and
generates data in the [creativecommons/cc-legal-tools-data][repodata]
repository.

[repodata]:https://github.com/creativecommons/cc-legal-tools-data


## Code of conduct

[`CODE_OF_CONDUCT.md`][org-coc]:
> The Creative Commons team is committed to fostering a welcoming community.
> This project and all other Creative Commons open source projects are governed
> by our [Code of Conduct][code_of_conduct]. Please report unacceptable
> behavior to [conduct@creativecommons.org](mailto:conduct@creativecommons.org)
> per our [reporting guidelines][reporting_guide].

[org-coc]: https://github.com/creativecommons/.github/blob/main/CODE_OF_CONDUCT.md
[code_of_conduct]: https://opensource.creativecommons.org/community/code-of-conduct/
[reporting_guide]: https://opensource.creativecommons.org/community/code-of-conduct/enforcement/


## Contributing

See [`CONTRIBUTING.md`][org-contrib].

[org-contrib]: https://github.com/creativecommons/.github/blob/main/CONTRIBUTING.md


## About

This application manages 639 legal tools (636 licenses and 3 public domain
tools). The current version of the licenses is 4.0 and includes 6 licenses.
They are international and are designed to operate globally, ensuring they are
robust, enforceable and easily adopted worldwide. Prior versions were adapted
to specific jurisdictions ("ported"). That is why there are 636 licenses.

Broadly speaking, each legal tool consists of three layers:
1. `deed`: a plain language summary of the legal tool
2. `legalcode`: the legal tool itself
3. `rdf`: metadata about the legal tool in RDF/XML format

With translations of the deed and translations of the legal code, this
application manages over 30,000 documents.


### Not the live site

This project is not intended to serve the legal tools directly. Instead, a
command line tool can be used to save all the rendered HTML and RDF/XML pages
as files. Then those files are used as part of the CreativeCommons.org
site (served as static files).


## Software Versions

- [Python 3.11][python311] specified in:
  - [`.github/workflows/django-app-coverage.yml`][django-app-coverage]
  - [`.github/workflows/static-analysis.yml`][static-analysis]
  - [`.pre-commit-config.yaml`](.pre-commit-config.yaml)
  - [`Dockerfile`](Dockerfile)
  - [`Pipfile`](Pipfile)
  - [`pyproject.toml`](pyproject.toml)
- [Django 4.2 (LTS)][django42]
  - [`Pipfile`](Pipfile)

[django-app-coverage]: .github/workflows/django-app-coverage.yml
[static-analysis]: .github/workflows/static-analysis.yml
[python311]: https://docs.python.org/3.11/
[django42]: https://docs.djangoproject.com/en/4.2/


## Setting up the Project


### Data Repository

Visit [Cloning a Repository][gitclone] on how to clone a GitHub repository.

The [creativecommons/cc-legal-tools-data][repodata] project repository should
be cloned into a directory adjacent to this one:
```
PARENT_DIR
├── cc-legal-tools-app     (git clone of this repository)
└── cc-legal-tools-data    (git clone of the cc-legal-tools-data repository)
```

If it is not cloned into the default location, the Django
`DATA_REPOSITORY_DIR` Django configuration setting, or the
`DATA_REPOSITORY_DIR` environment variable can be used to configure its
location.

[gitclone]:https://docs.github.com/en/repositories/creating-and-managing-repositories/cloning-a-repository
[repodata]:https://github.com/creativecommons/cc-legal-tools-data


### Docker Compose Setup

Use the following instructions to start the project with Docker compose.
Pleaes note that CC staff use macOS for development--please help us with
documenting other operating systems if you encounter issues.

1. Ensure the [Data Repository](#data-repository), above, is in place
2. [Install Docker Engine](https://docs.docker.com/engine/install/)
3. Ensure you are at the top level of the directory where you cloned this repository (where `manage.py` is)
4. Create Django local settings file
    ```shell
    cp cc_legal_tools/settings/local.example.py cc_legal_tools/settings/local.py
    ```
    - Update variables in new file, as necessary
5. Build the containers
    ```shell
    docker compose build
    ```
6. **Run the containers**
    ```shell
    docker compose up
    ```
   1. **app** ([127.0.0.1:8005](http://127.0.0.1:8005/)): this Django
      application
      - Any changes made to Python will be detected and rebuilt
        transparently as long as the development server is running.
   2. **static** ([127.0.0.1:8006](http://127.0.0.1:8006/)): a static web
      server serving [creativecommons/cc-legal-tools-data][repodata]:`docs/`
7. Initialize data
    ```shell
    ./dev/init_data.sh
    ```
    1. Delete database (which may not yet exist)
    2. Initialize database
    3. Perform databsea migrations
    4. Crate supseruser (will prompt for password)
    5. Load data

[repodata]:https://github.com/creativecommons/cc-legal-tools-data


### Manual Setup

> :warning: **This section may be helpful for maintaining the project, but
> should _NOT_ be used for development. Please use the Docker Compose Setup,
> above.**

1. Complete Docker Compose Setup, above
2. Development Environment
   1. Install dependencies
      - Linux:
        ```shell
        sudo apt-get install python3.11 python3.11-dev python3-pip
        ```
        ```shell
        pip3 install pipenv
        ```
      - macOS: via [Homebrew](https://brew.sh/):
        ```shell
        brew install pipenv python@3.11
        ```
      - Windows: [install Python][python-windows] and then use `pip` to install
        `pipenv`:
        ```shell
        pip install pipenv
        ```
   2. Install Python environment and modules via pipenv to create a
      virtualenv
      - Linux:
        ```shell
        pipenv install --dev --python /usr/bin/python3.11
        ```
      - macOS: via [Homebrew](https://brew.sh/):
        ```shell
        pipenv install --dev --python /usr/local/opt/python@3.11/libexec/bin/python
        ```
      - Windows:
        ```shell
        pipenv install --dev --python \User\Appdata\programs\python
        ```
   3. Install pre-commit hooks
    ```shell
    pipenv run pre-commit install
    ```
3. Run development server ([127.0.0.1:8005](http://127.0.0.1:8005/))
    ```shell
    pipenv run ./manage.py runserver
    ```
   - Any changes made to Python will be detected and rebuilt transparently as
     long as the development server is running.

[python-windows]:https://www.pythontutorial.net/getting-started/install-python/


#### Manual Commands

> :information_source: The rest of the documentation assumes Docker. If you are
> using a manual setup, use `pipenv run` instead of `docker compose exec app`
> for the commands below.


### Tooling

- **[Python Guidelines — Creative Commons Open Source][ccospyguide]**
- [Black][black]: the uncompromising Python code formatter
- [Coverage.py][coveragepy]: Code coverage measurement for Python
- Docker
  - [Dockerfile reference | Docker Documentation][dockerfile]
  - [Compose file version 3 reference | Docker Documentation][compose3]
- [flake8][flake8]: a python tool that glues together pep8, pyflakes, mccabe,
  and third-party plugins to check the style and quality of some python code.
- [isort][isort]: A Python utility / library to sort imports.
- [pre-commit][precommit]: A framework for managing and maintaining
  multi-language pre-commit hooks.

[ccospyguide]: https://opensource.creativecommons.org/contributing-code/python-guidelines/
[black]: https://github.com/psf/black
[coveragepy]: https://github.com/nedbat/coveragepy
[dockerfile]: https://docs.docker.com/engine/reference/builder/
[compose3]: https://docs.docker.com/compose/compose-file/compose-file-v3/
[flake8]: https://gitlab.com/pycqa/flake8
[isort]: https://pycqa.github.io/isort/
[precommit]: https://pre-commit.com/


#### Helper Scripts

Best run before every commit:
- `./dev/coverage.sh` - Run coverage tests and report
- `./dev/tools.sh` - Run Python code tools (isort, black, flake8)

Run as needed:
- `./dev/copy_theme.sh` - Copy the portions of
  [creativecommons/vocabulary-theme][vocab-theme] needed for local development
  - Run after each new release of
    [creativecommons/vocabulary-theme][vocab-theme]

Data management:
- `./dev/dump_data.sh` - Dump Django application data
- `./dev/init_data.sh` - :warning: Initialize Django application data
- `./dev/load_data.sh` - Load Django application data

Esoteric and dangerous:
- `./dev/updatemessages.sh` - :warning: Run Django Management
  nofuzzy_makemessages with helpful options (including excluding legalcode) and
  compilemessages

[vocab-theme]: https://github.com/creativecommons/vocabulary-theme


#### Coverage Tests and Report

The coverage tests and report are run as part of pre-commit and as a GitHub
Action. To run it manually:
1. Ensure the [Data Repository](#data-repository), above, is in place
2. Ensure [Docker Compose Setup](#docker-compose-setup), above, is complete
2. Coverage test
    ```shell
    docker compose exec app coverage run manage.py test --noinput --keepdb
    ```
3. Coverage report
    ```shell
    docker compose exec app coverage report
    ```


### Commit Errors


#### Error building trees

If you encounter an `error: Error building trees` error from pre-commit when
you commit, try adding your files (`git add <FILES>`) before committing them.


## Frontend Dependencies

The following CC projects are used to achieve a consistent look and feel:
- [creativecommons/vocabulary-theme][vocabulary-theme]: WordPress Theme
  implementation of the Vocabulary design system

[vocabulary-theme]: https://github.com/creativecommons/vocabulary-theme


## Data

The legal tools metadata is in a database. The metadata tracks which legal
tools exist, their translations, their ports, and their characteristics like
what they permit, require, and prohibit.

~~The metadata can be downloaded by visiting the URL path:
`127.0.0.1:8005`[`/licenses/metadata.yaml`][metadata]~~ (currently disabled)

[metadata]: http://127.0.0.1:8005/licenses/metadata.yaml

There are two main models (Django terminology for tables) in
[`legal_tools/models.py`](legal_tools/models.py):
1. `LegalCode`
2. `Tool`

A Tool can be identified by a `unit` (ex. `by`, `by-nc-sa`, `devnations`) which
is a proxy for the complete set of permissions, requirements, and prohibitions;
a `version` (ex. `4.0`, `3.0)`, and an optional `jurisdiction` for ports. So we
might refer to the tool by its **identifier** "BY 3.0 AM" which would be the
3.0 version of the BY license terms as ported to the Armenia jurisdiction. For
additional information see: [**Legal Tools Namespace** -
creativecommons/cc-legal-tools-data: CC Legal Tools Data (static HTML, language
files, etc.)][namespace].

There are three places legal code text could be:
1. **Gettext files** (`.po` and `.mo`) in the
   [creativecommons/cc-legal-tools-data][repodata] repository (legal tools with
   full translation support):
   - 4.0 Licenses
   - CC0
2. **Django template**
   ([`legalcode_licenses_3.0_unported.html`][unportedtemplate]):
   - Unported 3.0 Licenses (English-only)
3. **`html` field** (in the `LegalCode` model):
   - Everything else

The text that's in gettext files can be translated via Transifex at [Creative
Commons localization][cctransifex]. For additional information on the Django
translation domains / Transifex resources, see [How the license translation is
implemented](#how-the-tool-translation-is-implemented), below.

Documentation:
- [Models | Django documentation | Django][djangomodels]
- [Templates | Django documentation | Django][djangotemplates]

[namespace]: https://github.com/creativecommons/cc-legal-tools-data#legal-tools-namespace
[unportedtemplate]: templates/includes/legalcode_licenses_3.0_unported.html
[cctransifex]: https://www.transifex.com/creativecommons/public/
[djangomodels]: https://docs.djangoproject.com/en/4.2/topics/db/models/
[djangotemplates]: https://docs.djangoproject.com/en/4.2/topics/templates/


## Importing the existing legal tool text

> :warning: **This section should no longer be required and will eventually be
> moved to a better location.**

Note that once the site is up and running in production, the data in the site
will become the canonical source, and the process described here should not
need to be repeated after that.

The implementation is the Django management command `load_html_files`, which
reads from the legacy HTML legal code files in the
[creativecommons/cc-legal-tools-data][repodata] repository, and populates the
database records and translation files.

`load_html_files` uses [BeautifulSoup4][bs4docs] to parse the legacy HTML legal
code:
1. `import_zero_license_html()` for CC0 Public Domain tool
   - HTML is handled specifically (using tag ids and classes) to populate
     translation strings and to be used with specific HTML formatting when
     displayed via template
2. `import_by_40_license_html()` for 4.0 License tools
   - HTML is handled specifically (using tag ids and classes) to populate
     translation strings and to be used with specific HTML formatting when
     displayed via a template
3. `import_by_30_unported_license_html()` for unported 3.0 License tools
   (English-only)
   - HTML is handled specifically to be used with specific HTML formatting
     when displayed via a template
4. `simple_import_license_html()` for everything else
   - HTML is handled generically; only the title and license body are
     identified. The body is stored in the `html` field of the
     `LegalCode` model

[bs4docs]: https://www.crummy.com/software/BeautifulSoup/bs4/doc/
[repodata]: https://github.com/creativecommons/cc-legal-tools-data


### Import Process

> :warning: **This section should no longer be required and will eventually be
> moved to a better location.**

This process will read the HTML files from the specified directory, populate
`LegalCode` and `Tool` models, and create the `.po` portable object Gettext
files in [creativecommons/cc-legal-tools-data][repodata].

1. Ensure the [Data Repository](#data-repository), above, is in place
2. Ensure [Docker Compose Setup](#docker-compose-setup), above, is complete
3. Clear data in the database
    ```shell
    docker compose exec app ./manage.py clear_license_data
    ```
4. Load legacy HTML in the database
    ```shell
    docker compose exec app ./manage.py load_html_files
    ```
5. Optionally (and only as appropriate):
   1. Commit the `.po` portable object Gettext file changes in
      [creativecommons/cc-legal-tools-data][repodata]
   2. [Translation Update Process](#translation-update-process), below
   3. [Generate Static Files](#generate-static-files), below

[repodata]:https://github.com/creativecommons/cc-legal-tools-data


### Import Dependency Documentation

> :warning: **This section should no longer be required and will eventually be
> moved to a better location.**

- [Beautiful Soup Documentation — Beautiful Soup 4 documentation][bs4docs]
  - [lxml - Processing XML and HTML with Python][lxml]
- [Quick start guide — polib documentation][polibdocs]

[bs4docs]: https://www.crummy.com/software/BeautifulSoup/bs4/doc/
[lxml]: https://lxml.de/
[polibdocs]: https://polib.readthedocs.io/en/latest/quickstart.html


## Translation

To upload/download translation files to/from Transifex, you'll need an account
there with access to these translations. Then follow the [Authentication -
Transifex API v3][transauth]: to get an API token, and set
`TRANSIFEX["API_TOKEN"]` in your environment with its value.

The [creativecommons/cc-legal-tools-data][repodata] repository must be cloned
next to this `cc-legal-tools-app` repository. (It can be elsewhere, then you
need to set `DATA_REPOSITORY_DIR` to its location.) Be sure to clone using a
URL that starts with `git@github...` and not `https://github...`, or you won't
be able to push to it. Also see [Data Repository](#data-repository), above.

In production, the `check_for_translation_updates` management command should be
run hourly. See [Check for Translation
Updates](#check-for-translation-updates), below.

Also see [Publishing changes to git repo](#publishing-changes-to-git-repo),
below.

[Babel][babel] is used for localization information.

Documentation:
- [Babel — Babel documentation][babel]
- [Translation | Django documentation | Django][djangotranslation]

[babel]: http://babel.pocoo.org/en/latest/index.html
[repodata]:https://github.com/creativecommons/cc-legal-tools-data
[transauth]: https://transifex.github.io/openapi/index.html#section/Authentication


### How the tool translation is implemented

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


### Check for Translation Updates

> :warning: **This functionality is currently disabled.**

The hourly run of `check_for_translation_updates` looks to see if any of the
translation files in Transifex have newer last modification times than we know
about. It performs the following process (which can also be done manually:

1. Ensure the [Data Repository](#data-repository), above, is in place
2. Within the [creativecommons/cc-legal-tools-data][repodata] (the [Data
   Repository](#data-repository)):
   1. Checkout or create the appropriate branch.
      - For example, if a French translation file for BY 4.0 has changed, the
        branch name will be `cc4-fr`.
   2. Download the updated `.po` portable object Gettext file from Transifex
   3. Do the [Translation Update Process](#translation-update-process) (below)
      - _This is important and easy to forget,_ but without it, Django will
        keep using the old translations
   4. Commit that change and push it upstream.
3. Within this `cc-legal-tools-app` repository:
   1. For each branch that has been updated, [Generate Static
      Files](#generate-static-files) (below). Use the options to update git and
      push the changes.

[repodata]:https://github.com/creativecommons/cc-legal-tools-data


### Check for Translation Updates Dependency Documentation

- [GitPython Documentation — GitPython documentation][gitpythondocs]
- [Requests: HTTP for Humans™ — Requests documentation][requestsdocs]

[gitpythondocs]: https://gitpython.readthedocs.io/en/stable/index.html
[requestsdocs]: https://docs.python-requests.org/en/master/


### Translation Update Process

This Django Admin command must be run any time the `.po` portable object
Gettext files are created or changed.

1. Ensure the [Data Repository](#data-repository), above, is in place
2. Ensure [Docker Compose Setup](#docker-compose-setup), above, is complete
3. Compile translation messages (update the `.mo` machine object Gettext files)
    ```shell
    docker compose exec app ./manage.py compilemessages
    ```


## Generate Static Files

Generating static files updates the static files in the `docs/` directory of
the [creativecommons/cc-legal-tools-data][repodata] repository (the [Data
Repository](#data-repository), above).


### Static Files Process

This process will write the HTML files in the cc-legal-tools-data clone
directory under `docs/`. It will not commit the changes (`--nogit`) and will
not push any commits (`--nopush` is implied by `--nogit`).

1. Ensure the [Data Repository](#data-repository), above, is in place
2. Ensure [Docker Compose Setup](#docker-compose-setup), above, is complete
3. Delete the contents of the `docs/` directory and then recreate/copy the
   static files it should contain:
    ```shell
    docker compose exec app ./manage.py publish -v2
    ```


### Publishing changes to git repo

When the site is deployed, to enable pushing and pulling the licenses data repo
with GitHub, create an SSH deploy key for the cc-legal-tools-data repo with
write permissions, and put the private key file (not password protected)
somewhere safe (owned by `www-data` if on a server), and readable only by its
owner (0o400). Then in settings, make `TRANSLATION_REPOSITORY_DEPLOY_KEY` be
the full path to that deploy key file.


### Publishing Dependency Documentation

- [Beautiful Soup Documentation — Beautiful Soup 4 documentation][bs4docs]
  - [lxml - Processing XML and HTML with Python][lxml]
- [GitPython Documentation — GitPython documentation][gitpythondocs]

[bs4docs]: https://www.crummy.com/software/BeautifulSoup/bs4/doc/
[gitpythondocs]: https://gitpython.readthedocs.io/en/stable/index.html
[lxml]: https://lxml.de/


## Licenses


### Code

[`LICENSE`](LICENSE): the code within this repository is licensed under the
Expat/[MIT][mit] license.

[mit]: http://www.opensource.org/licenses/MIT "The MIT License | Open Source Initiative"


### Legal Code text

[![CC0 1.0 Universal (CC0 1.0) Public Domain Dedication
button][cc-zero-png]][cc-zero]

The text of the Creative Commons public licenses (legal code) is dedicated to
the public domain under the [CC0 1.0 Universal (CC0 1.0) Public Domain
Dedication][cc-zero].

[cc-zero-png]: https://licensebuttons.net/l/zero/1.0/88x31.png "CC0 1.0 Universal (CC0 1.0) Public Domain Dedication button"
[cc-zero]: https://creativecommons.org/publicdomain/zero/1.0/


### vocabulary-theme

[![CC0 1.0 Universal (CC0 1.0) Public Domain Dedication
button][cc-zero-png]][cc-zero]

[`COPYING`](COPYING): All the code within Vocabulary is dedicated to
the public domain under the [CC0 1.0 Universal (CC0 1.0) Public Domain
Dedication][cc-zero].

[cc-zero-png]: https://licensebuttons.net/l/zero/1.0/88x31.png "CC0 1.0 Universal (CC0 1.0) Public Domain Dedication button"
[cc-zero]: https://creativecommons.org/publicdomain/zero/1.0/ "Creative Commons — CC0 1.0 Universal"


#### Normalize.css

normalize.css is licensed under the Expat/[MIT][mit] License.

[mit]: https://opensource.org/license/mit/


#### Fonts


##### Accidenz Commons

[Accidenz Commons][accidenzcommons] by Archetypo is licensed under the [Creative
Commons Attribution-ShareAlike 4.0 International (CC BY-SA 4.0)
License][ccbysa40].

[accidenzcommons]: https://creativecommons.org/2019/10/28/accidenz-commons-open-licensed-font/
[ccbysa40]: https://creativecommons.org/licenses/by-sa/4.0/


##### JetBrains Mono

[JetBrains Mono][jetbrainsmono] is licensed under the [OFL-1.1 License][ofl].

[jetbrainsmono]: https://www.jetbrains.com/lp/mono/
[ofl]: https://github.com/JetBrains/JetBrainsMono/blob/master/OFL.txt


##### Roboto Condensed

[Roboto Condensed][robotocondensed] by Christian Robertson is licensed under
the [Apache License, Version 2.0][apache20].

[robotocondensed]: https://fonts.google.com/specimen/Roboto+Condensed
[apache20]: http://www.apache.org/licenses/LICENSE-2.0


##### Source Sans Pro

[Source Sans Pro][sourcesanspro] by Paul D. Hunt is licensed under the [Open
Font License][oflsil].

[sourcesanspro]: https://fonts.adobe.com/fonts/source-sans
[oflsil]: https://scripts.sil.org/cms/scripts/page.php?site_id=nrsi&id=OFL


##### Vocabulary Icons

Vocabulary Icons use icons from [Font Awesome][fontawesome] which are licensed
under the [Creative Commons Attribution 4.0 International (CC BY 4.0)
License][ccbysa40].

[fontawesome]: https://fontawesome.com/
[ccby40]: https://creativecommons.org/licenses/by/4.0/
