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
if ! command -v msgcat; then
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
        --no-obsolete \
        --verbosity 2
echo

printf "\e[1m\e[7m %-80s\e[0m\n" 'Concatenate legacy ccEngine translations'
for _locale_dir in $(find ../cc-licenses-data/locale/* -maxdepth 0 -type d); do
    _locale="${_locale_dir##*/}"
    echo "${_locale}"
    _po_current="${_locale_dir}/LC_MESSAGES/django.po"
    echo "    ${_po_current}"
    case ${_locale} in
        oc_Aranes) _legacy_locale='oc';;
        zh_Hans) _legacy_locale='zh-Hans';;
        zh_Hant) _legacy_locale='zh-Hant';;
        *) _legacy_locale="${_locale}";;
    esac
    if [[ -d "../cc.i18n/cc/i18n/po/${_legacy_locale}" ]]; then
        _po_legacy="../cc.i18n/cc/i18n/po/${_legacy_locale}/cc_org.po"
        echo "    ${_po_legacy}"
    else
        echo '    *** NOT FOUND ***'
        exit 1
    fi
    msgcat \
        --output-file="${_po_current}" \
        --use-first \
        --sort-output \
        "${_po_current}" \
        "${_po_legacy}"
done
echo

printf "\e[1m\e[7m %-80s\e[0m\n" 'Django Managment nofuzzy_makemessages'
docker-compose exec app coverage run manage.py \
    nofuzzy_makemessages \
        --all \
        --symlinks \
        --ignore **/includes/legalcode_licenses_4.0.html \
        --ignore **/includes/legalcode_zero.html \
        --no-obsolete \
        --verbosity 2
echo

printf "\e[1m\e[7m %-80s\e[0m\n" 'Django Managment compilemessages'
docker-compose exec app coverage run manage.py \
    compilemessages
echo
