

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
