# cc-legal-tools-app

**Creative Commons (CC) Legal Tools Application.** This repository contains the
application that manages the licenses and public domain declarations (static
HTML, internationalization and localization files, etc.). It consumes and
generates data in the [creativecommons/cc-legal-tools-data][repodata]
repository.

[repodata]:https://github.com/creativecommons/cc-legal-tools-data


## Not the live site

This project is not intended to serve the license and deed pages directly.
Though if it's deployed on a public server it could do that, performance would
probably not be acceptable.

Instead, a command line tool can be used to save all the rendered HTML pages
for deeds and legal code as files. Then those files are used as part of the
real creativecommons.org site, just served as static files. See details farther
down.

For the parent project for the entire creativecommons.org site (of which this
project is a component, see
[creativecommons/project_creativecommons.org][project_cc].

[project_cc]: https://github.com/creativecommons/project_creativecommons.org


## Software Versions

- [Python 3.9][python39] (For parity with Debian GNU/Linux 11 [bullseye])
- [Django 3.2][django32]

Both versions are specified in the [`Pipfile`](Pipefile).

[python39]: https://docs.python.org/3.9/
[django32]: https://docs.djangoproject.com/en/3.2/


## Setting up the Project


### Data Repository

The [creativecommons/cc-legal-tools-data][repodata] project repository should
be cloned into a directory adjacent to this one:
```
PARENT_DIR
├── cc-legal-tools-app
└── cc-legal-tools-data
```

If it is not cloned into the default location,  the Django
`DATA_REPOSITORY_DIR` django configuration setting, or the
`DATA_REPOSITORY_DIR` environment variable can be used to configure its
location.

[repodata]:https://github.com/creativecommons/cc-legal-tools-data


### Docker Compose Setup

Use the following instructions to start the project with Docker compose.

1. Initial Setup
   1. Ensure the [Data Repository](#data-repository), above,  is in place
   2. Install Docker ([Install Docker Engine | Docker
      Documentation][installdocker]) and Docker Compose ([Install Docker
      Compose | Docker Documentation][installcompose])
   3. Create Django local settings file
        ```
        cp cc_legal_tools/settings/local.example.py cc_legal_tools/settings/local.py
        ```
   4. Build the containers
        ```
        docker-compose build
        ```
   5. Run database migrations
        ```
        docker-compose exec app ./manage.py migrate
        ```
   6. Clear data in the database
        ```
        docker-compose exec app ./manage.py clear_license_data
        ```
   7. Load legacy HTML in the database
        ```
        docker-compose exec app ./manage.py load_html_files
        ```
2. Run the containers
    ```
    docker-compose up
    ```

The commands above will create two docker containers:
1. **app** ([127.0.0.1:8000](http://127.0.0.1:8000/)): this Djano application
   - Any changes made to Python will be detected and rebuilt transparently as
     long as the development server is running.
2. **static** ([127.0.0.1:8080](http://127.0.0.1:8080/)): a static web server
   serving [creativecommons/cc-legal-tools-data][repodata]/docs.

[installdocker]: https://docs.docker.com/engine/install/
[installcompose]: https://docs.docker.com/compose/install/
[repodata]:https://github.com/creativecommons/cc-legal-tools-data


### Manual Setup

1. Development Environment
   1. Ensure the [Data Repository](#data-repository), above,  is in place
   2. Install dependencies
      - Linux:
        ```
        sudo apt-get install python3.9 python3.9-dev python3-pip
        ```
        ```
        pip3 install pipenv
        ```
      - macOS: via [Homebrew](https://brew.sh/):
        ```
        brew install pipenv python@3.9
        ```
   3. Install Python environment and modules via pipenv to create a
      virtualenv
      - Linux:
        ```
        pipenv install --dev --python /usr/bin/python3.9
        ```
      - macOS: via [Homebrew](https://brew.sh/):
        ```
        pipenv install --dev --python /usr/local/opt/python@3.9/libexec/bin/python
        ```
   4. Install pre-commit hooks
    ```
    pipenv run pre-commit install
    ```
2. Configure Django
   1. Create Django local settings file
    ```
    cp cc_legal_tools/settings/local.example.py cc_legal_tools/settings/local.py
    ```
   2. Create project database
      - Linux:
        ```
        sudo createdb -E UTF-8 cc_legal_tools
        ```
      - macOS:
        ```
        createdb -E UTF-8 cc_legal_tools
        ```
   4. Load database schema
    ```
    pipenv run ./manage.py migrate
    ```
3. Run development server ([127.0.0.1:8000](http://127.0.0.1:8000/))
    ```
    pipenv run ./manage.py runserver
    ```
   - Any changes made to Python will be detected and rebuilt transparently as
     long as the development server is running.


### Manual Commands

**NOTE:** The rest of the documentation assumes Docker. If you are using a
manual setup, use `pipenv run` instead of `docker-compose exec app` for the
commands below.


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

Esoteric and dangerous:
- `./dev/concatenatemessages.sh` - Concatenate legacy ccEngine translations
  into cc-legal-tools-app
  - rarely used (only after source strings are updated)
- `./dev/resetdb.sh` - Reset Django application database data (!!DANGER!!)
  - usually only helpful if you're doing model/schema work
- `./dev/updatemessages.sh` - Run Django Management nofuzzy_makemessages with
  helpful options (including excluding legalcode) and compilemessages


#### Coverage Tests and Report

The coverage tests and report are run as part of pre-commit and as a GitHub
Action. To run it manually:
1. Ensure the [Data Repository](#data-repository), above,  is in place
2. Ensure [Docker Compose Setup](#docker-compose-setup), above,  is complete
2. Coverage test
    ```
    docker-compose exec app coverage run manage.py test --noinput --keepdb
    ```
3. Coverage report
    ```
    docker-compose exec app coverage report
    ```


### Commit Errors


#### Error building trees

If you encounter an `error: Error building trees` error from pre-commit when
you commit, try adding your files (`git add <FILES>`) prior to committing them.


## Data

The legal tools metadata is in a database. The metadata tracks which legal
tools exist, their translations, their ports, and their characteristics like
what they permit, require, and prohibit.

The metadata can be downloaded by visiting URL path:
`127.0.0.1:8000`[`/licenses/metadata.yaml`][metadata]

[metadata]: http://127.0.0.1:8000/licenses/metadata.yaml

There are two main models (Django terminology for tables) in
[`legal_tools/models.py`](legal_tools/models.py):
1. `LegalCode`
2. `Tool`

A Tool can be identified by a `unit` (ex. `by`, `by-nc-sa`, `devnations`) which
is a proxy for the complete set of permissions, requirements, and prohibitions;
a `version` (ex. `4.0`, `3.0)`, and an optional `jurisdiction` for ports. So we
might refer to the tool by it's **identifier** "BY 3.0 AM" which would be the
3.0 version of the BY license terms as ported to the Armenia jurisdiction. For
additional information see: [**Legal Tools Namespace** -
creativecommons/cc-legal-tools-data: CC Legal Tools Data (static HTML, language
files, etc.)][namespace].

There are three places legal code text could be:
1. **gettext files** (`.po` and `.mo`) in the
   [creativecommons/cc-legal-tools-data][repodata] repository (legal tools with
   full translation support):
   - 4.0 Licenses
   - CC0
2. **django template**
   ([`legalcode_licenses_3.0_unported.html`][unportedtemplate]):
   - Unported 3.0 Licenses (English-only)
3. **`html` field** (in the `LegalCode` model):
   - Everything else

The text that's in gettext files can be translated via Transifex at [Creative
Commons localization][cctransifex]. For additional information the Django
translation domains / Transifex resources, see [How the license translation is
implemented](#how-the-tool-translation-is-implemented), below.

Documentation:
- [Models | Django documentation | Django][djangomodels]
- [Templates | Django documentation | Django][djangotemplates]

[namespace]: https://github.com/creativecommons/cc-legal-tools-data#legal-tools-namespace
[unportedtemplate]: templates/includes/legalcode_licenses_3.0_unported.html
[cctransifex]: https://www.transifex.com/creativecommons/public/
[djangomodels]: https://docs.djangoproject.com/en/3.2/topics/db/models/
[djangotemplates]: https://docs.djangoproject.com/en/3.2/topics/templates/


## Importing the existing legal tool text

The process of getting the text into the site varies by legal tool.

Note that once the site is up and running in production, the data in the site
will become the canonical source, and the process described here should not
need to be repeated after that.

The implementation is the Django management command `load_html_files`, which
reads from the legacy HTML legal code files in the
[creativecommons/cc-legal-tools-data][repodata] repository, and populates the
database records and translation files.

`load_html_files` uses [BeautifulSoup4][bs4docs] to parse the legacy HTML legal
code:
1. `import_zero_license_html` for CC0 Public Domain tool
   - HTML is handled specificially (using tag ids and classes) to populate
     translation strings and to be used with specific HTML formatting when
     displayed via template
2. `import_by_40_license_html` for 4.0 License tools
   - HTML is handled specificially (using tag ids and classes) to populate
     translation strings and to be used with specific HTML formatting when
     displayed via a template
3. `import_by_30_unported_license_html` for unported 3.0 License tools
   (English-only)
   - HTML is handled specificially to be used with specific HTML formatting
     when displayed via a template
4. `simple_import_license_html` for everything else
   - HTML is handled generically; only the title and license body are
     identified. The body is stored in the `html` field of the
     `LegalCode` model

[bs4docs]: https://www.crummy.com/software/BeautifulSoup/bs4/doc/
[repodata]: https://github.com/creativecommons/cc-legal-tools-data


### Import Process

This process will read the HTML files from the specified directory, populate
`LegalCode` and `Tool` models, and create `.po` files in
[creativecommons/cc-legal-tools-data][repodata].

1. Ensure the [Data Repository](#data-repository), above, is in place
2. Ensure [Docker Compose Setup](#docker-compose-setup), above, is complete
3. Clear data in the database
    ```
    docker-compose exec app ./manage.py clear_license_data
    ```
4. Load legacy HTML in the database
    ```
    docker-compose exec app ./manage.py load_html_files
    ```
5. Optionally (and only as appropriate):
   1. commit `.po` file changes in
      [creativecommons/cc-legal-tools-data][repodata]
   2. [Translation Update Process](#translation-update-process), below
   3. [Generate Static Files](#generate-static-files), below

[repodata]:https://github.com/creativecommons/cc-legal-tools-data


### Import Dependency Documentation

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
next to this `cc-legal-tools-app` repository. (It can be elsewhere, then you need
to set `DATA_REPOSITORY_DIR` to its location.) Be sure to clone using a URL
that starts with `git@github...` and not `https://github...`, or you won't be
able to push to it. Also see [Data Repository](#data-repository), above.

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
[djangotranslation]: https://docs.djangoproject.com/en/3.2/topics/i18n/translation/
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
   2. Download the updated `.po` file from Transifex
   3. Do the [Translation Update Process](#translation-update-process) (below)
      - *This is important and easy to forget,* but without it, Django will
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

This Django Admin command must be run any time the `.po` files are created or
changed.

1. Ensure the [Data Repository](#data-repository), above,  is in place
2. Ensure [Docker Compose Setup](#docker-compose-setup), above,  is complete
3. Compile translation messages (update `.mo` files)
    ```
    docker-compose exec app ./manage.py compilemessages
    ```


## Generate Static Files

Generating static files updates the static files in the `doc` directory of the
[creativecommons/cc-legal-tools-data][repodata] repository (the [Data
Repository](#data-repository), above).


### Static Files Process

This process will write the HTML files in the cc-legal-tools-data clone
directory under `docs/`. It will not commit the changes (`--nogit`) and will
not push any commits (`--nopush` is implied by `--nogit`).

1. Ensure the [Data Repository](#data-repository), above,  is in place
2. Ensure [Docker Compose Setup](#docker-compose-setup), above,  is complete
3. Compile translation messages (update `.mo` files)
    ```
    docker-compose exec app ./manage.py publish --nogit --branch=main
    ```


### Publishing changes to git repo

When the site is deployed, to enable pushing and pulling the licenses data repo
with GitHub, create an ssh deploy key for the cc-legal-tools-data repo with
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


## License

- [`LICENSE`](LICENSE) (Expat/[MIT][mit] License)

[mit]: http://www.opensource.org/licenses/MIT "The MIT License | Open Source Initiative"
