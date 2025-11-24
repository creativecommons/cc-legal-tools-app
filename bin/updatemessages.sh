#!/usr/bin/env bash
#
# Run Django Management nofuzzy_makemessages with helpful options (including
# excluding legalcode) and compilemessages
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

DIR_REPO="$(cd -P -- "${0%/*}/.." && pwd -P)"
# https://en.wikipedia.org/wiki/ANSI_escape_code
E0="$(printf "\e[0m")"        # reset
E30="$(printf "\e[30m")"      # black foreground
E31="$(printf "\e[31m")"      # red foreground
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

check_set_sed() {
    if command -v gsed >/dev/null; then
        GSED='gsed'
    elif sed --version >/dev/null; then
        GSED='sed'
    else
        # shellcheck disable=SC2016
        error_exit \
             'GNU sed is required. If on macOS install `gnu-sed` via brew.'
    fi

}

error_exit() {
    # Echo error message and exit with error
    echo -e "${E31}ERROR:${E0} ${*}" 1>&2
    exit 1
}

nofuzzy_makemessages () {
    print_header 'Django nofuzzy_makemessages'
    # shellcheck disable=SC2035
    docker compose exec app python manage.py nofuzzy_makemessages \
        --all \
        --symlinks \
        --ignore **/includes/legalcode_licenses_4.0.html \
        --ignore **/includes/legalcode_contextual_menu.html \
        --ignore **/includes/legalcode_zero.html \
        --no-obsolete \
        --verbosity 2
    echo
}

restore_creation_date() {
    local _creation_new _creation_old _pofile
    print_header 'Restore POT-Creation-Date'
    pushd ../cc-legal-tools-data/ >/dev/null
    for _pofile in $(git diff --name-only)
    do
        [[ "${_pofile}" =~ django\.po$ ]] || continue
        if _creation_old="$(git -c pager.diff=false diff "${_pofile}" \
            | grep '^-"POT-Creation-Date')"
        then
            echo "fixing POT-Creation-Date: ${_pofile}"
        else
            continue
        fi
        _creation_old="${_creation_old:2:${#_creation_old}-5}"
        _creation_new="$(git -c pager.diff=false diff "${_pofile}" \
            | grep '^+"POT-Creation-Date')"
        _creation_new="${_creation_new:2:${#_creation_new}-5}"
        if [[ -n "${_creation_old}" ]] && [[ -n "${_creation_new}" ]]; then
            echo "updating ${_pofile}"
            "${GSED}" -e"s#${_creation_new}#${_creation_old}#" -i "${_pofile}"
        fi
    done
    popd >/dev/null
    echo
}

print_header() {
    # Print 80 character wide black on white heading with time
    printf "${E30}${E107}# %-69s$(date '+%T') ${E0}\n" "${@}"
}

#### MAIN #####################################################################

cd "${DIR_REPO}"

check_docker
check_set_sed
nofuzzy_makemessages
restore_creation_date

print_header 'Django format_pofile'
docker compose exec app python manage.py format_pofile locale
echo

print_header 'Django compilemessages'
docker compose exec app coverage run manage.py \
    compilemessages
echo
