Develop and deploy cc_licenses
============================================================

Contents:

.. toctree::
   :maxdepth: 2

   provisioning
   settings
   translation

NOTES TO ADD SOMEWHERE:

Languages and locales
---------------------

This project needs a LOT of locales installed because of how many
languages. On Ubuntu, we might want to just do something like this
to install them all::

    sudo apt-get install $(apt-cache search --names-only language-pack | cut -d ' ' -f 1  | egrep -v -e 'language-pack-kde|language-pack-gnome')
    sudo
