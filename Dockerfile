# https://docs.docker.com/engine/reference/builder/

# https://hub.docker.com/_/python/
FROM python:3.11-slim

# Configure apt not to prompt during docker build
ARG DEBIAN_FRONTEND=noninteractive

# Python: disable bytecode (.pyc) files
# https://docs.python.org/3.11/using/cmdline.html
ENV PYTHONDONTWRITEBYTECODE=1

# Python: force the stdout and stderr streams to be unbuffered
# https://docs.python.org/3.11/using/cmdline.html
ENV PYTHONUNBUFFERED=1

# Python: enable faulthandler to dump Python traceback on catastrophic cases
# https://docs.python.org/3.11/library/faulthandler.html
ENV PYTHONFAULTHANDLER=1

WORKDIR /root

# Configure apt to avoid installing recommended and suggested packages
RUN apt-config dump \
    | grep -E '^APT::Install-(Recommends|Suggests)' \
    | sed -e's/1/0/' \
    | tee /etc/apt/apt.conf.d/99no-recommends-no-suggests

# Resynchronize the package index and install packages
# https://docs.docker.com/build/building/best-practices/#apt-get
RUN apt-get update && apt-get install -y \
        gcc \
        gettext \
        git \
        sqlite3 \
        ssh \
    && rm -rf /var/lib/apt/lists/*

## Install pipenv
RUN pip install --upgrade \
    pip \
    pipenv \
    setuptools

# Install python dependencies
COPY Pipfile Pipfile.lock .
RUN pipenv sync --dev --system

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
