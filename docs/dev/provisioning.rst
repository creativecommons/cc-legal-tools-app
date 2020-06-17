Server Provisioning
========================


Overview
------------------------

Cc_Licenses is deployed on the following stack.

- OS: Ubuntu 18.04 LTS
- Python: 3.7+
- Database: Postgres 9.3
- Application Server: Gunicorn
- Frontend Server: Nginx
- Cache: Memcached

These services can configured to run together on a single machine or on different machines.
`Supervisord <http://supervisord.org/>`_ manages the application server process.


.. note::

    Deploying using Dokku is an alternative to the information on this page.
    See the README to get started.


Provisioning Options
--------------------

Caktus prefers one of two provisioning options for new projects, `Tequila`_ or `Dokku`_.

Dokku is a good option for small projects, early projects in need of a staging machine,
or non-client projects run as experiments or side projects.

Tequila, built on Ansible, should be used for any project that will need more than one machine
and more complex provisioning and deployment configurations.

Dokku
'''''

The configuration requirements for Dokku are very small, so they are included in the
project template by default. You can even use them in addition to Tequila, if you'd like,
or transition from Dokku to Tequila after an initial prototyping phase of a project.

Primarily Dokku is configured by the `runtime.txt` and `app.json` files. The `predeploy.sh` and
`postdeploy.sh` scripts are also used as part of the Dokku deploys. In order to setup a new project
just create a new Dokku app on your server and a new database using the Dokku Postgres plugin::

    ssh dokku@dokku.me apps:create my-new-app
    ssh dokku@dokku.me postgres:create my-new-app-db
    postgres:link my-new-app-db my-new-app

And configure the Dokku server as a remote for your git repository::

    git remote add dokku dokku@dokku.me:my-new-app

Now, simply pushing to this remote will deploy your application's master branch::

    git push dokku

Tequila
'''''''

You can read about how to setup Tequila for a new project from
`Tequila Project Setup <https://github.com/caktus/tequila/blob/master/docs/project_setup.rst>`
documentation, which will walk you through adding Tequila to any Django project, including one
created from this project template.
