#!/bin/bash
#
# Run coverage tests and report
#
# This script passes all arguments to Coverage Tests. For example, it can be
# called from the cc-legal-tools-app directory like so:
#
#     ./dev/coverage.sh --failfast

set -o errexit
set -o errtrace
set -o nounset

# shellcheck disable=SC2154
trap '_es=${?};
    printf "${0}: line ${LINENO}: \"${BASH_COMMAND}\"";
    printf " exited with a status of ${_es}\n";
    exit ${_es}' ERR

DIR_REPO="$(cd -P -- "${0%/*}/.." && pwd -P)"
# https://en.wikipedia.org/wiki/ANSI_escape_code
E0="$(printf "\e[0m")"        # reset
E30="$(printf "\e[30m")"      # black foreground
E31="$(printf "\e[31m")"      # red foreground
E107="$(printf "\e[107m")"    # bright white background

#### FUNCTIONS ################################################################

error_exit() {
    # Echo error message and exit with error
    echo -e "${E31}ERROR:${E0} ${*}" 1>&2
    exit 1
}

print_header() {
    # Print 80 character wide black on white heading with time
    printf "${E30}${E107}# %-69s$(date '+%T') ${E0}\n" "${@}"
}

#### MAIN #####################################################################

cd "${DIR_REPO}"

docker compose exec app true 2>/dev/null \
    || error_exit \
        'The Docker app container/service is not avaialable. See README.md'

print_header 'Coverage erase'
docker compose exec app coverage erase --debug=dataio
echo

print_header 'Coverage tests'
docker compose exec app coverage run --debug=pytest \
    manage.py test --noinput --parallel 4 ${@:-} \
    || exit
echo

print_header 'Coverage combine'
docker compose exec app coverage combine
echo

print_header 'Coverage html'
docker compose exec app coverage html
echo

print_header 'Coverage report'
docker compose exec app coverage report
echo
