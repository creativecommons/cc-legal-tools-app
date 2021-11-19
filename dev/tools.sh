#!/bin/bash
#
# Run Python code tools (isort, black, flake8)
#
set -o errtrace
set -o nounset

# Change directory to cc-legal-tools-app (grandparent directory of this script)
cd ${0%/*}/../

if ! docker-compose exec app true 2>/dev/null; then
    echo 'The app container/services is not avaialable.' 1>&2
    echo 'First run `docker-compose up`.' 1>&2
    exit 1
fi

printf "\e[1m\e[7m %-80s\e[0m\n" 'isort'
docker-compose exec app isort ${@:-.}
echo

printf "\e[1m\e[7m %-80s\e[0m\n" 'black'
docker-compose exec app black ${@:-.}
echo

printf "\e[1m\e[7m %-80s\e[0m\n" 'flake8'
docker-compose exec app flake8 ${@:-.}
echo
