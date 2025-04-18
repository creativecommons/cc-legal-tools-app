# cc-legal-tools-app

**Creative Commons (CC) Legal Tools Application.** This repository contains the
application that manages the license tools and public domain tools (static
HTML, internationalization and localization files, etc.). It consumes and
generates data in the [creativecommons/cc-legal-tools-data][repodata]
repository.

[repodata]:https://github.com/creativecommons/cc-legal-tools-data

## Code of Conduct

[`CODE_OF_CONDUCT.md`][org-coc]:
> The Creative Commons team is committed to fostering a welcoming community.
> This project and all other Creative Commons open source projects are governed
> by our [Code of Conduct][code_of_conduct]. Please report unacceptable
> behavior to [conduct@creativecommons.org](mailto:conduct@creativecommons.org)
> per our [reporting guidelines][reporting_guide].

[org-coc]: https://github.com/creativecommons/.github/blob/main/CODE_OF_CONDUCT.md
[code_of_conduct]: https://opensource.creativecommons.org/community/code-of-conduct/
[reporting_guide]: https://opensource.creativecommons.org/community/code-of-conduct/enforcement/


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


## Setup and Usage

Once this project's required dependencies (Docker, Git, etc.) are enabled on
your system, you will be able to run the legal-tools application and generate
static files.

For information on learning and installing the prerequisite technologies for
this project, please see [Foundational technologies — Creative Commons Open
Source][found-tech].

[found-tech]: https://opensource.creativecommons.org/contributing-code/foundational-tech/


### Codebases Setup

Both this repository and the [creativecommons/cc-legal-tools-data][repodata]
project repository should be cloned side by side, resulting in a structure like
the following:
```
creative-commons/
├── cc-legal-tools-app/     (git clone of this repository)
└── cc-legal-tools-data/    (git clone of the cc-legal-tools-data repository)
```

To achieve this, we recommend the following procedure:

1. Create and change to a container directory, such as `creative-commons` or `cc`.
    ```shell
    mkdir creative-commons
    cd creative-commons
    ```
2. Clone both repos using SSH or, if that does not work, HTTPS protocol.
    ```shell
    git clone git@github.com:creativecommons/cc-legal-tools-app.git
    git clone git@github.com:creativecommons/cc-legal-tools-data.git
    ```
    or
    ```shell
    git clone https://github.com/creativecommons/cc-legal-tools-app.git
    git clone https://github.com/creativecommons/cc-legal-tools-data.git
    ```

Visit [Cloning a repository - GitHub Docs][gitclone] for more on how to clone a
GitHub repository.

[gitclone]:https://docs.github.com/en/repositories/creating-and-managing-repositories/cloning-a-repository


### Docker Prep and Initial Execution

Use the following instructions to prepare and run the project with Docker
Compose.

1. Ensure all prerequisites and repositories are in place.
2. Ensure you are at the top level of the directory where you cloned this
repository (where `manage.py` is).
    ```shell
    cd cc-legal-tools-app
    ```
3. Create Django local settings file from the example file.
    ```shell
    cp cc_legal_tools/settings/local.example.py cc_legal_tools/settings/local.py
    ```
    - Update variables in new file, if necessary.
    - This file is ignored by Git.
4. Build the containers.
    ```shell
    docker compose build
    ```
5. **Run the containers.**
    ```shell
    docker compose up
    ```
   1. **app** ([127.0.0.1:8005](http://127.0.0.1:8005/)): this Django
      application
      - Any changes made to Python will be detected and rebuilt
        transparently as long as the development server is running.
   2. **static** ([127.0.0.1:8006](http://127.0.0.1:8006/)): a static web
      server serving [creativecommons/cc-legal-tools-data][repodata]:`docs/`
6. Initialize data.
Open a separate terminal tab, and in the same directory, run:
    ```shell
    ./bin/init_data.sh
    ```
    1. Deletes database (which may not yet exist)
    2. Initializes database
    3. Performs database migrations
    4. Creates supseruser (will prompt for password)
    5. Loads data

Note: Once this full setup is performed, running Step 5 above will execute the
application on any subsequent occasion.


## Project Usage

With the prerequisites installed and built, these tools can be used to generate
and manage data from the associated [data repository][repodata].


### Data

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


### Translation

See [`docs/translation.md`](docs/translation.md)


### Generate Static Files

Generating static files updates the static files in the `docs/` directory of
the [creativecommons/cc-legal-tools-data][repodata] repository (the [Data
Repository](#data-repository), above).


#### Static Files Process

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


#### Publishing Changes to Git Repo

When the site is deployed, to enable pushing and pulling the licenses data repo
with GitHub, create an SSH deploy key for the cc-legal-tools-data repo with
write permissions, and put the private key file (not password protected)
somewhere safe (owned by `www-data` if on a server), and readable only by its
owner (0o400). Then in settings, make `TRANSLATION_REPOSITORY_DEPLOY_KEY` be
the full path to that deploy key file.


#### Publishing Dependency Documentation

- [Beautiful Soup Documentation — Beautiful Soup 4 documentation][bs4docs]
  - [lxml - Processing XML and HTML with Python][lxml]
- [GitPython Documentation — GitPython documentation][gitpythondocs]

[bs4docs]: https://www.crummy.com/software/BeautifulSoup/bs4/doc/
[gitpythondocs]: https://gitpython.readthedocs.io/en/stable/index.html
[lxml]: https://lxml.de/


### Machine/metadata Layer: RDF/XML

For details and history, see [`docs/rdf.md`](docs/rdf.md).


## Development

Inside the Docker container, the Python-based tooling centers around by pre-commit and Django.

See the [Code of Conduct](#code-of-conduct) above and the [Code of Conduct document][code_of_conduct] for more information on participant expectations and responsibilities.


### Contributing

See [`CONTRIBUTING.md`][org-contrib].

[org-contrib]: https://github.com/creativecommons/.github/blob/main/CONTRIBUTING.md


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


### Software Versions

These are the currently designated versions of the various dependencies:
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


### Developer Resources

These resources are available for developing this tooling:
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


> :information_source: The rest of the documentation assumes Docker. If you are
> using a manual setup, use `pipenv run` instead of `docker compose exec app`
> for the commands below.


### Helper Scripts

Best run before every commit:
- `./bin/coverage.sh` - Run coverage tests and report
- `./bin/tools.sh` - Run Python code tools (isort, black, flake8)

Run as needed:
- `./bin/copy_theme.sh` - Copy the portions of
  [creativecommons/vocabulary-theme][vocab-theme] needed for local development
  - Run after each new release of
    [creativecommons/vocabulary-theme][vocab-theme]

Data management:
- `./bin/dump_data.sh` - Dump Django application data
- `./bin/init_data.sh` - :warning: Initialize Django application data
- `./bin/load_data.sh` - Load Django application data

Esoteric and dangerous:
- `./bin/updatemessages.sh` - :warning: Run Django Management
  nofuzzy_makemessages with helpful options (including excluding legalcode) and
  compilemessages

[vocab-theme]: https://github.com/creativecommons/vocabulary-theme


### Coverage Tests and Report

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


#### Error Building Trees

If you encounter an `error: Error building trees` error from pre-commit when
you commit, try adding your files (`git add <FILES>`) before committing them.


## Frontend Dependencies

The following CC projects are used to achieve a consistent look and feel:
- [creativecommons/vocabulary-theme][vocabulary-theme]: WordPress Theme
  implementation of the Vocabulary design system

[vocabulary-theme]: https://github.com/creativecommons/vocabulary-theme


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


### Vocabulary Theme

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
