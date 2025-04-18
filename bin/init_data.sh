#!/usr/bin/env bash
#
# Initialize Django application data (!!DANGER!!)
#
#### SETUP ####################################################################

set -o errexit
set -o errtrace
set -o nounset

# shellcheck disable=SC2154
trap '_es=${?};
    printf "${0}: line ${LINENO}: \"${BASH_COMMAND}\"";
    printf " exited with a status of ${_es}\n";
    exit ${_es}' ERR

DATA_FILE='../cc-legal-tools-data/config/app_data.yaml'
DIR_REPO="$(cd -P -- "${0%/*}/.." && pwd -P)"
# https://en.wikipedia.org/wiki/ANSI_escape_code
E0="$(printf "\e[0m")"        # reset
E30="$(printf "\e[30m")"      # black foreground
E31="$(printf "\e[31m")"      # red foreground
E33="$(printf "\e[33m")"      # yellow foreground
E43="$(printf "\e[43m")"      # yellow background
E107="$(printf "\e[107m")"    # bright white background

#### FUNCTIONS ################################################################

check_docker() {
    local _msg
    if ! docker compose exec app true 2>/dev/null; then
        _msg='The app container/services is not avaialable.'
        _msg="${_msg}\n       First run \`docker compose up\`."
        error_exit "${_msg}"
    fi
}

danger_confirm() {
    local _confirm _i _prompt _rand

    printf "${E43}${E30}# %-70s$(date '+%T') ${E0}\n" \
        'Confirmation required'
    echo -e "${E33}WARNING:${E0} this scripts deletes the app database"
    # Loop until user enters random number
    _rand=${RANDOM}${RANDOM}${RANDOM}
    _rand=${_rand:0:4}
    _prompt="Type the number, ${_rand}, to continue: "
    _i=0
    while read -p "${_prompt}" -r _confirm
    do
        if [[ "${_confirm}" == "${_rand}" ]]
        then
            echo
            return
        fi
        (( _i > 1 )) && error_exit 'invalid confirmation number'
        _i=$(( ++_i ))
    done
}

error_exit() {
    # Echo error message and exit with error
    echo -e "${E31}ERROR:${E0} ${*}" 1>&2
    exit 1
}

print_header() {
    # Print 80 character wide black on white heading with time
    printf "${E30}${E107}# %-70s$(date '+%T') ${E0}\n" "${@}"
}

#### MAIN #####################################################################

cd "${DIR_REPO}"

check_docker
danger_confirm

print_header 'Delete database'
docker compose exec app rm -fv db.sqlite3
echo

print_header 'Initialize database'
docker compose exec app sqlite3 db.sqlite3 -version
docker compose exec app sqlite3 db.sqlite3 -echo 'VACUUM;'
echo

print_header 'Perform database migrations'
docker compose exec app ./manage.py migrate
echo

print_header 'Create superuser'
docker compose exec app ./manage.py createsuperuser \
    --username admin --email "$(git config --get user.email)"
echo

print_header 'Django loaddata - Import LegalCode and Tool model data'
du -h "${DATA_FILE}"
docker compose exec app ./manage.py loaddata \
    --app legal_tools \
    --verbosity 3 \
    "${DATA_FILE}"
echo
