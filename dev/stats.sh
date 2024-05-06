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
E4="$(printf "\e[4m")"        # underline
E30="$(printf "\e[30m")"      # black foreground
E31="$(printf "\e[31m")"      # red foreground
E33="$(printf "\e[33m")"      # yellow foreground
E97="$(printf "\e[97m")"      # bright white foreground
E100="$(printf "\e[100m")"    # bright black (gray) background
E107="$(printf "\e[107m")"    # bright white background
DIR_REPO="$(cd -P -- "${0%/*}/.." && pwd -P)"
DIR_PUB_LICENSES="$(cd -P -- \
    "${DIR_REPO}/../cc-legal-tools-data/docs/licenses" && pwd -P)"
DIR_PUB_PUBLICDOMAIN="$(cd -P -- \
    "${DIR_REPO}/../cc-legal-tools-data/docs/publicdomain" && pwd -P)"


#### FUNCTIONS ################################################################


check_prerequisites() {
    if ! command -v scc &>/dev/null
    then
        # shellcheck disable=SC2016
        error_exit 'The `scc` command is unavailable.'
    fi
}


error_exit() {
    # Echo error message and exit with error
    echo -e "${E31}ERROR:${E0} ${*}" 1>&2
    exit 1
}


header() {
    # Print 80 character wide black on white heading with time
    printf "${E30}${E107} %-71s$(date '+%T') ${E0}\n" "${@}"
}


print_key_val() {
    local _sep
    if (( ${#1} > 10 ))
    then
        _sep="\n    "
    else
        _sep=' '
    fi
    printf "${E97}${E100}%21s${E0}${_sep}%s\n" "${1}:" "${2}"
}


print_var() {
    print_key_val "${1}" "${!1}"
}


published_documents() {
    local _count
    header 'Published'
    print_var DIR_PUB_LICENSES
    print_var DIR_PUB_PUBLICDOMAIN
    echo

    echo "${E1}Legal Tools${E0}"
    # licenses
    _count=$(find "${DIR_PUB_LICENSES}" \
        -type f -name 'deed.en.html' \
        | wc -l \
        | sed -e's/[[:space:]]*//g')
    printf "  %-13s%'4d\n" "Licenses" "${_count}"
    # public domain
    _count=$(find "${DIR_PUB_PUBLICDOMAIN}" \
        -type f -name 'deed.en.html' \
        | wc -l \
        | sed -e's/[[:space:]]*//g')
    printf "  ${E4}%-13s%'4d${E0}\n" "Public domain" "${_count}"
    # total
    _count=$(find "${DIR_PUB_LICENSES}" "${DIR_PUB_PUBLICDOMAIN}" \
        -type f -name 'deed.en.html' \
        | wc -l \
        | sed -e's/[[:space:]]*//g')
    printf "  %-13s%'4d\n" "Total" "${_count}"
    echo

    echo "${E1}Documents${E0}"
    # licenses
    _count=$(find "${DIR_PUB_LICENSES}" \
        -type f \( -name '*.html' -o -name 'rdf' \) \
        | wc -l \
        | sed -e's/[[:space:]]*//g')
    printf "  %-13s% '7d\n" "Licenses" "${_count}"
    # public domain
    _count=$(find "${DIR_PUB_PUBLICDOMAIN}" \
        -type f \( -name '*.html' -o -name 'rdf' \) \
        | wc -l \
        | sed -e's/[[:space:]]*//g')
    printf "  ${E4}%-13s% '7d${E0}\n" "Public domain" "${_count}"
    # total
    _count=$(find "${DIR_PUB_LICENSES}" "${DIR_PUB_PUBLICDOMAIN}" \
        -type f \( -name '*.html' -o -name 'rdf' \) \
        | wc -l \
        | sed -e's/[[:space:]]*//g')
    printf "  %-13s% '7d\n" "Total" "${_count}"
    echo
}


source_code() {
    header 'Source code'
    print_var DIR_REPO
    cd "${DIR_REPO}"
    scc \
        --exclude-dir .git,wp-content \
        --no-duplicates \
        --dryness
    echo
}


todo() {
    header 'Deeds & UX translation'
    echo "${E33}TODO${E0}"
    echo
    header 'Legal Code translation'
    echo "${E33}TODO${E0}"
    echo
}


#### MAIN #####################################################################

check_prerequisites
source_code
published_documents
todo
