# https://docs.docker.com/engine/reference/builder/

# https://github.com/creativecommons/containers/pkgs/container/trixie
FROM ghcr.io/creativecommons/trixie:latest

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
        nodejs \
        npm \
    && apt-get clean --quiet \
    && rm --recursive --force /var/lib/apt/lists/*

WORKDIR /opt
COPY prettier/prettier-server.js .
RUN set -o errexit -o nounset \
    && npm install express prettier

# Create Prettier service
COPY --chmod=0555 prettier/prettier-run /etc/sv/prettier/run
RUN set -o errexit -o nounset \
    && mkdir --parents /etc/sv/prettier/log \
    && ln -s /etc/sv/socklog-unix/log/run /etc/sv/prettier/log/run \
    && update-service --add prettier
