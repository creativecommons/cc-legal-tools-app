Server Provisioning
========================

Overview
------------------------

Cc_Licenses is deployed on the following stack.

- OS: Ubuntu 18.04 LTS or 20.04 LTS
- Python: 3.7 (or higher)
- Database: Postgres 10+
- Application Server: Gunicorn
- Frontend Server: Nginx

Domain and SSL certificate
--------------------------

(I put this first because you might have to wait for someone else
to do it, so you might as well start it as early as possible.)

Just a reminder that you'll need a domain name that resolves to
the IP address of your web server, and a corresponding SSL
certificate if you want to serve pages over SSL.

Deploying
---------

Here's a recipe for deploying this web site that should work. Automating
this is left as an exercise for the reader.

If you haven't before, clone the repo::

    $ git clone git@github.com:creativecommons/cc-licenses.git

Change to the new directory for the rest of these steps::

    $ cd cc-licenses

Check out the "main" branch::

    $ git checkout main

Do a ``git pull`` to make sure you have the latest from upstream::

    $ git pull origin main

A word to the wise: I often forget that these things change, and have
to remind myself to use the documentation from the version of the code
I'm trying to use.

Environment
...........

Create a virtual environment using Python 3.7::

    $ python3 --version
    Python 3.7.7
    $ python3 -m venv /somepath/cc-licenses-venv

Activate the venv::

    $ . /somepath/cc-licenses-venv/bin/activate

Install the Python requirements for production into the virtual
environment::

    $ pip install -r requirements/production.txt

Settings
........

We configure a particular site deploy by arranging for a bunch of
environment variables to be set before starting Django.

Tell Django to use the deploy settings::

    $ export DJANGO_SETTINGS_MODULE=cc_licenses.settings.deploy

Set the ENVIRONMENT environment variable to a name to distinguish this
deploy from others, e.g. "staging" or "production"::

    $ export ENVIRONMENT=staging

Arrange to make an empty Postgres database available for the site, and
set environment variable DATABASE_URL pointing to it::

    $ export DATABASE_URL="postgresql://user:pass@hostname:port/dbname?sslmode=require"

Note: When coming up with this URL, you can test by seeing if psql can
connect to it::

    $ psql $DATABASE_URL

Create a local directory for static files. This directory needs to be
writable during this deploy process, and readable by the Django server
at runtime. Call it STATIC_ROOT::

    $ export STATIC_ROOT=/path/to/staticfiles

(This is for files that come from the site source code and will be served
as static files, like ``.css`` and ``.js`` files.)

Create a local directory for media files. This directory must be readable
and writable by the Django process at runtime. Call it MEDIA_ROOT::

    $ export MEDIA_ROOT=/path/to/mediafiles

(This is for any files that might need to be uploaded by users and stored
by the Django process, then served again later. Examples: images, avatars,
files - it depends on the site.)

Generate a secret key to use, which should be a long random string. One
way::

    #!/usr/bin/env python3
    from django.utils.crypto import get_random_string
    chars = 'abcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*(-_=+)'
    SECRET_KEY = get_random_string(50, chars)

Then set it as DJANGO_SECRET_KEY::

    $ export DJANGO_SECRET_KEY=<the random string from above>

This should be different for each site being deployed, but the same on
all servers running Django for a particular site, and not changing over
time.

Set DOMAIN to the hostname the site will be served at::

    $ export DOMAIN=www.example.com

The site might need to send email to admins on errors, and to users for
things like password resets. Arrange to make an SMTP server available for
outgoing email, then set the following Django settings as environment
variables:

* EMAIL_HOST
* EMAIL_HOST_USER
* EMAIL_HOST_PASSWORD
* EMAIL_USE_TLS
* EMAIL_USE_SSL (just set one of EMAIL_USE_TLS or EMAIL_USE_TLS to a
  non-empty string to indicate "True"; leave the other unset)
* EMAIL_PORT (optional; defaults to 25, 465, or 587 depending on
  whether EMAIL_USE_TLS, EMAIL_USE_SSL, or neither are set)
* DEFAULT_FROM_EMAIL
* EMAIL_SUBJECT_PREFIX

These are documented starting
`here <https://docs.djangoproject.com/en/3.0/ref/settings/#email-host>`_;
I won't bother copying the docs.

Migrate and collect static
..........................

There are a couple of tasks that need to be done any time the code is
updated, before (re)starting the server. The migrate step only needs to
be done on one server since it updates the database that all servers are
sharing. The collectstatic step needs to be done on every server.

We generally build this into our deploy process.

1. Activate the virtual env::

    $ . /somepath/cc-licenses-venv/bin/activate

2. Set all the environment variables (above).

3. Run database migrations:

    $ python manage.py migrate --noinput

4. Collect all static files to STATIC_ROOT:

    $ python manage.py collectstatic --noinput

