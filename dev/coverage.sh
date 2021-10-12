#!/bin/bash
#
# Run coverage tests and report
#
set -o errtrace
set -o nounset

# This script passes all arguments to Coverage Tests. For example, it can be
# called from the cc-licenses directory like so:
#
#     ./dev/coverage.sh --failfast

# Change directory to cc-licenses (grandparent directory of this script)
cd ${0%/*}/../

printf "\e[1m\e[7m %-80s\e[0m\n" 'Coverage Tests'
docker-compose exec app coverage run manage.py test --noinput ${@:-} \
    || exit
echo

printf "\e[1m\e[7m %-80s\e[0m\n" 'Coverage Report'
docker-compose exec app coverage report
echo
