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
if ! docker-compose exec db true 2>/dev/null; then
    echo 'The app container/services is not avaialable.' 1>&2
    echo 'First run `docker-compose up`.' 1>&2
    exit 1
fi


DOCKER_DB_RUN="docker-compose run -e PGHOST=db \
                                  -e PGDATABASE=postgres \
                                  -e PGPASSWORD=postgres \
                                  -e PGUSER=postgres \
                                  db"

printf "\e[1m\e[7m %-80s\e[0m\n" 'Drop Database'
${DOCKER_DB_RUN} psql -d template1 \
    -c "SELECT pg_terminate_backend(pid)
        FROM pg_stat_activity
        WHERE datname='postgres';" \
    -c 'ALTER DATABASE postgres allow_connections = off;' \
    -c 'DROP DATABASE postgres;'
echo

printf "\e[1m\e[7m %-80s\e[0m\n" 'Create Database'
${DOCKER_DB_RUN} psql -d template1 \
    -c "CREATE DATABASE postgres OWNER postgres;" \
    -c 'ALTER DATABASE postgres allow_connections = on;'
echo

#printf "\e[1m\e[7m %-80s\e[0m\n" 'Reset migrations'
#docker-compose exec app ./manage.py migrate --fake licenses zero
#echo

printf "\e[1m\e[7m %-80s\e[0m\n" 'Perform migrations'
docker-compose exec app ./manage.py migrate
echo

printf "\e[1m\e[7m %-80s\e[0m\n" 'createsuperuser'
docker-compose exec app ./manage.py createsuperuser \
    --username admin --email "$(git config --get user.email)"
echo

#printf "\e[1m\e[7m %-80s\e[0m\n" 'Restart app'
#docker-compose restart app
#echo