Run Django
..........

To get a process running Django and serving requests, we'll use a tool
called `gunicorn <https://gunicorn.org/>`_ that's installed into the
virtual environment.

We'll run this strictly internally, listening for requests on a Unix port.
Our web server will proxy to that port.

Reminder: arrange for the environment variables mentioned above to be set
before gunicorn is started.  (You can set them on the gunicorn command
line with ``-e``, but it gets unwieldy.)

::

    $ cd path-where-we-checked-out-the-code
    $ /somepath/cc-licenses-venv/bin/gunicorn --bind unix:/tmp/portfile cc_licenses.wsgi

Gunicorn has lots of options for tuning which you can look up.

Run a webserver in front
........................

We usually run nginx as our front-end web server. A simple approach is to
add a new config file to /etc/nginx/sites-enabled for each site, making
sure server_name is set correctly in each.  E.g.
``/etc/nginx/sites-enabled/www.example.com.conf`` (the name is completely
arbitrary). Then reload or restart nginx.

In that config file, we generally want to redirect non-SSL requests to
SSL with something like::

    server {
      listen *:80;
      listen [::]:80;
      server_name DOMAIN;
      access_log PATH_access.log;
      error_log PATH_error.log;
      return 301 https://DOMAIN$request_uri;
    }

changing DOMAIN and PATH appropriately.

Then we proxy the SSL requests to Django, by adding something like this
to the file (the SSL cipher settings might be out of date, though).

Note: *after* this is known to be working, you can uncomment the
``Strict-Transport-Security`` line if you want.

You'll need a valid SSL certificate for this.

Again, change the all-caps parts appropriately::

    upstream django {
      server unix:/tmp/portfile fail_timeout=0;
    }

    server {
      listen *:443 ssl;   # add spdy here too if you want
      listen [::]:443 ssl;
      server_name DOMAIN;
      ssl_certificate PATH.crt;
      ssl_certificate_key PATH.key;

      access_log PATH_access.log;
      error_log PATH_error.log;
      root PATH;
      location /media {
        alias MEDIA_ROOT;
      }
      location /static {
        alias STATIC_ROOT;
      }
      location / {
        client_max_body_size 500M;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header Host $host;
        proxy_redirect off;
        proxy_buffering on;
        proxy_intercept_errors on;
        proxy_pass http://django;
      }

      # See https://www.trevorparker.com/hardening-ssl-in-nginx/
      ssl_protocols             TLSv1 TLSv1.1 TLSv1.2;
      ssl_prefer_server_ciphers on;
      ssl_ciphers               DHE-RSA-AES128-GCM-SHA256:DHE-DSS-AES128-GCM-SHA256:ECDHE-RSA-AES1\
    28-GCM-SHA256:ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES256-GCM-SHA384:ECDHE-ECDSA-AES256-GCM\
    -SHA384:kEDH+AESGCM:DHE-RSA-AES128-SHA256:DHE-RSA-AES128-SHA:DHE-DSS-AES128-SHA256:DHE-RSA-AES\
    256-SHA256:DHE-DSS-AES256-SHA:DHE-RSA-AES256-SHA:ECDHE-RSA-AES128-SHA256:ECDHE-ECDSA-AES128-SH\
    A256:ECDHE-RSA-AES128-SHA:ECDHE-ECDSA-AES128-SHA:ECDHE-RSA-AES256-SHA384:ECDHE-ECDSA-AES256-SH\
    A384:ECDHE-RSA-AES256-SHA:ECDHE-ECDSA-AES256-SHA:AES128-GCM-SHA256:AES256-GCM-SHA384:AES128-SH\
    A256:AES256-SHA256:AES128-SHA:AES256-SHA:AES:CAMELLIA:DES-CBC3-SHA:!aNULL:!eNULL:!EXPORT:!DES:\
    !RC4:!MD5:!PSK:!aECDH:!EDH-DSS-DES-CBC3-SHA:!EDH-RSA-DES-CBC3-SHA:!KRB5-DES-CBC3-SHA;
      ssl_session_timeout       5m;
      ssl_session_cache         shared:SSL:10m;

      # add_header Strict-Transport-Security max-age=31536000;
    }

Finally, reload or restart nginx::

    $ sudo systemctl reload nginx

Troubleshooting
---------------

Once all that is running, you should be able to visit
https://www.example.com and see the site front page. But, sometimes not
everything is quite right the first time :-)

A gateway error indicates that gunicorn isn't running. Add some gunicorn
logging if necessary, and check those logs.

If you see the wrong site, nginx isn't properly routing requests for that
server name to our server. See
http://nginx.org/en/docs/http/server_names.html. Keep in mind that nginx
defaults to just sending requests to the first server it can find if it
doesn't recognize the incoming server name.
