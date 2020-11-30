#!/bin/sh

# We configure git to use this script instead of just /usr/bin/ssh.
# This script is used so we can pass some options to ssh when git uses it.
# We assume that we've previously set TRANSLATION_REPOSITORY_DEPLOY_KEY in the
# environment to point to the key file.

# ssh fumbles if it can't write to .ssh, so give it a .ssh it can do that with.
export HOME=$PROJECT_ROOT
mkdir -p $HOME/.ssh
chmod 700 $HOME/.ssh

if [ "$TRANSLATION_REPOSITORY_DEPLOY_KEY" = "" ] ; then
  echo "$0 ERROR: TRANSLATION_REPOSITORY_DEPLOY_KEY is not set in the environment"
  exit 1
fi

exec ssh -o StrictHostKeyChecking=no -o CheckHostIP=no -i $TRANSLATION_REPOSITORY_DEPLOY_KEY "$@"
