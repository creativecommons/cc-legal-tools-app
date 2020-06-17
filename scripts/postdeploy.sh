#!/usr/bin/env bash
set -ex

# This runs *inside* the container, very late in the deploy - I think,
# after dokku has actually switched over to the newly deployed version
# of the app. As such, it's too late for most of the things we might
# want to do during a deploy.

# Current directory is "/app", which is the root of the copy
# of this repository inside the container.
# Lots of env vars are set, and a bunch of shell vars too.
# Uncomment the next few lines and try a deploy to see all the current ones.
echo "POSTDEPLOY SCRIPT"
#echo "Current directory: "$(pwd)
#echo "LS:"
#ls -A
#echo "Environment:"
#printenv|sort
#echo "VARIABLES:"
#set
