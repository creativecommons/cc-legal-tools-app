#!/bin/bash
set -o errexit
set -o errtrace
set -o nounset

# shellcheck disable=SC2154
trap '_es=${?};
    printf "${0}: line ${LINENO}: \"${BASH_COMMAND}\"";
    printf " exited with a status of ${_es}\n";
    exit ${_es}' ERR

# https://en.wikipedia.org/wiki/ANSI_escape_code
E0="$(printf "\e[0m")"        # reset
E1="$(printf "\e[1m")"        # bold
E9="$(printf "\e[9m")"        # strike (not supported in Terminal.app)
E30="$(printf "\e[30m")"      # black foreground
E31="$(printf "\e[31m")"      # red foreground
E33="$(printf "\e[33m")"      # yellow foreground
E90="$(printf "\e[90m")"      # bright black (gray) foreground
E97="$(printf "\e[97m")"      # bright white foreground
E100="$(printf "\e[100m")"    # bright black (gray) background
E107="$(printf "\e[107m")"    # bright white background
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


copy_vocabulary_theme_files() {
    header 'Copying necessary files from vocabulary-themes'
    print_var REPO_DIR
    print_var STATIC_THEME_DIR | sed -e"s#${REPO_DIR}#.#"
    {
        cp -av "${THEME_DIR}/src/chooser" "${STATIC_THEME_DIR}/"
        cp -v "${THEME_DIR}/src/style.css" "${STATIC_THEME_DIR}/"
        cp -av "${THEME_DIR}/src/vocabulary" "${STATIC_THEME_DIR}/"
    } | sed \
        -e"s#.* -> ${STATIC_THEME_DIR}#${E90}STATIC_THEME_DIR${E0}#"
    echo
}


create_static_theme_dirs() {
    header 'Creating necessary static theme directories'
    print_var REPO_DIR
    print_var STATIC_DIR | sed -e"s#${REPO_DIR}#.#"
    {
        mkdir -p -v "${STATIC_THEME_DIR}"
    } | sed -e"s#${STATIC_DIR}#${E90}STATIC_DIR${E0}#"
    echo
}


create_wp_content_readme() {
    header 'Creating wp-content README.md'
    print_var REPO_DIR
    print_var STATIC_DIR | sed -e"s#${REPO_DIR}#.#"
    echo "${README}" > "${STATIC_DIR}/wp-content/README.md"
    echo "${E90}STATIC_DIR${E0}/wp-content/README.md"
    echo
}


error_exit() {
    # Echo error message and exit with error
    echo -e "${E31}ERROR:${E0} ${*}" 1>&2
    exit 1
}


get_vocabulary_theme_dir() {
    header 'Getting vocabulary-theme dir'
    if ! THEME_DIR="$(cd -P -- \
        "${REPO_DIR}"/../vocabulary-theme 2> /dev/null \
        && pwd -P)" || ! [[ -d "${THEME_DIR}" ]]
    then
        error_exit \
            'creativecommons/vocabulary-theme is not a sibling directory'
    fi
    print_var REPO_DIR
    print_var STATIC_THEME_DIR | sed -e"s#${REPO_DIR}#.#"
    print_var THEME_DIR | sed -e"s#${THEME_DIR}#../vocabulary-theme#g"
    echo
}


header() {
    # Print 80 character wide black on white heading with time
    printf "${E30}${E107} %-71s$(date '+%T') ${E0}\n" "${@}"
}


print_key_val() {
    printf "${E97}${E100}%18s${E0} %s\n" "${1}:" "${2}"
}


print_var() {
    print_key_val "${1}" "${!1}"
}


purge_static_theme_dir() {
    header 'Purging existing static theme directories'
    print_var REPO_DIR
    print_var STATIC_DIR | sed -e"s#${REPO_DIR}#.#"
    print_var STATIC_THEME_DIR | sed -e"s#${REPO_DIR}#.#"
    {
        rm -f -r -v "${STATIC_THEME_DIR}/"*
    } | sed \
        -e"s#${STATIC_THEME_DIR}#${E90}${E9}STATIC_THEME_DIR${E0}${E9}#" \
        -e"s#\$#${E0}#"
    print_var REPO_DIR
    print_var STATIC_DIR | sed -e"s#${REPO_DIR}#.#"
    print_var STATIC_THEME_DIR | sed -e"s#${REPO_DIR}#.#"
    {
        rm -f -r -v "${STATIC_DIR}/wp-content"
    } | sed \
        -e"s#${STATIC_DIR}#${E90}${E9}STATIC_DIR${E0}${E9}#" \
        -e"s#\$#${E0}#"
    echo
}


#### MAIN #####################################################################

get_vocabulary_theme_dir
purge_static_theme_dir
create_static_theme_dirs
create_wp_content_readme
copy_vocabulary_theme_files
