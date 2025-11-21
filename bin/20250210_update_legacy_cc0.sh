#!/bin/bash
#
# Update legacy CC0 translation strings so that the string for the Other
# Information first paragraph. For more information, see:
#   https://github.com/creativecommons/cc-legal-tools-app/issues/502
#
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
E30="$(printf "\e[30m")"      # black foreground
E31="$(printf "\e[31m")"      # red foreground
E97="$(printf "\e[97m")"      # bright white foreground
E100="$(printf "\e[100m")"    # bright black (gray) background
E107="$(printf "\e[107m")"    # bright white background
DIR_APP="$(cd -P -- "${0%/*}/.." && pwd -P)"
DIR_PARENT="$(cd -P -- "${DIR_APP}/.." && pwd -P)"
DIR_LEGACY="$(cd -P -- "${DIR_PARENT}/cc.i18n" && pwd -P)"
DIR_DATA="$(cd -P -- "${DIR_PARENT}/cc-legal-tools-data" && pwd -P)"
SED=''

#### FUNCTIONS ################################################################


check_prerequisites() {
    local _m1 _m2 _m3
    print_header 'Check prerequisites'

    # cc-legal-tools-data repositry adjacent
    if [[ ! -d "${DIR_DATA}" ]]
    then
        _m1='The cc-legal-tools-data repository (see README.md) must be'
        _m2=' cloned adjacent to this one.'
        error_exit "${_m1}${_m2}"
    fi

    # Legacy ccEngine localization repositry adjacent
    if [[ ! -d "${DIR_LEGACY}" ]]
    then
        _m1='The legacy ccEngine localization repository'
        _m2=' (https://github.com/creativecommons/cc.i18n) must be cloned'
        _m3=' adjacent to this one.'
        error_exit "${_m1}${_m2}${_m3}"
    fi

    # GNU sed available
    if command -v gsed >/dev/null
    then
        SED=$(command -v gsed)
    elif sed --version >/dev/null
    then
        SED=$(command -v sed)
    else
        # shellcheck disable=SC2016
        error_exit \
            'GNU sed is required. If on macOS install `gnu-sed` via brew.'
    fi

    # gettext available
    if ! command -v msgcat &>/dev/null
    then
        # shellcheck disable=SC2006,SC2016
        _m1="The `msgcat` command isn't available. It is provided by the"
        _m2=' gettext package on apt/dpkg based Linux and from Homebrew on'
        _m3=' macOS.'
        error_exit "${_m1}${_m2}${_m3}"
    fi

    # Docker app service running
    if ! docker compose exec app true 2>/dev/null
    then
        _m1="The app container/services isn't avaialable. First run"
        # shellcheck disable=SC2016
        _m2=' `docker compose up`.'
        error_exit "${_m1}${_m2}"
    fi

    print_var DIR_PARENT
    print_var DIR_APP
    print_var DIR_DATA
    print_var DIR_LEGACY
    echo
}


compile_mofiles() {
    print_header 'Compile mo files'
    docker compose exec app python manage.py compilemessages \
        | "${SED}" --unbuffered \
            -e'/^File.*is already compiled/d' \
            -e's|/home/cc/||'
    echo
}


concatenate_translations() {
    local _dir_legacy_po _legacy_locale_1 _legacy_locale_2 _locale \
        _po_current _po_legacy_1 _po_legacy_2
    print_header 'Concatenate legacy ccEngine translations'
    _dir_legacy_po="${DIR_LEGACY}/cc/i18n/po"
    for _locale_dir in  "${DIR_DATA}"/locale/*
    do
        [[ -d "${_locale_dir}" ]] || continue
        _locale="${_locale_dir##*/}"
        echo "${E1}${_locale}${E0}"
        _po_current="${_locale_dir}/LC_MESSAGES/django.po"
        echo "    [current] ${_po_current#"${DIR_PARENT}/"}"
        _legacy_locale_1='.INVALID.SHOULD_NOT_EXIST'
        _legacy_locale_2='.INVALID.SHOULD_NOT_EXIST'
        _po_legacy_1=''
        _po_legacy_2=''
        case ${_locale} in
            es)
                _legacy_locale_1="${_locale}"
                _legacy_locale_2='es_ES'
                ;;
            kn)
                _legacy_locale_1="${_locale}"
                _legacy_locale_2='kn_IN'
                ;;
            oc_Aranes)
                _legacy_locale_1='oc'
                ;;
            tr)
                _legacy_locale_1="${_locale}"
                _legacy_locale_2='tr_TR'
                ;;
            zh_Hans)
                _legacy_locale_1='zh-Hans'
                _legacy_locale_2='zh'
                ;;
            zh_Hant)
                _legacy_locale_1='zh-Hant'
                _legacy_locale_2='zh_TW'
               ;;
            *)
               _legacy_locale_1="${_locale}"
               ;;
        esac

        if [[ -d "${_dir_legacy_po}/${_legacy_locale_1}" ]]; then
            _po_legacy_1="${_dir_legacy_po}/${_legacy_locale_1}/cc_org.po"
            echo "    [legacy1] ${_po_legacy_1#"${DIR_PARENT}/"}"
            msgcat \
                --output-file="${_po_current}" \
                --use-first \
                --sort-output \
                "${_po_current}" \
                "${_po_legacy_1}"
        fi

        if [[ -d "${_dir_legacy_po}/${_legacy_locale_2}" ]]; then
            _po_legacy_2="${_dir_legacy_po}/${_legacy_locale_2}/cc_org.po"
            echo "    [legacy2] ${_po_legacy_2#"${DIR_PARENT}/"}"
            msgcat \
                --output-file="${_po_current}" \
                --use-first \
                --sort-output \
                "${_po_current}" \
                "${_po_legacy_2}"
        fi

    done
    echo
}


