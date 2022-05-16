#!/bin/bash
#
# Run Django Management nofuzzy_makemessages with helpful options (including
# excluding legalcode) and compilemessages
#
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
    echo 'GNU sed is required. If on macOS install `gnu-sed` via brew.' 1>&2
    exit 1
fi
if ! docker compose exec app true 2>/dev/null; then
    echo 'The app container/services is not avaialable.' 1>&2
    echo 'First run `docker compose up`.' 1>&2
    exit 1
fi

printf "\e[1m\e[7m %-80s\e[0m\n" 'Django Managment nofuzzy_makemessages'
docker compose exec app coverage run manage.py \
    nofuzzy_makemessages \
        --all \
        --symlinks \
        --ignore **/includes/legalcode_licenses_4.0.html \
        --ignore **/includes/legalcode_menu_sidebar.html \
        --ignore **/includes/legalcode_zero.html \
        --no-obsolete \
        --verbosity 2
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
        gsed -e"s#${creation_new}#${creation_old}#" -i "${_pofile}"
    fi
done
popd >/dev/null
echo

printf "\e[1m\e[7m %-80s\e[0m\n" 'Django Management format_pofile'
docker compose exec app ./manage.py format_pofile locale
echo

printf "\e[1m\e[7m %-80s\e[0m\n" 'Django Managment compilemessages'
docker compose exec app coverage run manage.py \
    compilemessages
echo
