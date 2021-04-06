#!/bin/sh
#
# We configure git to use this script instead of just /usr/bin/ssh.
# This script is used so we can pass some options to ssh when git uses it.
set -o errexit
set -o nounset

# Ensure required environment variables are present
[ -n "${PROJECT_ROOT}" ]
[ -n "${TRANSLATION_REPOSITORY_DEPLOY_KEY}" ]

# Ensure SSH has a writable configuration directory (otherwise it will fail)
export HOME="${PROJECT_ROOT}"
mkdir -p "${HOME}/.ssh"
chmod 700 "${HOME}/.ssh"

ssh -i "${TRANSLATION_REPOSITORY_DEPLOY_KEY}" \
    -o CheckHostIP=no -o StrictHostKeyChecking=no -T -x "${@}"


# This wrapper can be tested like so:
#
# PROJECT_ROOT=. TRANSLATION_REPOSITORY_DEPLOY_KEY=/path/to/ssh/private/key \
#     ./ssh_wrapper.sh git@github.com
