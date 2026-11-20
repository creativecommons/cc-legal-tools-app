# https://docs.docker.com/engine/reference/builder/

# https://github.com/creativecommons/containers/pkgs/container/trixie
FROM ghcr.io/creativecommons/trixie:latest

# Python: disable bytecode (.pyc) files
# https://docs.python.org/3.13/using/cmdline.html
#ENV PYTHONDONTWRITEBYTECODE=1

# Django: disable development server warning
# https://docs.djangoproject.com/en/5.2/ref/django-admin/#envvar-DJANGO_RUNSERVER_HIDE_WARNING
ENV DJANGO_RUNSERVER_HIDE_WARNING=true

# Python: force the stdout and stderr streams to be unbuffered
# https://docs.python.org/3.13/using/cmdline.html
ENV PYTHONUNBUFFERED=1

# Python: enable faulthandler to dump Python traceback on catastrophic cases
# https://docs.python.org/3.13/library/faulthandler.html
ENV PYTHONFAULTHANDLER=1

#Python: force-enable pip's PEP 517 mode
# https://github.com/pypa/pip/issues/6334
#ENV PIP_USE_PEP517=true

# https://docs.docker.com/build/building/best-practices/#apt-get
# - apt and dpkg are configured in parent CC Debian trixie image
# - Retrieve new lists of packages, distribution upgrade, install new
#   packages, erase downloaded archive files, and erase package lists
# - nodejs and npm are only used to test GitHub Actions workflow
#   compatibility (PRETTIER_SLOW=1)
RUN set -o errexit -o nounset \
    && apt-get update  --quiet \
    && apt-get dist-upgrade --quiet --yes \
    && apt-get install --quiet --yes \
        gcc \
        gettext \
        git \
        nodejs \
        npm \
        pipenv \
        sqlite3 \
        ssh \
    && apt-get clean --quiet \
    && rm --recursive --force /var/lib/apt/lists/*

# Command line prettier is only used to test GitHub Actions workflow
# compatibility (PRETTIER_SLOW=1)
RUN npm install --global prettier

# Create Django service
COPY --chmod=0555 app/django-run /etc/sv/django/run
RUN set -o errexit -o nounset \
    && mkdir --parents /etc/sv/django/log \
    && ln -s /etc/sv/socklog-unix/log/run /etc/sv/django/log/run \
    && update-service --add django

# Create and switch to a new "cc" user
RUN useradd --create-home cc
WORKDIR /home/cc
USER cc:cc
RUN set -o errexit -o nounset \
    && mkdir --mode=0700 .ssh \
    && mkdir cc-legal-tools-app \
    && mkdir cc-legal-tools-data

# Configure git for tests
RUN git config --global user.email 'app@docker-container' \
    && git config --global user.name 'App DockerContainer' \
    && git config --global --add safe.directory '*'

# Install python dependencies
COPY Pipfile Pipfile.lock .
RUN set -o errexit -o nounset \
    && mkdir .venv \
    && PIPENV_VENV_IN_PROJECT=1 pipenv sync --dev --no-site-packages
ENV VIRTUAL_ENV=/home/cc/.venv
ENV PATH=$VIRTUAL_ENV/bin:$PATH

WORKDIR /home/cc/cc-legal-tools-app

# ENTRYPOINT **must** be run as root
USER root
