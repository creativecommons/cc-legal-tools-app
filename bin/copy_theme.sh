#!/usr/bin/env bash
#
# Rsync vocabulary-theme files from a normal checkout (not a releaes tag
# checkout, which has a different structure)
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
E30="$(printf "\e[30m")"      # foreground: black
E31="$(printf "\e[31m")"      # foreground: red
E94="$(printf "\e[94m")"      # foreground: bright blue
E97="$(printf "\e[97m")"      # foreground: bright white
E100="$(printf "\e[100m")"    # background: bright black (gray)
E107="$(printf "\e[107m")"    # background: bright white
# shellcheck disable=SC2016
README='# Dev theme files

This directory is only used in the Django and GitHub development environments.
In the Docker development, staging, and production environments, the files are
provided by the [creativecommons/vocabulary-theme][vocabulary-theme] WordPress
theme.

For additional information on the Docker development, staging, and production
environments, see [creativecommons/index-dev-env][index-dev-env].

Also see the primary repository [`../../../README.md`](../../../README.md).

[vocabulary-theme]: https://github.com/creativecommons/vocabulary-theme
[index-dev-env]: https://github.com/creativecommons/index-dev-env'
REPO_DIR="$(cd -P -- "${0%/*}/.." && pwd -P)"
STATIC_DIR="${REPO_DIR}/cc_legal_tools/static"
STATIC_THEME_DIR="${STATIC_DIR}/wp-content/themes/vocabulary-theme"
# The get_vocabulary_theme_dir() function sets the following global variables:
THEME_DIR=''

#### FUNCTIONS ################################################################

check_pipenv() {
    local _msg
    if ! pipenv --venv --quiet >/dev/null
    then
        _msg='The pipenv virtual environment is not avaialable.'
        _msg="${_msg}\n       First run \`pipenv sync --dev\`."
        error_exit "${_msg}"
    fi
}

create_static_theme_dirs() {
    print_header 'Create necessary static theme directories'
    print_var REPO_DIR
    print_var STATIC_DIR | sed -e"s#${REPO_DIR}#${E94}REPO_DIR${E0}#"
    print_var STATIC_THEME_DIR | sed -e"s#${STATIC_DIR}#${E94}STATIC_DIR${E0}#"
    mkdir -p "${STATIC_THEME_DIR}"
    # shellcheck disable=SC2012
    ls -D'%F' -d -h -o "${STATIC_THEME_DIR}" \
        | sed -e"s#${STATIC_DIR}#${E94}STATIC_DIR${E0}#" \
        | awk '{print $1" "$6}'
    echo
}

create_wp_content_readme() {
    print_header 'Create wp-content README.md'
    print_var REPO_DIR
    print_var STATIC_DIR | sed -e"s#${REPO_DIR}#${E94}REPO_DIR${E0}#"
    echo "${README}" > "${STATIC_DIR}/wp-content/README.md"
    # shellcheck disable=SC2012
    ls -D'%F' -h -o "${STATIC_DIR}/wp-content/README.md" \
        | sed -e"s#${STATIC_DIR}#${E94}STATIC_DIR${E0}#" \
        | awk '{print $1" "$6}'
    echo
}

error_exit() {
    # Echo error message and exit with error
    echo -e "${E31}ERROR:${E0} ${*}" 1>&2
    exit 1
}

get_vocabulary_theme_dir() {
    print_header 'Get vocabulary-theme dir'
    if ! THEME_DIR="$(cd -P -- \
        "${REPO_DIR}"/../vocabulary-theme 2> /dev/null \
        && pwd -P)" || ! [[ -d "${THEME_DIR}" ]]
    then
        error_exit \
            'creativecommons/vocabulary-theme is not a sibling directory'
    fi
    print_var THEME_DIR
    pushd "${THEME_DIR}" >/dev/null
    git log --decorate=no -1
    popd >/dev/null
    echo
}

print_header() {
    # Print 80 character wide black on white heading with time
    printf "${E30}${E107} %-71s$(date '+%T') ${E0}\n" "${@}"
}

print_key_val() {
    printf "${E97}${E100}%18s${E0} %s\n" "${1}:" "${2}"
}

print_var() {
    print_key_val "${1}" "${!1}"
}

rsync_vocabulary_theme_files() {
    print_header 'Rsync necessary files from vocabulary-themes'
    print_var THEME_DIR
    print_var REPO_DIR
    print_var STATIC_DIR | sed -e"s#${REPO_DIR}#${E94}REPO_DIR${E0}#"
    print_var STATIC_THEME_DIR | sed -e"s#${STATIC_DIR}#${E94}STATIC_DIR${E0}#"
    # The rsync options below are ordered to match `man rsync`
    rsync \
        --recursive \
        --links \
        --delete \
        --delete-excluded \
        --partial \
        --prune-empty-dirs \
        --times \
        --exclude 'inc/' \
        --exclude '*.php' \
        --stats \
        --human-readable \
        "${THEME_DIR}/src/" \
        "${STATIC_THEME_DIR}/"
    echo
}

run_pre-commit() {
    print_header 'Run pre-commit to clean-up files'
    print_var REPO_DIR
    print_var STATIC_DIR | sed -e"s#${REPO_DIR}#${E94}REPO_DIR${E0}#"
    print_var STATIC_THEME_DIR | sed -e"s#${STATIC_DIR}#${E94}STATIC_DIR${E0}#"
    find "${STATIC_THEME_DIR}" -type f -print0 \
        | xargs -0 pipenv run pre-commit run --color=always --files || true
    echo
}

#### MAIN #####################################################################

cd "${DIR_REPO}"

check_pipenv
get_vocabulary_theme_dir
create_static_theme_dirs
create_wp_content_readme
rsync_vocabulary_theme_files
run_pre-commit
