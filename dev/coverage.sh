#!/bin/bash
#
# Run coverage tests and report
#
set -o errtrace
set -o nounset

# This script passes all arguments to Coverage Tests. For example, it can be
# called from the cc-legal-tools-app directory like so:
#
#     ./dev/coverage.sh --failfast

# Change directory to cc-legal-tools-app (grandparent directory of this script)
cd ${0%/*}/../

if ! docker-compose exec app true 2>/dev/null; then
    echo 'The app container/services is not avaialable.' 1>&2
    echo 'First run `docker-compose up`.' 1>&2
    exit 1
fi

printf "\e[1m\e[7m %-80s\e[0m\n" 'Coverage Tests'
docker-compose exec app coverage run manage.py test --noinput ${@:-} \
    || exit
echo

printf "\e[1m\e[7m %-80s\e[0m\n" 'Coverage Report'
docker-compose exec app coverage report
echo
