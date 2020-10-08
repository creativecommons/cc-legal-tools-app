

.. EDIT the below links to use the project's github repo path. Or just remove them.

.. image:: https://requires.io/github/GITHUB_ORG/cc_licenses/requirements.svg?branch=master
.. image:: https://requires.io/github/GITHUB_ORG/cc_licenses/requirements.svg?branch=develop

Creative Commons Licenses
=========================

Below you will find basic setup and deployment instructions for the cc_licenses
project. To begin you should have the following applications installed on your
local development system:

- Python >= 3.7
- NodeJS >= 10.16
- `pip <http://www.pip-installer.org/>`_ >= 20
- `virtualenv <http://www.virtualenv.org/>`_ >= 1.10
- `virtualenvwrapper <http://pypi.python.org/pypi/virtualenvwrapper>`_ >= 3.0
- Postgres >= 9.3
- git >= 1.7

Installing the proper NodeJS versions for each of your projects can be difficult. It's probably best
to `use nvm <https://github.com/nvm-sh/nvm>`_.

Django version
------------------------

The Django version configured in this template is conservative. If you want to
use a newer version, edit ``requirements/base.txt``.

Getting Started
------------------------

First clone the repository from Github and switch to the new directory::

    $ git clone git@github.com:[ORGANIZATION]/cc_licenses.git
    $ cd cc_licenses

To setup your local environment you can use the quickstart make target `setup`, which will
install both Python and Javascript dependencies (via pip and npm) into a virtualenv named
"cc_licenses", configure a local django settings file, and create a database via
Postgres named "cc_licenses" with all migrations run::

    $ make setup
    $ workon cc_licenses

If you require a non-standard setup, you can walk through the manual setup steps below making
adjustments as necessary to your needs.

To setup your local environment you should create a virtualenv and install the
necessary requirements::

    # Check that you have python3.7 installed
    $ which python3.7
    $ mkvirtualenv cc_licenses -p `which python3.7`
    (cc_licenses)$ pip install -r requirements/dev.txt

Next, we'll set up our local environment variables. We use `django-dotenv
<https://github.com/jpadilla/django-dotenv>`_ to help with this. It reads environment variables
located in a file name ``.env`` in the top level directory of the project. The only variable we need
to start is ``DJANGO_SETTINGS_MODULE``::

    (cc_licenses)$ cp cc_licenses/settings/local.example.py cc_licenses/settings/local.py
    (cc_licenses)$ echo "DJANGO_SETTINGS_MODULE=cc_licenses.settings.local" > .env

Create the Postgres database and run the initial migrate::

    (cc_licenses)$ createdb -E UTF-8 cc_licenses
    (cc_licenses)$ python manage.py migrate

If you want to use `Travis <http://travis-ci.org>`_ to test your project,
rename ``project.travis.yml`` to ``.travis.yml``, overwriting the ``.travis.yml``
that currently exists.  (That one is for testing the template itself.)::

    (cc_licenses)$ mv project.travis.yml .travis.yml

Development
-----------

You should be able to run the development server via::

    (cc_licenses)$ python manage.py runserver

Or, on a custom port and address::

    (cc_licenses)$ python manage.py runserver 0.0.0.0:8001

Any changes made to Python will be detected and rebuilt transparently as
long as the development server is running.

Importing the existing license text
-----------------------------------

Temporarily during development, we'll be importing the translated license text
from HTML files.

First, clean up any old data by running::

    python manage.py clear_license_data

Then, clone https://github.com/creativecommons/creativecommons.org next to this repo.
Then run::

    python manage.py load_html_files ../creativecommons.org/docroot/legalcode

It will read the HTML files from the specified directory, populate the database
with LegalCode and License records, and at least for the BY 4.0 licenses, create
.po and .mo files under locale.licenses.

To clean things up ready to start over, you can run clear_license_data again.

Translation
-----------

To upload/download translation files to/from Transifex, you'll need an account
there with access to these translations.
Then follow `these instructions <https://docs.transifex.com/api/introduction#authentication>`_
to get an API token, and set TRANSIFEX_API_TOKEN in your environment with its value.

