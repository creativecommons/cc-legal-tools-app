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
E30="$(printf "\e[30m")"      # black foreground
E31="$(printf "\e[31m")"      # red foreground
E33="$(printf "\e[33m")"      # yellow foreground
E47="$(printf "\e[47m")"      # white background
E97="$(printf "\e[97m")"      # bright white foreground
E100="$(printf "\e[100m")"    # bright black (gray) background
E107="$(printf "\e[107m")"    # bright white background
REPO_DIR="$(cd -P -- "${0%/*}/.." && pwd -P)"
DATA_DIR="$(cd -P -- "${REPO_DIR}/../cc-legal-tools-data" && pwd -P)"

#### FUNCTIONS ################################################################


error_exit() {
    # Echo error message and exit with error
    echo -e "${E31}ERROR:${E0} ${*}" 1>&2
    exit 1
}

extract_label_orig() {
    local _template="${1}"
    LABEL_ORIG=$(gsed --null-data --regexp-extended \
        -e"s|.*<a[^>]*id=\"${KEY_LEGACY}[^\"]*\"[^>]*>([^<]+)</a>.*|\\1|" \
        "${REPO_DIR}/templates/includes/deed_body_${_template}.html")
}


header1() {
    # Print 80 character wide black on white heading with time
    printf "${E30}${E107} %-71s$(date '+%T') ${E0}\n" "${@}"
}


header2() {
    # Print 80 character wide black on white heading with time
    printf "${E30}${E47} %-71s$(date '+%T') ${E0}\n" "${@}"
}


modify_template() {
    local _template="${1}"
    gsed --null-data --regexp-extended \
        -e"s|<a[^>]*id=\"${KEY_LEGACY}[^\"]*\"[^>]*>([^<]+)</a>|<a href=\"#ref-${KEY}\" id=\"src-${KEY}\">\\1</a>|" \
        --in-place "${REPO_DIR}/templates/includes/deed_body_${_template}.html"
}


print_key_val() {
    printf "${E97}${E100}%18s${E0} %s\n" "${1}:" "${2}"
}


print_var() {
    print_key_val "${1}" "${!1}"
}


#### MAIN #####################################################################

ITEMS='
licenses mediation-and-arbitration
licenses appropriate-credit
licenses indicate-changes
licenses same-license
licenses commercial-purposes
licenses some-kinds-of-mods
licenses technological-measures
licenses exception-or-limitation
licenses publicity-privacy-or-moral-rights
mark all-jurisdictions
mark-zero publicity-rights
mark moral-rights
mark-zero endorsement
'

cd "${REPO_DIR}"
git restore templates

cd "${DATA_DIR}"
git restore locale

header1 'Unwrap Deeds & UX portable object Gettext Files'
cd "${REPO_DIR}"
docker compose exec app ./manage.py format_pofile -w9999 locale \
    >/dev/null
echo 'message lines wrapped at 9999 characters'
sleep 1
echo

IFS=$'\n'
for _line in ${ITEMS}
do
    IFS=' ' read -r TEMPLATE KEY <<< "${_line}"
    KEY_LEGACY=${KEY//-/_}
    echo
    header1 "${KEY}"
    print_var KEY_LEGACY
    echo

    if [[ "${TEMPLATE}" == 'mark-zero' ]]
    then
        header2 "APP/templates/includes/deed_body_mark.html"
        header2 "APP/templates/includes/deed_body_zero.html"
    else
        header2 "APP/templates/includes/deed_body_${TEMPLATE}.html"
    fi
    echo -n 'extracting LABEL_ORIG: '
    if [[ "${TEMPLATE}" == 'mark-zero' ]]
    then
        extract_label_orig mark
    else
        extract_label_orig "${TEMPLATE}"
    fi
    if echo "${LABEL_ORIG}" | grep --fixed-strings --quiet '{%'
    then
        error_exit 'LABEL_ORIG extraction failed'
    fi
    echo "${LABEL_ORIG}"

    echo 'modifying template'
    if [[ "${TEMPLATE}" == 'mark-zero' ]]
    then
        modify_template mark
        modify_template zero
    else
        modify_template "${TEMPLATE}"
    fi
    echo

    cd "${DATA_DIR}"
    for _dir in locale/*
    do
        PO="${_dir}/LC_MESSAGES/django.po"
        header2 "DATA/${PO}"

        echo -n 'extracting LABEL_TRANS: '
        cd "${DATA_DIR}"
        if grep  --quiet \
            "msgstr.*<a[^>]*id=\\\\\"${KEY_LEGACY}[^\"]*\\\\\"" "${PO}"
        then
            LABEL_TRANS=$(gsed --null-data --regexp-extended \
                -e"s|.*msgstr[^\n]+<a[^>]*id=\\\\\"${KEY_LEGACY}[^\"]*\\\\\"[^>]*>[[:space:]]*([^<]+)[[:space:]]*</[[:space:]]*a>.*|\\1|" \
                "${PO}")
        else
            LABEL_TRANS=''
        fi

        if [[ -n "${LABEL_TRANS}" ]]
        then
            if echo "${LABEL_TRANS}" \
                | grep --fixed-strings --quiet 'Project-Id-Version'
            then
                error_exit 'LABEL_TRANS extraction failed'
            fi
            echo "${LABEL_TRANS}"
            echo 'adding label translation'
            gsed --null-data --regexp-extended \
                -e"s|msgid \"${LABEL_ORIG}\"\nmsgstr \"\"\n|msgid \"${LABEL_ORIG}\"\nmsgstr \"${LABEL_TRANS}\"\n|" \
                --in-place "${PO}"
        else
            echo "${E33}NOT FOUND${E0}"
        fi

        echo 'modifying src anchor'
        cd "${DATA_DIR}"
        gsed --regexp-extended \
            -e"s|<a[^>]*id=\\\\\"${KEY_LEGACY}[^\"]*\\\\\"[^>]*>[[:space:]]*([^<]+)[[:space:]]*</[[:space:]]*a>|<a href=\\\\\"#ref-${KEY}\\\\\" id=\\\\\"src-${KEY}\\\\\">\\1</a>|g" \
            --in-place "${PO}"
        echo

    done
done

header1 'Re-wrap Deeds & UX portable object Gettext Files'
cd "${REPO_DIR}"
docker compose exec app ./manage.py format_pofile locale \
    >/dev/null
echo 'message lines wrapped at 78 characters'
echo
