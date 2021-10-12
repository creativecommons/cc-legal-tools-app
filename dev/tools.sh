#!/bin/bash
#
# Run Python code tools (isort, black, flake8)
#
set -o errtrace
set -o nounset

# Change directory to cc-licenses (grandparent directory of this script)
cd ${0%/*}/../

printf "\e[1m\e[7m %-80s\e[0m\n" 'isort'
docker-compose exec app isort ${@:-.}
echo

printf "\e[1m\e[7m %-80s\e[0m\n" 'black'
docker-compose exec app black ${@:-.}
echo

printf "\e[1m\e[7m %-80s\e[0m\n" 'flake8'
docker-compose exec app flake8 ${@:-.}
echo