The cc-licenses-data repo should be cloned next to the cc-licenses repo. (It can
be elsewhere, then you need to set TRANSLATION_REPOSITORY_DIRECTORY to its location.)
Be sure to clone using a URL that starts with "git@github..." and not "https://github...",
or you won't be able to push to it.

To enable pushing and pulling the licenses data repo with Github, create an ssh deploy
key for the cc-licenses-data repo with write permissions, and put the private key file (not password
protected) somewhere safe, owned by www-data, and readable only by its owner (0o400).
Then in settings, make TRANSLATION_REPOSITORY_DEPLOY_KEY be the full path to that
deploy key file.

Now arrange for "python manage.py check_for_translation_updates" to be run hourly (with
the appropriate virtualenv and env vars set), probably from cron.

Importing license text initially
................................

When adding new licenses to the site, we are getting the license text into the site
by running "load_html_files" to parse the existing HTML files from the creativecommons.org
repository, both English and translations. Then we run "upload_license_messages"
to upload them to Transifex, and also add them in git::

    $ cd path-to/cc-licenses
    $ python manage.py load_html_files ...path-to-creativecommons.org/docroot/legalcode
    $ python manage.py upload_license_messages
    $ cd ../cc-licenses-data
    $ ... git commit the new .po and .mo files to whatever branch you're using ...

We then construct a template or templates using the English text, styled for the
new site, and with each piece of text to be translated marked as such. For example,
``cc_licenses/templates/includes/legalcode_40_license.html``.  That template is
passed a LegalCode object as ``legalcode`` and can use it to conditionally include
different parts of the license. This works pretty well for the 4.0 BY licenses, which
are very similar and can share one template.

Importing non-license text initially
....................................

All text in the site that is not in the licenses can be gathered using Django's
"makemessages" into django.po files, *but* we need to exclude the Django templates
that actually include the English license text, because the actual legal text is
in different .po files from the non-legal text.

That will end up looking something like::

    $ python manage.py makemessages --ignore legalcode_40_license.html [--ignore anothertemplate...]

Then we upload the English django.po files to Transifex with::

    $ tx push -r CC.django-po -s

When license translations change
................................

When license translations are changed on Transifex, the ``check_for_translation_updates``
periodic job will create a translation branch on the cc-licenses-data repo. Someone will
manually create a pull request, review the translation, and if the changes are approved,
merge the changed translation pull request.

Then someone will need to pull the updated cc-licenses-data branch from the web server,
build the updated HTML files, commit the changes, and push that back upstream so the
static files used for the production site will be up-to-date again::

    $ cd path-to/cc-licenses-data
    $ git checkout develop (or whatever the approved branch is)
    $ cd ../cc-licenses
    $ python manage.py publish --branch_name develop (or whatever the approved branch is)
    $ cd ../cc-licenses-data
    $ ... git add, commit, push

When non-license translations change
....................................

There's other text on the site, like the deed page, navigation, button text, etc etc.
Those are in the "django-po" resource on Transifex. When those translations have
changed, someone should create a new branch in their cc-licenses-data working tree,
then from cc-licenses, "tx pull -r CC.django-po", which will update the .po files
in cc-licenses-data. Then run "python manage.py compilemessages" to compile the .po
files to .mo files in cc-licenses-data. Now commit the changes, push the branch and
open a pull request. When the pull request is merged, repeat the steps from above of
pulling cc-licenses-data, building the static files, committing the updated HTML files,
and pushing::

    $ cd path-to/cc-licenses-data
    $ git checkout -b new-branch-name
    $ cd ../cc-licenses
    $ tx pull -r CC.django-po
    $ python manage.py compilemessages
    $ cd ../cc-licenses-data
    $ git add locale
    $ git commit -m "Commit message..."
    $ git push

Note that we ONLY include changes under "locale". Transifex might pull down some
changes under "legalcode" but we want to ignore those for this particular operation.
Just commit the changes under "locale".

When license text changes
.........................

