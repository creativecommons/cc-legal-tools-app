# Creative Commons Licenses

Below you will find basic setup and deployment instructions for the
cc_licenses project. To begin you should have the following applications
installed on your local development system:

-   Python == 3.7
-   [pip][pip] >= 20
-   [virtualenv][virtualenv] >= 1.10
-   [virtualenvwrapper][virtualenvwrapper] >= 3.0
-   Postgres >= 9.3
-   git >= 1.7
-   pandoc == 2.10.1

[pip]: https://www.pip-installer.org/
[virtualenv]: https://www.virtualenv.org/
[virtualenvwrapper]: https://pypi.python.org/pypi/virtualenvwrapper


## Django version

The Django version configured in this template is conservative. If you
want to use a newer version, edit `requirements/base.txt`.


## Getting Started

First clone the repository from Github and switch to the new directory:

    $ git clone git@github.com:creativecommons/cc-licenses.git
    $ cd cc-licenses

To setup your local environment you can use the quickstart make target setup,
which will install Python dependencies (via pip) into a virtualenv named
"cc_licenses", configure a local django settings file, and create a database
via Postgres named "cc_licenses" with all migrations run:

    $ make setup
    $ workon cc_licenses

If you require a non-standard setup, you can walk through the manual setup
steps below making adjustments as necessary to your needs.

To setup your local environment you should create a virtualenv and install the
necessary requirements:

    # Check that you have python3.7 installed
    $ which python3.7
    $ mkvirtualenv cc_licenses -p `which python3.7`
    (cc_licenses)$ pip install -r requirements/dev.txt

