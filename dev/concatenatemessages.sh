#!/bin/bash
#
# Concatenate legacy ccEngine translations into cc-legal-tools-app
set -o errexit
set -o errtrace
set -o nounset

# Change directory to cc-legal-tools-app (grandparent directory of this script)
cd ${0%/*}/../

if command -v gsed >/dev/null; then
    _sed=gsed
elif sed --version >/dev/null; then
    _sed=sed
else
    echo 'GNU sed is required. If on macOS install via `gnu-sed`' 1>&2
    exit 1
fi
if ! docker compose exec app true 2>/dev/null; then
    echo 'The app container/services is not available.'
    echo 'First run `docker compose up`.'
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

printf "\e[1m\e[7m %-80s\e[0m\n" 'Django Management nofuzzy_makemessages'
docker compose exec app ./manage.py \
    nofuzzy_makemessages \
        --all \
        --symlinks \
        --ignore **/includes/legalcode_licenses_4.0.html \
        --ignore **/includes/legalcode_menu_sidebar.html \
        --ignore **/includes/legalcode_zero.html \
        --no-obsolete
echo

printf "\e[1m\e[7m %-80s\e[0m\n" 'Clean-up legacy ccEngine translations'
for _file in ../cc.i18n/cc/i18n/po/*/cc_org.po; do
    echo "${_file}"
    # Generic Patterns:
    #    1. Deed to Share & Deed to Remix: use HTML entity
    #    2. Deed to Share & Deed to Remix: clean-up whitespace
    #    3. Deed Share & Deed Adapt: clean-up whitespace
    #    4. Deed Attribution Description: clean-up whitespace
    #    5. certification unit name: clean-up whitespace
    # Translation Clean-up Patterns:
    #    6. Arabic Deed to Share and In Particular: fix broken closing tag
    #    7. Arabic Deed to Remix: clean-up whitespace
    #    8. Bulgarian to Remix: clean-up whitespace
    #    9. Esperanto: use correct HTML entity
    #   10. Korean: remove File Separator control character
    #   11. Romanian: clean-up whitespace
    #   12. Spanish: clean-up whitespace
    "${_sed}" \
        -e's#strong> \(–\|-\|—\|--\)#strong> \&mdash; #g' \
        -e's#strong> &mdash;  #strong> \&mdash; #g' \
        -e's#strong>  &mdash;#strong> \&mdash;#g' \
        -e's#span>.  You#span>. You#g' \
        -e's#on United States law) \\n"#on United States law) "#' \
        -e's#msgstr " <strong>#msgstr "<strong>#' \
        -e's#<strong>\([^<]\+\)<strong>#<strong>\1</strong>#' \
        -e's#strong> да#strong>да#' \
        -e's#strong>&nbsp;— #strong> \&mdash; #g' \
        -e's#\x1C##g' \
        -e's#strong> remixezi#strong>remixezi#g' \
        -e's# Adaptar#Adaptar#g' \
        -i "${_file}"
done

printf "\e[1m\e[7m %-80s\e[0m\n" 'Concatenate legacy ccEngine translations'
for _locale_dir in $(find ../cc-legal-tools-data/locale/* -maxdepth 0 -type d); do
    _locale="${_locale_dir##*/}"
    echo "${_locale}"
    _po_current="${_locale_dir}/LC_MESSAGES/django.po"
    echo "    ${_po_current}"
    _legacy_locale_1='.INVALID.SHOULD_NOT_EXIST'
    _legacy_locale_2='.INVALID.SHOULD_NOT_EXIST'
    _po_legacy_1=''
    _po_legacy_2=''
    _po_tmp=''
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
        msgcat \
            --output-file="${_po_current}" \
            --use-first \
            --sort-output \
            ${_po_current} \
            ${_po_legacy_1}
    fi

    if [[ -d "../cc.i18n/cc/i18n/po/${_legacy_locale_2}" ]]; then
        _po_legacy_2="../cc.i18n/cc/i18n/po/${_legacy_locale_2}/cc_org.po"
        echo "    ${_po_legacy_2}"
        msgcat \
            --output-file="${_po_current}" \
            --use-first \
            --sort-output \
            ${_po_current} \
            ${_po_legacy_2}
    fi

    if [[ -f "tmp/locale/${_locale}/tmp.po" ]]; then
        _po_tmp="tmp/locale/${_locale}/tmp.po"
        echo "    ${_po_tmp}"
        msgcat \
            --output-file="${_po_current}" \
            --use-first \
            --sort-output \
            ${_po_current} \
            ${_po_tmp}
    fi
done
echo

printf "\e[1m\e[7m %-80s\e[0m\n" 'Django Management nofuzzy_makemessages'
docker compose exec app ./manage.py \
    nofuzzy_makemessages \
        --all \
        --symlinks \
        --ignore **/includes/legalcode_licenses_4.0.html \
        --ignore **/includes/legalcode_menu_sidebar.html \
        --ignore **/includes/legalcode_zero.html \
        --no-obsolete
echo

printf "\e[1m\e[7m %-80s\e[0m\n" 'Restore POT-Creation-Date'
pushd ../cc-legal-tools-data/ >/dev/null
for _pofile in $(git diff --name-only); do
    [[ "${_pofile}" =~ django\.po$ ]] || continue
    creation_old="$(git diff "${_pofile}" | grep '^-"POT-Creation-Date')"
    creation_old="${creation_old:2:${#creation_old}-5}"
    creation_new="$(git diff "${_pofile}" | grep '^+"POT-Creation-Date')"
    creation_new="${creation_new:2:${#creation_new}-5}"
    if [[ -n "${creation_old}" ]] && [[ -n "${creation_new}" ]]; then
        echo "updating ${_pofile}"
        echo "        pattern: ${creation_new}"
        echo "    replacement: ${creation_old}"
        gsed -e"s#${creation_new}#${creation_old}#" -i "${_pofile}"
    fi
done
popd >/dev/null
echo

printf "\e[1m\e[7m %-80s\e[0m\n" 'Update PO-Revision-Date'
revision_new="PO-Revision-Date: $(date -u '+%F %T+00:00')"
pushd ../cc-legal-tools-data/ >/dev/null
for _pofile in $(git diff --name-only); do
    [[ "${_pofile}" =~ django\.po$ ]] || continue
    revision_old="$(grep '^"PO-Revision-Date' "${_pofile}")"
    revision_old="${revision_old:1:${#revision_old}-4}"
    if [[ -n "${revision_old}" ]] && [[ -n "${revision_new}" ]]; then
        echo "updating ${_pofile}"
        echo "        pattern: ${revision_old}"
        echo "    replacement: ${revision_new}"
        gsed -e"s#${revision_old}#${revision_new}#" -i "${_pofile}"
    fi
done
popd >/dev/null
echo

printf "\e[1m\e[7m %-80s\e[0m\n" 'Django Management format_pofile'
docker compose exec app ./manage.py format_pofile locale
echo

printf "\e[1m\e[7m %-80s\e[0m\n" 'Reminders'
echo '- Changes were made to ccEngine repository (../cc.i18n). It is probably'
echo '  best if you restore it.'
echo '- Next run the following Django management commands:'
echo '  1. normalize_translations'
echo '  2. compile_messages'