If the English text of a license changes (seems unlikely, but possible)... we need to
figure out what to do. "compilemessages" isn't flexible enough to update the right
.po files.

If this is really rare, it might be sufficient to manually edit the affected English
.po files, then push those .po files to
Transifex for the translators to update their translations. From there, the
*when license translations change* workflow should apply.

When non-license text changes
.............................

If non-license English text changes, just repeat *Importing non-license text initially*.

Deployment
----------

There are different ways to deploy, and `this document <http://caktus.github.io/developer-documentation/deploy-strategies.html>`_ outlines a few of them that could be used for cc_licenses.

Deployment with fabric
......................

We use a library called `fabric <http://www.fabfile.org/>`_ as a wrapper around a lot of our deployment
functionality. However, deployment is no longer fully set up in this template, and instead you'll need
to do something like set up `Tequila <https://github.com/caktus/tequila>`_ for your project. Currently,
best way to do that is to copy the configuration from an existing project. Once that is done, and the
servers have been provisioned, you can deploy changes to a particular environment with the ``deploy``
command::

    $ fab staging deploy

Deployment with Dokku
.....................

Alternatively, you can deploy the project using Dokku. See the
`Caktus developer docs <http://caktus.github.io/developer-documentation/dokku.html>`_.

How the license translation is implemented
------------------------------------------

First, note that translation uses two sets of files. Most things use the built-in
Django translation support. But the translation of the actual legal text of the licenses
is handled using a different set of files.

Second note: the initial implementation focuses on the 4.0 by-*
licenses. Others will be added as time allows.

Also note: What Transifex calls a ``resource`` is what Django
calls a ``domain``. I'll probably use the terms interchangeably.

The translation data consists of ``.po`` files, and they are managed in a separate
repository from this code, ``https://github.com/creativecommons/cc-licenses-data``.
This is typically checked out beside the ``cc-licenses`` repo, but can be put
anywhere by changing the Django ``TRANSLATION_REPOSITORY_DIRECTORY`` setting,
or setting the ``TRANSLATION_REPOSITORY_DIRECTORY`` environment variable.

For the common web site stuff, and translated text outside of the actual legal
code of the licenses, the messages use the standard Django translation
domain ``django``, and the resource name on Transifex for those messages is
``django-po``. These files are also in the cc-licenses-data repo.

For the license legal code, for each combination of license code, version, and
jurisdiction code, there's another separate domain.

Transifex requires the resource slug to consist solely of letters, digits, underscores,
and hyphens. So we define the resource slug by joining the license code,
version, and jurisdiction with underscores (``_``), then stripping out any periods
(``.``) from the resulting string. Examples: ``by-nc_40``, ``by-nc-sa_30_es``
(where ``_es`` represents the jurisdiction, not the translation).

For each domain, there's a file for each translation.
The files are all named ``<resourcename>.po`` but are in different directories
for each translated language.

We have the following structure in our translation data repo::

    legalcode/
       <language>/
           LC_MESSAGES/
                 by_4.0.mo
                 by_4.0.po
                 by-nc_4.0.mo
                 by-nc_4.0.po
                 ...

The language code used in the path to the files is *not* necessarily
the same as what we're using to identify the licenses in the
URLs. Good example? The translated files for
``https://creativecommons.org/licenses/by-nc/4.0/legalcode.zh-Hans``
are in the ``zh_Hans`` directory. That's because ``zh_Hans`` is what
Django uses to identify that translation.

The .po files are initially created from the existing HTML license files
by running
``python manage.py load_html_files <path to docroot/legalcode>``
where ``<path to docroot/legalcode>`` is the path to
the docroot/legalcode directory where the ``creativecommons.org``
repo is checked out. (See also above.)

After this is done and merged to the main branch, it should not be
done again. Instead, edit the HTML license template files to change
the English text, and use Transifex to update the translation files.

Anytime ``.po`` files are created or changed, run
``python manage.py compilemessages`` to update the ``.mo`` files.

.. important:: If the ``.mo`` files are not updated, Django will not use the updated translations!
