# Creative Commons Licenses


## Software Versions

The Django version configured in this template is conservative. If you
want to use a newer version, edit `Pipfile`.

Python version 3.7 is used for parity with Debian GNU/Linux 10 (buster).


## Not the live site

This project is not intended to serve the license and deed pages directly.
Though if it's deployed on a public server it could do that, performance would
probably not be acceptable.

Instead, a command line tool can be used to save all the rendered HTML pages
for licenses and deeds as files. Then those files are used as part of the real
creativecommons.org site, just served as static files. See details farther
down.


## Setting up the Project


### Data Repository

The [creativecommons/cc-licenses-data][repodata] project repository must be
cloned into a directory adjacent to this one:
```
PARENT_DIR
├── cc-licenses
└── cc-licenses-data
```

[repodata]:https://github.com/creativecommons/cc-licenses-data


### Docker Compose Setup

Use the following instructions to start the project with Docker compose.

1. Initial Setup
   1. Ensure the [Data Repository](#data-repository) is in place
   2. Install Docker ([Install Docker Engine | Docker Documentation][installdocker])
   3. Create Django local settings file
        ```shell
        cp cc_licenses/settings/local.example.py cc_licenses/settings/local.py
        ```
   4. Build the containers
        ```shell
        docker-compose build
        ```
   5. Run database migrations
        ```shell
        docker-compose run app ./manage.py migrate
        ```
   6. Clear data in the database
        ```shell
        docker-compose run app ./manage.py clear_license_data
        ```
   7. Load legacy HTML in the database
        ```shell
        docker-compose run app ./manage.py load_html_files ../cc-licenses-data/legacy/legalcode
        ```
2. Run the containers
    ```shell
    docker-compose up
    ```

The commands above will create 3 docker containers:
1. **app** ([127.0.0.1:8000](http://127.0.0.1:8000/)): this Djano application
   - Any changes made to Python will be detected and rebuilt transparently as
     long as the development server is running.
2. **db**: PostgreSQL database backend for this Django application
3. **static** ([127.0.0.1:8080](http://127.0.0.1:8080/)): a static web server
   serving [creativecommons/cc-licenses-data][repodata]/docs.

[installdocker]: https://docs.docker.com/engine/install/
[repodata]:https://github.com/creativecommons/cc-licenses-data


### Manual Setup

1. Development Environment
   1. Ensure the [Data Repository](#data-repository) is in place
   2. Install dependencies
      - Linux:
        ```shell
        sudo apt-get install pandoc postgresql postgresql-contrib python3.7 python3.7-dev python3-pip
        ```
        ```shell
        pip3 install pipenv
        ```
      - macOS: via [Homebrew](https://brew.sh/):
        ```shell
        brew install pandoc pipenv postgresql python@3.7
        ```
   3. Install Python 3.7 environment and modules via pipenv to create a
      virtualenv
      - Linux:
        ```shell
        pipenv install --dev --python /usr/bin/python3.7
        ```
      - macOS: via [Homebrew](https://brew.sh/):
        ```shell
        pipenv install --dev --python /usr/local/opt/python@3.7/libexec/bin/python
        ```
   4. Install pre-commit hooks
    ```shell
    pipenv run pre-commit install
    ```
2. Configure Django and PostgreSQL
   1. Create Django local settings file
    ```shell
    cp cc_licenses/settings/local.example.py cc_licenses/settings/local.py
    ```
   2. Start PostgrSQL server
      - It's completely fine to not make a specific postgresql account. But if
        you do wish to create a different user account for the project, Please
        refer to the official documentation.
        https://www.postgresql.org/docs/current/tutorial-install.html
      - Linux:
        ```shell
        sudo service postgresql start
        ```
      - macOS:
        ```shell
        brew services run postgres
        ```

   3. Create project database
      - Linux:
        ```shell
        sudo createdb -E UTF-8 cc_licenses
        ```
      - macOS:
        ```shell
        createdb -E UTF-8 cc_licenses
        ```
   4. Load database schema
    ```shell
    pipenv run ./manage.py migrate
    ```
3. Run development server ([127.0.0.1:8000](http://127.0.0.1:8000/))
    ```shell
    pipenv run ./manage.py runserver
    ```
   - Any changes made to Python will be detected and rebuilt transparently as
     long as the development server is running.


### Manual Commands

**NOTE:** The rest of the documentation assumes Docker. If you are using a
manual setup, use `pipenv run` instead of `docker-compose run web` for the
commands below.


### Tooling

- **[Python Guidelines — Creative Commons Open Source][ccospyguide]**
- [Black][black]: the uncompromising Python code formatter
- [Coverage.py][coveragepy]: Code coverage measurement for Python
- [flake8][flake8]: a python tool that glues together pep8, pyflakes, mccabe,
  and third-party plugins to check the style and quality of some python code.
- [isort][isort]: A Python utility / library to sort imports.
- [pre-commit][precommit]: A framework for managing and maintaining
  multi-language pre-commit hooks.

[ccospyguide]: https://opensource.creativecommons.org/contributing-code/python-guidelines/
[black]: https://github.com/psf/black
[coveragepy]: https://github.com/nedbat/coveragepy
[flake8]: https://gitlab.com/pycqa/flake8
[isort]: https://pycqa.github.io/isort/
[precommit]: https://pre-commit.com/


#### Coverage Tests and Report

The coverage tests and report are run as part of pre-commit and as a GitHub
Action. To run it manually:
1. Ensure the [Data Repository](#data-repository) is in place
2. Ensure [Docker Compose Setup](#docker-compose-setup) is complete
2. Coverage test
    ```shell
    docker-compose run app coverage run manage.py test --noinput --keepdb
    ```
3. Coverage report
    ```shell
    docker-compose run app coverage report
    ```


### Commit Errors


#### Error building trees

If you encounter an `error: Error building trees` error from pre-commit when
you commit, try adding your files (`git add <FILES>`) prior to committing them.


## Data

The license data is stored as follows.

The license metadata is in a database. The metadata tracks which licenses
exist, their translations, their ports, and their characteristics like what
they permit, require, and prohibit.

The metadata can be downloaded by visiting URL path: /licenses/metadata.yaml

There are two main models (that's Django terminology for tables).

A License can be identified by a license code (e.g. BY, BY-NC-SA) which is a
proxy for the complete set of permissions, requirements, and prohibitions; a
version number (e.g. 4.0, 3.0), and an optional jurisdiction for ports. So we
might refer to the license "BY 3.0 Armenia" which would be the 3.0 version of
the BY license terms as ported to the Armenia jurisdiction.

A License can exist in multiple languages or translations. Each one, including
English, is represented by a LegalCode record. A LegalCode is identified by a
license and a language, e.g. we might refer to the "BY 3.0 Armenia in Armenian"
legalcode record.

Right now there are three places the text of licenses could be.

For licenses that we are translating, like BY 4.0 and CC0, the text is in
gettext files (.po and .mo) in the cc-licenses-data repository.

For the 3.0 unported licenses that are English-only, the text is in a Django
template.

For the 3.0 ported licenses, we've just got the HTML in the database in the
LegalCode records, and insert it as-is into the page.

The text that's in gettext files can be translated via transifex at [Creative
Commons localization][transifex]. The resources there are named for the license
they contain text for. Examples: "CC0 1.0" or "CC BY-NC-ND 4.0".

[transifex]: https://www.transifex.com/creativecommons/CC/


## Importing the existing license text

The process of getting the text into the site varies by license.

Note that once the site is up and running in production, the data in the site
will become the canonical source, and the process described here should not
need to be repeated after that.

The implementation is the Django management command `load_html_files`, which
reads from the existing HTML files in the creativecommons.org repository, and
populates the database records and translation files.

`load_html_files` has custom code for each flavor of license. There's a method
to parse BY\* 4.0 HTML files, another for CC0, another for BY\* 3.0 unported
files, and another for BY\* 3.0 ported. We would expect to add more such
methods for other license flavors.

Each parsing method uses BeautifulSoup4 to parse the HTML text into a tree
representing the structure of the HTML, and picks out the part of the page that
contains the license (as opposed to navigation, styling, and boilerplate text
that occurs on many pages). Then it uses tag id's and classes and the structure
of the HTML to pick out the text for each part of the license (generally a
translatable phrase or paragraph) and organize it into translation files, or
for the ported 3.0 licenses, just pretty-prints the HTML and saves it as-is.

The BY\* 4.0 licenses are the most straightforward. The text is the same from
one license to the next (e.g. BY-NC, BY-SA) except where the actual license
terms are different, and even then, the text specific to particular terms, say
"NC", are pretty much the same in the licenses that have those terms.

That means we were able to create a single Django HTML template to render any
BY\* 4.0 license, using conditionals to include or vary parts of the text as
needed.

The regularity of these licenses extends to the translated versions, so the
English text in the Django template is marked for translation as usual in
Django, and Django can substitute the appropriate translated text for each
message as the page is rendered.

CC0 (the public domain "license") works similarly.

The 3.0 licenses are more complicated due to ports and less consistency
in general.

The unported (international) 3.0 licenses are not translated, and do have
enough regularity that it was possible to create a single Django template to
render the 3.0 unported licenses. Since these are not translated, and there's
no expectation that they ever will be, the template just has the English text
in it, not marked for translation.

The ported 3.0 licenses are too varied to do something like that. Each port can
have arbitrary differences from the unported version, so trying to capture
those differences as conditionals in a template would be nearly impossible, and
certainly unmanageable. As for translations, some of the ports do have multiple
languages, although many don't have an English translation at all.

So for the ported 3.0 licenses, at least for now, it was decided to just
extract the part of the existing HTML pages that had the actual license text
and store it in the LegalCode objects representing those ports in those
languages. There is a template for 3.0 ported licenses, but it basically just
inserts whatever HTML we've saved into the page.

The older version licenses have not yet been looked at. Hopefully we can model
importing those licenses on how we've done the 3.0 licenses.


#### Import Process

This process will read the HTML files from the specified directory, populate
the database with LegalCode and License records, and create `.po` and `.mo`
files in [creativecommons/cc-licenses-data][repodata].

Once you've done that, you might want to update the static HTML files
for the site; see "Saving the site as static files" farther on.

Now commit the changes from cc-licenses-data and push to GitHub.

It's simplest to do this part on a development machine. It gets too complicated
trying to run on the server and authenticate properly to GitHub from the
command line.

1. Ensure the [Data Repository](#data-repository) is in place
2. Ensure [Docker Compose Setup](#docker-compose-setup) is complete
3. Clear data in the database
    ```shell
    docker-compose run app ./manage.py clear_license_data
    ```
4. Load legacy HTML in the database
    ```shell
    docker-compose run app ./manage.py load_html_files ../cc-licenses-data/legacy/legalcode
    ```

[repodata]:https://github.com/creativecommons/cc-licenses-data


## Translation

To upload/download translation files to/from Transifex, you'll need an account
there with access to these translations. Then follow [these
instructions](https://docs.transifex.com/api/introduction#authentication) to
get an API token, and set `TRANSIFEX_API_TOKEN` in your environment with its
value.

The cc-licenses-data repo should be cloned next to the cc-licenses repo. (It
can be elsewhere, then you need to set `DATA_REPOSITORY_DIR` to its location.)
Be sure to clone using a URL that starts with `git@github...` and not
`https://github...`, or you won't be able to push to it.

Now arrange for `docker-compose run app ./manage.py
check_for_translation_updates` to be run hourly (or the equivalent with the
appropriate virtualenv and env variarables set).

Also see [Publishing changes to git repo](#publishing-changes-to-git-repo).


### When translations have been updated in Transifex

The hourly run of `check_for_translation_updates` looks to see if any of
the translation files in Transifex have newer last modification times
than we know about. If so, it will:

- Determine which translation branch the changes should be tracked under. For
  example, if a French translation file for BY 4.0 has changed, the branch name
  will be cc4-fr.
- Check out the latest version of the cc4-fr branch in the cc-licenses-data
  repo beside the cc-licenses repo, or create a new branch from develop with
  that name.
- Download the updated translation file, compile it, and save both to
  cc-licenses-data.
- Commit that change and push it upstream.
- For each branch that has been updated, publish its static files into
  cc-licenses-data, commit, and push upstream.

If you knew that translation files in Transifex had changed, you could do the
equivalent steps manually:
- In cc-licenses-data, checkout or create the appropriate branch.
- Download the updated .po files from Transifex to the appropriate place in
  cc-licenses-data.
- In cc-licenses, run `docker-compose run app ./manage.py compilemessages`.
  *This is important and easy to forget,* but without it, Django will keep
using the old translations.
- In cc-licenses-data, commit and push the changes.
- In cc-licenses, run `docker-compose run app ./manage.py publish
  --branch=<branchname>`
  (see farther down for more about publishing).


### How the license translation is implemented

First, note that translation uses two sets of files. Most things use the
built-in Django translation support. But the translation of the actual legal
text of the licenses is handled using a different set of files.

Second note: the initial implementation focuses on the 4.0 by-X, 3.0 unported,
and CC0 licenses. Others will be added as time allows.

Also note: What Transifex calls a `resource` is what Django calls a `domain`.
I'll probably use the terms interchangeably.

The translation data consists of `.po` files, and they are managed in a
separate repository from this code
([creativecommons/cc-licenses-data][repodata]). This is typically checked out
beside the `cc-licenses` repo, but can be put anywhere by changing the Django
`DATA_REPOSITORY_DIR` setting, or setting the `DATA_REPOSITORY_DIR` environment
variable.

For the common web site stuff, and translated text outside of the actual legal
code of the licenses, the messages use the standard Django translation domain
`django`, and the resource name on Transifex for those messages is `django-po`.
These files are also in the cc-licenses-data repo, under `locale`.

For the license legal code, for each combination of license code, version, and
jurisdiction code, there's another separate domain. These are all in
cc-licenses-data under `legalcode`.

Transifex requires the resource slug to consist solely of letters, digits,
underscores, and hyphens. So we define the resource slug by joining the license
code, version, and jurisdiction with underscores (`_`), then stripping out any
periods (`.`) from the resulting string.  Examples: `by-nc_40`,
`by-nc-sa_30_es` (where `_es` represents the jurisdiction, not the
translation).

For each domain, there's a file for each translation. The files are all named
`<resourcename>.po` but are in different directories for each translated
language.

We have the following structure in our translation data repo:

    legalcode/
       <language>/
           LC_MESSAGES/
                 by_4.0.mo
                 by_4.0.po
                 by-nc_4.0.mo
                 by-nc_4.0.po
                 ...

The language code used in the path to the files is *not* necessarily the same
as what we're using to identify the licenses in the site URLs.  That's because
the language codes used by Django don't always match what the site URLs are
using, and we can't change either of them.

For example, the translated files for
`https://creativecommons.org/licenses/by-nc/4.0/legalcode.zh-Hans` are in the
`zh_Hans` directory. In this case, `zh_Hans` is what Django uses to identify
that translation.

The `.po` files are initially created from the existing HTML license files by
running `docker-compose run app ./manage.py load_html_files <path to
legacy/legalcode>`, where `<path to legacy/legalcode>` is a local path to
[creativecommons/cc-licenses-data][repodata]:
[`legacy/legalcode`][legacylegalcode] (see also above).

After this is done and merged to the main branch, it should not be done again.
Instead, edit the HTML license template files to change the English text, and
use Transifex to update the translation files.

> :warning: **Important:** If the `.mo` files are not updated, Django will not
> use the updated translations!

[repodata]:https://github.com/creativecommons/cc-licenses-data
[legacylegalcode]: https://github.com/creativecommons/cc-licenses-data/tree/main/legacy/legalcode


#### Translation Update Process

This process must be run any time the `.po` files are created or changed.

1. Ensure the [Data Repository](#data-repository) is in place
2. Ensure [Docker Compose Setup](#docker-compose-setup) is complete
3. Compile translation messages (update `.mo` files)
    ```shell
    docker-compose run app ./manage.py compilemessages
    ```


## Generate Static Files

We've been calling this process "publishing", but that's a little
misleading, since this process does nothing to make its results visible on the
Internet. It just updates the static HTML files in the -data directory.


#### Static Files Process

This process will write the HTML files in the cc-licenses-data clone directory
under `docs/`. It will not commit the changes (`--nogit`) and will not push any
commits (`--nopush` is implied by `--nogit`).

1. Ensure the [Data Repository](#data-repository) is in place
2. Ensure [Docker Compose Setup](#docker-compose-setup) is complete
3. Compile translation messages (update `.mo` files)
    ```shell
    docker-compose run app ./manage.py publish --nogit --branch=main
    ```


### Publishing changes to git repo

When the site is deployed, to enable pushing and pulling the licenses data repo
with GitHub, create an ssh deploy key for the cc-licenses-data repo with write
permissions, and put the private key file (not password protected) somewhere
safe, owned by www-data, and readable only by its owner (0o400). Then in
settings, make `TRANSLATION_REPOSITORY_DEPLOY_KEY` be the full path to that
deploy key file.


## License

- [`LICENSE`](LICENSE) (Expat/[MIT][mit] License)

[mit]: http://www.opensource.org/licenses/MIT "The MIT License | Open Source Initiative"
