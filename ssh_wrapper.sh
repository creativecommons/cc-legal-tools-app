#!/bin/sh

# We configure git to use this script instead of just /usr/bin/ssh.
# This script is used so we can pass some options to ssh when git uses it.
# We assume that we've previously set TRANSLATION_REPOSITORY_DEPLOY_KEY in the
# environment to point to the key file.

exec ssh -o StrictHostKeyChecking=no -i $TRANSLATION_REPOSITORY_DEPLOY_KEY "$@"
