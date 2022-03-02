# https://docs.docker.com/engine/reference/builder/

# https://hub.docker.com/_/python/
FROM python:3.9-slim

# Configure apt not to prompt during docker build
ARG DEBIAN_FRONTEND=noninteractive

# Python: disable bytecode (.pyc) files
# https://docs.python.org/3.9/using/cmdline.html
ENV PYTHONDONTWRITEBYTECODE=1

# Python: force the stdout and stderr streams to be unbuffered
# https://docs.python.org/3.9/using/cmdline.html
ENV PYTHONUNBUFFERED=1

# Python: enable faulthandler to dump Python traceback on catastrophic cases
# https://docs.python.org/3.9/library/faulthandler.html
ENV PYTHONFAULTHANDLER=1

WORKDIR /root

# Configure apt to avoid installing recommended and suggested packages
RUN apt-config dump \
| grep -E '^APT::Install-(Recommends|Suggests)' \
| sed -e's/1/0/' \
| tee /etc/apt/apt.conf.d/99no-recommends-no-suggests

# Resynchronize the package index
RUN apt-get update

# Install apt packages missing from slim docker image
RUN apt-get install -y git ssh

# Install apt package dependencies
RUN apt-get install -y gcc gettext sqlite3

## Install pipenv
RUN pip install --upgrade pip
RUN pip install --upgrade setuptools
RUN pip install --upgrade pipenv

# Install python dependencies
COPY Pipfile .
COPY Pipfile.lock .
RUN pipenv sync --dev --system

# Create and switch to a new "cc" user
RUN useradd --create-home cc
WORKDIR /home/cc
USER cc:cc
RUN mkdir .ssh
RUN chmod 0700 .ssh

# Configure git for tests
RUN git config --global user.email 'app@docker-container'
RUN git config --global user.name 'App DockerContainer'

## Prepare for running app
RUN mkdir cc-legal-tools-app
RUN mkdir cc-legal-tools-data
WORKDIR /home/cc/cc-legal-tools-app
