#!/usr/bin/env bash
#
# TODO: stop expanding this bash script and move it to the publishing process
#       so that the information is on an HTML page that is updated with each
#       publish
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
DIR_PUB_LICENSES="$(cd -P -- \
    "${DIR_REPO}/../cc-legal-tools-data/docs/licenses" && pwd -P)"
DIR_PUB_PUBLICDOMAIN="$(cd -P -- \
    "${DIR_REPO}/../cc-legal-tools-data/docs/publicdomain" && pwd -P)"
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
PORTED_NOTE="\
Prior to the international 4.0 version, the licenses were adapted to specific
legal jurisdictions (\"ported\"). This means there are more legal tools for
these earlier versions than there are licenses."

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

print_header() {
    # Print 80 character wide black on white heading with time
    printf "${E30}${E107}# %-69s$(date '+%T') ${E0}\n" "${@}"
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
    local _count _subtotal _ver
    print_header 'Published'
    print_var DIR_PUB_LICENSES
    print_var DIR_PUB_PUBLICDOMAIN
    echo

    echo "${E1}Licenses per license version${E0}"
    printf "  %-7s  %-4s  %s\n" 'Version' 'Count' 'Licenses'
    for _ver in '1.0' '2.0' '2.1' '2.5' '3.0' '4.0'
    do
        _count=$(find "${DIR_PUB_LICENSES}"/*/"${_ver}" \
            -maxdepth 0 -type d \
            | wc -l \
            | sed -e's/[[:space:]]*//g')
        _list=$(find "${DIR_PUB_LICENSES}"/*/"${_ver}" \
            -maxdepth 0 -type d \
            | awk -F'/' '{print $9}' \
            | sort \
            | tr '\n' ' ')
        printf "  %-7s  %'5d  " "${_ver}" "${_count}"
        _chars=0
        for _license in ${_list}
        do
            _len=${#_license}
            [[ -z "${_license}" ]] && continue
            if (( _chars + _len < 61 ))
            then
                printf "%s  " "${_license}"
            else
                _chars=0
                echo
                printf "%18s%s  " ' ' "${_license}"
            fi
            _chars=$(( _chars + _len + 2 ))
        done
        echo
    done
    echo

    echo "${E1}Legal tools per license version${E0}"
    echo "${PORTED_NOTE}"
    # per version
    for _ver in '1.0' '2.0' '2.1' '2.5' '3.0' '4.0'
    do
        _count=$(find "${DIR_PUB_LICENSES}"/*/"${_ver}" \
            -type f -name 'deed.en.html' \
            | wc -l \
            | sed -e's/[[:space:]]*//g')
        if [[ "${_ver}" != '4.0' ]]
        then
            printf "  %-5s%'4d\n" "${_ver}" "${_count}"
        else
            printf "  ${E4}%-5s%'4d${E0}\n" "${_ver}" "${_count}"
        fi
    done
    # total
    _count=$(find "${DIR_PUB_LICENSES}" \
        -type f -name 'deed.en.html' \
        | wc -l \
        | sed -e's/[[:space:]]*//g')
    printf "  %-5s%'4d\n" "Total" "${_count}"
    echo

    echo "${E1}Legal tools${E0}"
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
    print_header 'Source code'
    print_var DIR_REPO
    cd "${DIR_REPO}"
    scc \
        --exclude-dir .git,wp-content \
        --no-duplicates \
        --dryness
    echo
}

todo() {
    print_header 'Deeds & UX translation'
    echo "${E33}TODO${E0}"
    echo
    print_header 'Legal Code translation'
    echo "${E33}TODO${E0}"
    echo
}

#### MAIN #####################################################################

cd "${DIR_REPO}"

check_prerequisites
source_code
published_documents
todo
