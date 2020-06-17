#!/usr/bin/env bash
set -ex

# This runs *inside* the container, after things have been installed and
# collectstatic has run.
# Current directory is "/app", which is the root of the copy
# of this repository inside the container.
# Lots of env vars are set, and a bunch of shell vars too.
# Uncomment the next few lines and try a deploy to see all the current ones.
echo "PREDEPLOY SCRIPT"
#echo "Current directory: "$(pwd)
#echo "LS:"
#ls -A
#echo "Environment:"
#printenv|sort
#echo "VARIABLES:"
#set
#exit 1

mkdir -p $MEDIA_ROOT

# NOTE: the buildpack should already have installed our node packages
npm run build
# We need to run collectstatic here, even though the buildpack already did,
# to pick up the output of the `npm run build`
python manage.py collectstatic --noinput

# Run migrations
python manage.py migrate --noinput
