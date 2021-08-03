# Translation

## Resources

This project uses the standard [Django translation
mechanisms](https://docs.djangoproject.com/en/stable/topics/i18n/).

We use [Transifex](https://www.transifex.com) to make it easy for translators
to convert the English strings in our interface to proper translated strings in
other languages.

## What goes in version control?

While the `.po` files can be regenerated easily by running `make makemessages`
again for English or `make pullmessages` for the translated languages, we still
store them in Git to make it easier to keep an eye on changes, and revert if
needed. That way we are less likely to accidentally make a mistake and delete
huge swaths of messages without noticing it.

We also store the `.mo` files in Git because those are what Django gets the
translated messages from at runtime.

## First time setup

Steps 1 and 2 only need to be done once. Step 3 would only need to be repeated
if you were to add a new PO file to be translated. An example would be if you
were to add frontend JS translations.

1. Create a project on Transifex. This documentation will assume that you named
   it `cc_licenses`.

2. In the repo, create your Transifex config file:

        tx init

3. Tell Transifex where your files are, and how to link them to Transifex:

        tx set --auto-local -r cc_licenses.deeds_ux \
            'locale/<lang>/LC_MESSAGES/deeds_ux.po' \
            --source-lang en --type PO --execute

4. Commit this to the repo:

        git commit -m "Setup Transifex translation" .tx
        git push

## Updating messages on Transifex

Anytime there have been changes to the messages in the code or templates, a
developer should update the messages on Transifex as follows:

1. Make sure you have the latest code from main:

        git checkout main
        git pull

2. Regenerate the English (only) .po files:

        docker-compose run app ./manage.py makemessages

3. Run `git diff` and make sure the changes look reasonable.

4. If so, commit the updated .po file to main and push it upstream:

        git commit -m "Updated messages" locale/en/LC_MESSAGES/*.po
        git push

5. [Push][transifex-push] the updated source file to Transifex:

        docker-compose run app ./manage.py pushmessages

[transifex-push]: http://support.transifex.com/customer/portal/articles/996211-pushing-new-translations

## Updating translations from Transifex

Anytime translations on Transifex have been updated, someone should update our
translation files on the main branch as follows:

1. Make sure you have the latest code from main:

        git checkout main
        git pull

2. [Pull][transifex-pull] the updated .po files from Transifex:

        docker-compose run app ./manage.py pullmessages

3. Use `git diff` to see if any translations have actually changed. If not, you
   can stop here.

4. Look at the diffs to see if the changes look reasonable. E.g. if
   translations have vanished, figure out why before proceeding.

5. Compile the messages to .mo files:

        docker-compose run app ./manage.py compilemessages

   If you get any errors due to badly formatted translations, open issues on
   Transifex and work with the translators to get them fixed, then start this
   process over.

6. Run your test suite one more time:

        docker-compose run app ./manage.py test

7. Commit and push the changes:

        git commit -m "Updated translations" locale/*/LC_MESSAGES/*.po locale/*/LC_MESSAGES/*.mo
        git push

[transifex-pull]: http://support.transifex.com/customer/portal/articles/996157-getting-translations
