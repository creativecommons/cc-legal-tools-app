#!/bin/bash
#
# Concatenate legacy ccEngine translation into cc-licenses
#
set -o errtrace
set -o nounset

# Change directory to cc-licenses (grandparent directory of this script)
cd ${0%/*}/../

if ! docker-compose exec app true 2>/dev/null; then
    echo 'The app container/services is not avaialable.'
    echo 'First run `docker-compose up`.'
    exit 1
fi 1>&2
if [[ ! -d ../cc.i18n ]]; then
    echo -n 'The legacy localization repository'
    echo ' (https://github.com/creativecommons/cc.i18n)'
    echo  'must be checked out adjacent to this one.'
    exit 1
fi 1>&2
if ! command -v msgcat &>/dev/null; then
    echo -n 'The `msgcat` command is unavailable. It is provided by the'
    echo ' gettext package on'
    echo 'apt/dpkg based Linux and from Homebrew on macOS.'
    exit 1
fi 1>&2

printf "\e[1m\e[7m %-80s\e[0m\n" 'Django Managment nofuzzy_makemessages'
docker-compose exec app coverage run manage.py \
    nofuzzy_makemessages \
        --all \
        --symlinks \
        --ignore **/includes/legalcode_licenses_4.0.html \
        --ignore **/includes/legalcode_zero.html \
        --no-obsolete
echo

printf "\e[1m\e[7m %-80s\e[0m\n" 'Concatenate legacy ccEngine translations'
for _locale_dir in $(find ../cc-licenses-data/locale/* -maxdepth 0 -type d); do
    _locale="${_locale_dir##*/}"
    echo "${_locale}"
    _po_current="${_locale_dir}/LC_MESSAGES/django.po"
    echo "    ${_po_current}"
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
    if [[ -d "../cc.i18n/cc/i18n/po/${_legacy_locale_1}" ]]; then
        _po_legacy_1="../cc.i18n/cc/i18n/po/${_legacy_locale_1}/cc_org.po"
        echo "    ${_po_legacy_1}"
    else
        echo '    *** NOT FOUND ***'
        echo 'Invalid legacy location. Aborting.' 1>&2
        exit 1
    fi
    if [[ -d "../cc.i18n/cc/i18n/po/${_legacy_locale_2}" ]]; then
        _po_legacy_2="../cc.i18n/cc/i18n/po/${_legacy_locale_2}/cc_org.po"
        echo "    ${_po_legacy_2}"
    fi

    msgcat \
        --output-file="${_po_current}" \
        --use-first \
        --sort-output \
        ${_po_current} \
        ${_po_legacy_1} \
        ${_po_legacy_2}
done
echo

printf "\e[1m\e[7m %-80s\e[0m\n" 'Django Managment nofuzzy_makemessages'
docker-compose exec app coverage run manage.py \
    nofuzzy_makemessages \
        --all \
        --symlinks \
        --ignore **/includes/legalcode_licenses_4.0.html \
        --ignore **/includes/legalcode_zero.html \
        --no-obsolete
echo

printf "\e[1m\e[7m %-80s\e[0m\n" 'Django Managment compilemessages'
docker-compose exec app coverage run manage.py \
    compilemessages
echo
