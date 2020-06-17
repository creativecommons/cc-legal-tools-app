#!/usr/bin/env bash
set -ex

# Script to run for the first Dokku deploy
# It tries to be idempotent where possible, but it's not always possible.
# After running this once, later deploys can be done just by pushing master to Dokku:
#
#        git push dokku master
#
# To deploy other branches, see http://dokku.viewdocs.io/dokku/deployment/application-deployment/#deploying-non-master-branch

# Allow overriding project name on command line
if [ "$1" != "" ] ; then
    PROJECT="$1"
else
    PROJECT="cc_licenses"
fi

if ! git status >/dev/null ; then
    echo "The project must be checked into git before continuing"
    exit 1
fi

DOKKU_SERVER=dokku

if ! ssh $DOKKU_SERVER version ; then
    echo "This script assumes 'ssh'"$DOKKU_SERVER"' will connect as dokku to the dokku server."
    echo "Either edit the top of this script, or add something like this to your ~/.ssh/config file:"
    cat <<_EOF_
Host $DOKKU_SERVER
  Hostname my.dokku.server.tld
  User dokku
  RequestTTY yes
_EOF_
    exit 1
fi

dokku() { ssh $DOKKU_SERVER "$@"; }

dokku apps:report $PROJECT || dokku apps:create $PROJECT

STORAGE=/var/lib/dokku/data/storage/$PROJECT
dokku storage:list $PROJECT | grep --quiet $STORAGE || dokku storage:mount $PROJECT $STORAGE:/storage
dokku config:set $PROJECT MEDIA_ROOT=/storage/media MEDIA_URL=/media ENVIRONMENT=production DOMAIN=$PROJECT.$(dokku domains:report $PROJECT --domains-global-vhosts)

# Create and link to database
dokku postgres:info $PROJECT-database || dokku postgres:create $PROJECT-database
dokku postgres:info $PROJECT-database | grep Links: | grep --quiet $PROJECT || dokku postgres:link $PROJECT-database $PROJECT

# Create a secret key, but only if there's not one already.
dokku config:get $PROJECT DJANGO_SECRET_KEY >/dev/null || dokku config:set --no-restart $PROJECT DJANGO_SECRET_KEY=$(make generate-secret)

# Create remote
git remote | grep dokku || git remote add dokku $DOKKU_SERVER:$PROJECT

# PUSH!  First deploy
git push dokku master

# Set up letsencrypt - assumes DOKKU_LETSENCRYPT_EMAIL is already set globally on the Dokku server, or else it'll fail
dokku letsencrypt $PROJECT
dokku letsencrypt:cron-job --add $PROJECT
