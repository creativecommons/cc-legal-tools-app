# syntax=docker/dockerfile:1
# https://hub.docker.com/_/python/
FROM python:3.9
ENV PYTHONUNBUFFERED=1
ENV PYTHONFAULTHANDLER 1

# Install compilation dependencies and pipenv
RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc gettext
RUN pip install --upgrade pip \
    && pip install --upgrade setuptools \
    && pip install --upgrade pipenv

# Install python dependencies
COPY Pipfile .
COPY Pipfile.lock .
RUN pipenv sync --dev --system

# Configure git for tests (system is used instead of global because the cc home
# directory is used as the mount point for the repository)
RUN git config --system user.email 'app@docker-container'
RUN git config --system user.name 'App DockerContainer'

# Create and switch to a new "cc" user
RUN useradd --create-home cc
WORKDIR /home/cc
USER cc

# Install application into container
COPY . .