Next, we'll set up our local environment variables. We use
[django-dotenv](https://github.com/jpadilla/django-dotenv) to help with this.
It reads environment variables located in a file name `.env` in the top level
directory of the project. The only variable we need to start is
`DJANGO_SETTINGS_MODULE`:

    (cc_licenses)$ cp cc_licenses/settings/local.example.py cc_licenses/settings/local.py
    (cc_licenses)$ echo "DJANGO_SETTINGS_MODULE=cc_licenses.settings.local" > .env

Create the Postgres database and run the initial migrate:

    (cc_licenses)$ createdb -E UTF-8 cc_licenses
    (cc_licenses)$ python manage.py migrate

For outputting text files to work properly make sure to
[install](https://pandoc.org/installing.html) the stable release of pandoc at
version 2.10.1.

If you want to use [Travis](http://travis-ci.org) to test your project, rename
`project.travis.yml` to `.travis.yml`, overwriting the `.travis.yml` that
currently exists. (That one is for testing the template itself.) The setup
command does this for you:

    (cc_licenses)$ mv project.travis.yml .travis.yml


## Development

You should be able to run the development server via:

    (cc_licenses)$ python manage.py runserver

Or, on a custom port and address:

    (cc_licenses)$ python manage.py runserver 0.0.0.0:8001

Any changes made to Python will be detected and rebuilt transparently as
long as the development server is running.


## Not the live site

This project is not intended to serve the license and deed pages directly.
Though if it's deployed on a public server it could do that, performance would
probably not be acceptable.

Instead, a command line tool can be used to save all the rendered HTML pages
for licenses and deeds as files. Then those files are used as part of the real
creativecommons.org site, just served as static files. See details farther
down.


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


## Running the import

First, clean up any old data in the database by running:

    python manage.py clear_license_data

Then, clone [creativecommons/creativecommons.org][[repoccorg]] and
[creativecommons/cc-licenses-data][repodata] next to this repo.

Then run:

    python manage.py load_html_files ../creativecommons.org/docroot/legalcode

It will read the HTML files from the specified directory, populate the database
with LegalCode and License records, and create .po and .mo files in
cc-licenses-data.

Once you've done that, you might want to update the static HTML files
for the site; see "Saving the site as static files" farther on.

Now commit the changes from cc-licenses-data and push to Github.

It's simplest to do this part on a development machine. It gets too complicated
trying to run on the server and authenticate properly to GitHub from the
command line.

[repoccorg]: https://github.com/creativecommons/creativecommons.org
[repodata]:https://github.com/creativecommons/cc-licenses-data


## Translation

To upload/download translation files to/from Transifex, you'll need an account
there with access to these translations. Then follow [these
instructions](https://docs.transifex.com/api/introduction#authentication) to
get an API token, and set TRANSIFEX_API_TOKEN in your environment with its
value.

The cc-licenses-data repo should be cloned next to the cc-licenses repo.  (It
can be elsewhere, then you need to set TRANSLATION_REPOSITORY_DIRECTORY to its
location.) Be sure to clone using a URL that starts with `git@github...` and
not `https://github...`, or you won't be able to push to it.

When the site is deployed, to enable pushing and pulling the licenses data repo
with Github, create an ssh deploy key for the cc-licenses-data repo with write
permissions, and put the private key file (not password protected) somewhere
safe, owned by www-data, and readable only by its owner (0o400). Then in
settings, make TRANSLATION_REPOSITORY_DEPLOY_KEY be the full path to that
deploy key file.

Now arrange for "python manage.py check_for_translation_updates" to be
run hourly (with the appropriate virtualenv and env vars set).


## When translations have been updated in Transifex

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
- In cc-licenses, run "python manage.py compilemessages". *This is important
  and easy to forget,* but without it, Django will keep using the old
  translations.
- In cc-licenses-data, commit and push the changes.
- In cc-licenses, run `python manage.py publish --branch=<branchname>` (see
  farther down for more about publishing).


## How the license translation is implemented

First, note that translation uses two sets of files. Most things use the
built-in Django translation support. But the translation of the actual legal
text of the licenses is handled using a different set of files.

Second note: the initial implementation focuses on the 4.0 by-X, 3.0 unported,
and CC0 licenses. Others will be added as time allows.

Also note: What Transifex calls a `resource` is what Django calls a `domain`.
I'll probably use the terms interchangeably.

The translation data consists of `.po` files, and they are managed in a
separate repository from this code,
`https://github.com/creativecommons/cc-licenses-data`. This is typically
checked out beside the `cc-licenses` repo, but can be put anywhere by
changing the Django `TRANSLATION_REPOSITORY_DIRECTORY` setting, or
setting the `TRANSLATION_REPOSITORY_DIRECTORY` environment variable.

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

The .po files are initially created from the existing HTML license files by
running `python manage.py load_html_files <path to docroot/legalcode>`, where
`<path to docroot/legalcode>` is the path to the docroot/legalcode directory
where the `creativecommons.org` repo is checked out. (See also above.)

After this is done and merged to the main branch, it should not be done again.
Instead, edit the HTML license template files to change the English text, and
use Transifex to update the translation files.

Anytime `.po` files are created or changed, run `python manage.py
compilemessages` to update the `.mo` files.

> :warning: **Important:** If the `.mo` files are not updated, Django will not
> use the updated translations!


## Saving the site as static files

We've been calling this process "publishing", but that's a little
misleading, since this process does nothing to make its results visible on the
Internet. It just updates the static HTML files in the -data directory.

This is most easily done from a developer environment.

Check out the [creativecommons/cc-licenses-data][repodata] repository next to
your `cc-licenses` working tree.

Decide what branch you want to generate the site from, e.g. "develop".

In the cc-licenses-data working directory, check out that branch and make sure
it's up-to-date, e.g.:

    $ git checkout develop
    $ git pull origin develop

Then change back to the cc-licenses tree, and run the publish management
command, probably starting with "\--nopush":

    $ python manage.py publish --nopush --branch=develop

This will write the HTML files in the cc-licenses-data tree under `build` and
commit the changes, but won't push them up to GitHub. You can do that manually
after checking the results.

Alternatively you can leave off `no-push` and *if* the publish makes changes,
it'll both commit and push them. Just be aware that it won't try to push unless
it has just committed some changes, so if upstream is already behind and
running publish doesn't make any new changes, you'll still have to push
manually to get upstream updated.


## License

- [`LICENSE`](LICENSE) (Expat/[MIT][mit] License)

[mit]: http://www.opensource.org/licenses/MIT "The MIT License | Open Source Initiative"
