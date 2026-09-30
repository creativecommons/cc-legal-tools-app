# https://docs.docker.com/engine/reference/builder/

# https://hub.docker.com/_/python/
FROM python:3.13

# Configure apt not to prompt during docker build
ARG DEBIAN_FRONTEND=noninteractive

# Python: disable bytecode (.pyc) files
# https://docs.python.org/3.13/using/cmdline.html
ENV PYTHONDONTWRITEBYTECODE=1

# Python: force the stdout and stderr streams to be unbuffered
# https://docs.python.org/3.13/using/cmdline.html
ENV PYTHONUNBUFFERED=1

# Python: enable faulthandler to dump Python traceback on catastrophic cases
# https://docs.python.org/3.13/library/faulthandler.html
ENV PYTHONFAULTHANDLER=1

# Python: force-enable pip's PEP 517 mode
# https://github.com/pypa/pip/issues/6334
#ENV PIP_USE_PEP517=true

WORKDIR /root

# https://docs.docker.com/build/building/best-practices/#apt-get
# - Resynchronize the package index, update packages, install packages, and
#   clean-up
# - nodejs and npm are only used to test GitHub Actions workflow
#   compatibility (PRETTIER_SLOW=1)
RUN DEBIAN_FRONTEND=noninteractive apt-get update \
        --no-allow-insecure-repositories --quiet \
    && DEBIAN_FRONTEND=noninteractive apt-get dist-upgrade \
        --no-install-recommends --no-install-suggests --quiet --yes \
    && DEBIAN_FRONTEND=noninteractive apt-get install \
        --no-install-recommends --no-install-suggests --quiet --yes \
        gcc \
        gettext \
        git \
        nodejs \
        npm \
        sqlite3 \
        ssh \
    && DEBIAN_FRONTEND=noninteractive apt-get clean --quiet \
    && rm --recursive --force /var/lib/apt/lists/*

## Install pipenv
RUN pip install --upgrade \
    pip \
    pipenv \
    setuptools

# Install python dependencies
COPY Pipfile Pipfile.lock .
RUN pipenv sync --dev --system

# Command line prettier is only used to test GitHub Actions workflow
# compatibility (PRETTIER_SLOW=1)
RUN npm install --global prettier

# Create and switch to a new "cc" user
RUN useradd --create-home cc
WORKDIR /home/cc
USER cc:cc
RUN mkdir .ssh && chmod 0700 .ssh

# Configure git for tests
RUN git config --global user.email 'app@docker-container' \
    && git config --global user.name 'App DockerContainer' \
    && git config --global --add safe.directory '*'

## Prepare for running app
RUN mkdir cc-legal-tools-app \
    && mkdir cc-legal-tools-data
WORKDIR /home/cc/cc-legal-tools-app

# vim: ft=dockerfile