error_exit() {
    # Echo error message and exit with error
    echo -e "${E31}ERROR:${E0} ${*}" 1>&2
    exit 1
}


format_pofiles() {
    print_header 'Django Management format_pofile'
    docker compose exec app python manage.py format_pofile locale \
        | "${SED}" --unbuffered \
            -e's|^/home/cc/||'
    echo
}


make_messages() {
    print_header 'Django Management nofuzzy_makemessages'
    # shellcheck disable=SC2035
    docker compose exec app python manage.py \
        nofuzzy_makemessages \
            --all \
            --symlinks \
            --ignore **/includes/legalcode_licenses_4.0.html \
            --ignore **/includes/legalcode_contextual_menu.html \
            --ignore **/includes/legalcode_zero.html \
            --add-location full \
            --no-obsolete \
        | "${SED}" --unbuffered \
            -e"s|^/home/cc/||"
    echo
}


restore_update_dates() {
    local _date_new _date_old _pofile
    pushd "${DIR_DATA}" >/dev/null

    print_header 'Restore POT-Creation-Date'
    for _pofile in $(git diff --name-only);
    do
        [[ "${_pofile}" =~ django\.po$ ]] || continue
        _date_old="$(git diff "${_pofile}" | grep '^-"POT-Creation-Date')" \
            || continue
        _date_old="${_date_old:2:${#_date_old}-5}"
        _date_new="$(git diff "${_pofile}" | grep '^+"POT-Creation-Date')"
        _date_new="${_date_new:2:${#_date_new}-5}"
        if [[ -n "${_date_old}" ]] && [[ -n "${_date_new}" ]]
        then
            echo "${E1}updating ${_pofile}${E0}"
            echo "        pattern: ${_date_new}"
            echo "    replacement: ${_date_old}"
            "${SED}" -e"s#${_date_new}#${_date_old}#" -i "${_pofile}"
        fi
    done
    echo

    print_header 'Update PO-Revision-Date'
    _date_new="PO-Revision-Date: $(date -u '+%F %T+00:00')"
    for _pofile in $(git diff --name-only)
    do
        [[ "${_pofile}" =~ django\.po$ ]] || continue
        _date_old="$(grep '^"PO-Revision-Date' "${_pofile}")"
        _date_old="${_date_old:1:${#_date_old}-4}"
        if [[ -n "${_date_old}" ]] && [[ -n "${_date_new}" ]]
        then
            echo "${E1}updating ${_pofile}${E0}"
            echo "        pattern: ${_date_old}"
            echo "    replacement: ${_date_new}"
            "${SED}" -e"s#${_date_old}#${_date_new}#" -i "${_pofile}"
        fi
    done
    echo

    popd >/dev/null
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


show_reminders() {
    print_header 'Reminders'
    echo '- Changes were made to ccEngine repository (../cc.i18n). It is'
    echo '  probably best if you restore it.'
    echo '- Next run the following Django management commands:'
    echo '  1. normalize_translations'
    echo '  2. compilemessages'
    echo
}


update_legacy_cc0() {
    # <a href=\"http://wiki.creativecommons.org/Frequently_Asked_Questions#When_are_publicity_rights_relevant.3F\" class=\"helpLink\" id=\"publicity_rights\">publicity or privacy</a>
    #
    # <a href=\"#ref-publicity-rights\" id=\"src-publicity-rights\">publicity or privacy</a>
    local _match _r1 _r2 _replace
    pushd "${DIR_LEGACY}" >/dev/null
    _match='<a[^>]+publicity_rights[^>]+>([^<]+)</a>'
    _r1='<a href=\\"#ref-publicity-rights\\" id=\\"src-publicity-rights\\">'
    _r2='\1</a>'
    _replace="${_r1}${_r2}"
    print_header 'Update legacy CC0 deed translation string'
    cd "${DIR_LEGACY}"
    for _po in cc/i18n/po/*/cc_org.po
    do
        echo "cc.i18n/${_po}"
        # replace dos line endings with unix line endings to address error:
        #     warning: internationalized messages should not contain the '\r'
        #              escape sequence
        "${SED}" --in-place \
            -e 's/[\]r[\]n/\\n/' \
            "${_po}"
        # clean-up
        msgcat --output-file="${_po}" \
            --no-location --no-wrap --sort-output \
            "${_po}"
        "${SED}" --in-place \
            -e "/^#, python-format/d" \
            -e's#\x1C##g' \
            "${_po}"
        # update
        "${SED}" --in-place --regexp-extended \
            -e "s|${_match}|${_replace}|g" \
            "${_po}"
    done
    echo
    popd >/dev/null
}


#### MAIN #####################################################################

check_prerequisites
update_legacy_cc0
concatenate_translations
restore_update_dates
make_messages
format_pofiles
compile_mofiles
show_reminders
