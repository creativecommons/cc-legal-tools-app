## Helper Scripts

Best run before every commit:
- `./dev/20231009_concatenatemessages.sh` - Concatenate legacy ccEngine
  translations into cc-legal-tools-app


## Importing the existing legal tool text

Note that once the site is up and running in production, the data in the site
will become the canonical source, and the process described here should not
need to be repeated after that.

The implementation is the Django management command
`20231010_load_html_files.py`, which reads from the legacy HTML legal code
files in the [creativecommons/cc-legal-tools-data][repodata] repository, and
populates the database records and translation files.

`load_html_files` uses [BeautifulSoup4][bs4docs] to parse the legacy HTML legal
code:
1. `import_zero_license_html()` for CC0 Public Domain tool
   - HTML is handled specifically (using tag ids and classes) to populate
     translation strings and to be used with specific HTML formatting when
     displayed via template
2. `import_by_40_license_html()` for 4.0 License tools
   - HTML is handled specifically (using tag ids and classes) to populate
     translation strings and to be used with specific HTML formatting when
     displayed via a template
3. `import_by_30_unported_license_html()` for unported 3.0 License tools
   (English-only)
   - HTML is handled specifically to be used with specific HTML formatting
     when displayed via a template
4. `simple_import_license_html()` for everything else
   - HTML is handled generically; only the title and license body are
     identified. The body is stored in the `html` field of the
     `LegalCode` model

[bs4docs]: https://www.crummy.com/software/BeautifulSoup/bs4/doc/
[repodata]: https://github.com/creativecommons/cc-legal-tools-data


### Import Process

This process will read the HTML files from the specified directory, populate
`LegalCode` and `Tool` models, and create the `.po` portable object Gettext
files in [creativecommons/cc-legal-tools-data][repodata].

1. Ensure the Data Repository (see [`../../README.md`](../../README.md) is in
   place
2. Ensure Docker Compose Setup (see [`../../README.md`](../../README.md) is
   complete
3. Clear data in the database
    ```shell
    docker compose exec app ./manage.py clear_license_data
    ```
4. Load legacy HTML in the database
    ```shell
    docker compose exec app ./manage.py load_html_files
    ```
5. Optionally (and only as appropriate):
   1. Commit the `.po` portable object Gettext file changes in
      [creativecommons/cc-legal-tools-data][repodata]
   2. Translation Update Process (see [`../translation.md`](../translation.md)
   3. Generate Static Files (see [`../../README.md`](../../README.md)

[repodata]:https://github.com/creativecommons/cc-legal-tools-data


### Import Dependency Documentation

- [Beautiful Soup Documentation — Beautiful Soup 4 documentation][bs4docs]
  - [lxml - Processing XML and HTML with Python][lxml]
- [Quick start guide — polib documentation][polibdocs]

[bs4docs]: https://www.crummy.com/software/BeautifulSoup/bs4/doc/
[lxml]: https://lxml.de/
[polibdocs]: https://polib.readthedocs.io/en/latest/quickstart.html
