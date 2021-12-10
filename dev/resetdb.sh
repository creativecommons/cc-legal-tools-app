#!/bin/bash
#
# Reset Django application database data (!!DANGER!!)
set -o errexit
set -o errtrace
set -o nounset

# Change directory to cc-legal-tools-app (grandparent directory of this script)
cd ${0%/*}/../

if ! docker-compose exec app true 2>/dev/null; then
    echo 'The app container/services is not avaialable.' 1>&2
    echo 'First run `docker-compose up`.' 1>&2
    exit 1
fi

printf "\e[1m\e[7m %-80s\e[0m\n" 'Flush Database'
docker-compose exec app ./manage.py flush
echo

printf "\e[1m\e[7m %-80s\e[0m\n" 'Perform migrations'
docker-compose exec app ./manage.py migrate
echo

printf "\e[1m\e[7m %-80s\e[0m\n" 'createsuperuser'
docker-compose exec app ./manage.py createsuperuser \
    --username admin --email "$(git config --get user.email)"
echo
