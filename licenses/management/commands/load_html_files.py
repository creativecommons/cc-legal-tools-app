import os
import sys
from argparse import ArgumentParser

from bs4 import BeautifulSoup, Tag
from django.core.management import BaseCommand
from polib import POEntry, POFile

from i18n import DEFAULT_LANGUAGE_CODE
from licenses.bs_utils import inner_html, name_and_text, nested_text, text_up_to
from licenses.models import LegalCode, License
from licenses.utils import parse_legalcode_filename, validate_dictionary_is_all_text


class Command(BaseCommand):
    """
    Read the HTML files from a directory, figure out which licenses they are, and create
    and populate the corresponding License and LegalCode objects.  Then parse the HTML
    and create or update the .po and .mo files.
    """

    def add_arguments(self, parser: ArgumentParser):
        parser.add_argument("input_directory")

    def handle(self, input_directory, **options):
        # We're just doing the BY 4.0 licenses for now
        licenses_created = 0
        legalcodes_created = 0

        # We'll create LegalCode and License objects for all the by* HTML files.
        # (We're only going to parse the HTML for the 4.0 ones for now, though.)
        html_filenames = sorted(
            [
                f
                for f in os.listdir(input_directory)
                if f.startswith("by") and f.endswith(".html")
            ]
        )
        for filename in html_filenames:
            metadata = parse_legalcode_filename(filename)

            basename = os.path.splitext(filename)[0]
            fullpath = os.path.join(input_directory, filename)

            license_code = metadata["license_code"]
            version = metadata["version"]
            jurisdiction_code = metadata["jurisdiction_code"]
            language_code = metadata["language_code"] or DEFAULT_LANGUAGE_CODE
            about_url = metadata["about_url"]

            # These are valid for BY only
            license_code_parts = license_code.split("-")
            if "by" in license_code_parts:
                permits_derivative_works = "nd" not in license_code_parts
                permits_reproduction = "nd" not in license_code_parts
                permits_distribution = "nd" not in license_code_parts
                permits_sharing = "nd" not in license_code_parts
                requires_share_alike = "sa" in license_code_parts
                requires_notice = True
                requires_attribution = True
                requires_source_code = False  # GPL, LGPL only, I think
                prohibits_commercial_use = "nc" in license_code_parts
                prohibits_high_income_nation_use = False  # Not any BY 4.0 license
            else:
                raise NotImplementedError(basename)

            # Find or create a License object
            license, created = License.objects.get_or_create(
                about=about_url,
                defaults=dict(
                    license_code=license_code,
                    version=version,
                    jurisdiction_code=jurisdiction_code,
                    permits_derivative_works=permits_derivative_works,
                    permits_reproduction=permits_reproduction,
                    permits_distribution=permits_distribution,
                    permits_sharing=permits_sharing,
                    requires_share_alike=requires_share_alike,
                    requires_notice=requires_notice,
                    requires_attribution=requires_attribution,
                    requires_source_code=requires_source_code,
                    prohibits_commercial_use=prohibits_commercial_use,
                    prohibits_high_income_nation_use=prohibits_high_income_nation_use,
                ),
            )
            if created:
                licenses_created += 1
            # Find or create a LegalCode object
            legalcode, created = LegalCode.objects.get_or_create(
                license=license,
                language_code=language_code,
                defaults=dict(html_file=fullpath,),
            )

            if created:
                legalcodes_created += 1
        print(
            f"Created {licenses_created} licenses and {legalcodes_created} translation objects"
        )

        # NOW parse the HTML and output message files

        # We're just doing these license codes and version 4.0 for now.
        LICENSE_CODES = ["by", "by-sa", "by-nc-nd", "by-nc", "by-nc-sa", "by-nd"]
        version = "4.0"

        # What are the language codes we have translations for?
        language_codes = list(
            LegalCode.objects.filter(
                license__version=version, license__license_code__startswith="by"
            )
            .order_by("language_code")
            .distinct("language_code")
            .values_list("language_code", flat=True)
        )

        english_by_license_code = {}

        # We have to do English first. Django gets confused if you try to load
        # another language and it can't find English, I guess it's looking for
        # something to fall back to.
        language_codes.remove("en")
        for language_code in ["en"] + language_codes:
            for license_code in LICENSE_CODES:
                legalcode = LegalCode.objects.get(
                    license__license_code=license_code,
                    license__version=version,
                    language_code=language_code,
                )

                print(legalcode.html_file)
                with open(legalcode.html_file, "r", encoding="utf-8") as f:
                    content = f.read()

                messages_text = self.import_by_40_license_html(
                    content, license_code, language_code
                )

                if language_code == "en":
                    english_by_license_code[license_code] = messages_text

                pofile = POFile()
                pofile.metadata = {
                    "Project-Id-Version": f"{license_code}-{version}",
                    # 'Report-Msgid-Bugs-To': 'you@example.com',
                    # 'POT-Creation-Date': '2007-10-18 14:00+0100',
                    # 'PO-Revision-Date': '2007-10-18 14:00+0100',
                    # 'Last-Translator': 'you <you@example.com>',
                    # 'Language-Team': 'English <yourteam@example.com>',
                    "Language": language_code,
                    "MIME-Version": "1.0",
                    "Content-Type": "text/plain; charset=utf-8",
                    "Content-Transfer-Encoding": "8bit",
                }

                for internal_key, translation in messages_text.items():
                    message_key = internal_key
                    message_value = translation
                    pofile.append(
                        POEntry(msgid=message_key, msgstr=message_value.strip())
                    )

                assert "license_medium" in messages_text
                po_filename = legalcode.translation_filename()
                dir = os.path.dirname(po_filename)
                if not os.path.isdir(dir):
                    os.makedirs(dir)
                pofile.save(po_filename)
                print(f"Created {po_filename}")

    def import_by_40_license_html(self, content, license_code, language_code):
        """
        Returns a dictionary mapping our internal keys to strings.
        """
        messages = {}
        print(f"Importing {license_code} {language_code}")
        raw_html = content
        # Some trivial making consistent - some translators changed 'strong' to 'b'
        # for some unknown reason.
        raw_html = raw_html.replace("<b>", "<strong>").replace("</b>", "</strong>")
        raw_html = raw_html.replace("<B>", "<strong>").replace("</B>", "</strong>")

        # Parse the raw HTML to a BeautifulSoup object.
        soup = BeautifulSoup(raw_html, "lxml")

        # Get the license titles and intro text.

        deed_main_content = soup.find(id="deed-main-content")
        messages["license_medium"] = inner_html(soup.find(id="deed-license").h2)
        messages["license_long"] = inner_html(deed_main_content.h3)
        messages["license_intro"] = inner_html(
            deed_main_content.h3.find_next_sibling("p")
        )

        # Section 1 – Definitions.

        # We're going to work out a list of what definitions we expect in this license,
        # and in what order.
        # Start with the definitions common to all the BY 4.0 licenses
        expected_definitions = [
            "adapted_material",
            "copyright_and_similar_rights",
            "effective_technological_measures",
            "exceptions_and_limitations",
            "licensed_material",
            "licensed_rights",
            "licensor",
            "share",
            "sui_generis_database_rights",
            "you",
        ]

        # now insert the optional ones
        def insert_after(after_this, what_to_insert):
            i = expected_definitions.index(after_this)
            expected_definitions.insert(i + 1, what_to_insert)

        if license_code == "by-sa":
            insert_after("adapted_material", "adapters_license")
            insert_after("adapters_license", "by_sa_compatible_license")
            insert_after("exceptions_and_limitations", "license_elements_sa")
            # See https://github.com/creativecommons/creativecommons.org/issues/1153
            # BY-SA 4.0 for "pt" has an extra definition. Work around for now.
            if language_code == "pt":
                insert_after("you", "you2")
        elif license_code == "by":
            insert_after("adapted_material", "adapters_license")
        elif license_code == "by-nc":
            insert_after("adapted_material", "adapters_license")
            insert_after("licensor", "noncommercial")
        elif license_code == "by-nd":
            pass
        elif license_code == "by-nc-nd":
            insert_after("licensor", "noncommercial")
        elif license_code == "by-nc-sa":
            insert_after("adapted_material", "adapters_license")
            insert_after("exceptions_and_limitations", "license_elements_nc_sa")
            insert_after("adapters_license", "by_nc_sa_compatible_license")
            insert_after("licensor", "noncommercial")

        # definitions are in an "ol" that is the next sibling of the id=s1 element.
        messages["s1_definitions_title"] = inner_html(soup.find(id="s1").strong)
        for i, definition in enumerate(
            soup.find(id="s1").find_next_siblings("ol")[0].find_all("li")
        ):
            thing = name_and_text(definition)
            defn_key = expected_definitions[i]
            messages[
                f"s1_definitions_{defn_key}"
            ] = f"""<span style="text-decoration: underline;">{thing['name']}</span> {thing['text']}"""

        # Section 2 – Scope.
        messages["s2_scope"] = inner_html(soup.find(id="s2").strong)

        # Section 2a - License Grant
        # translation of "License grant"
        s2a = soup.find(id="s2a")
        if s2a.strong:
            messages["s2a_license_grant_title"] = inner_html(s2a.strong)
        elif s2a.b:
            messages["s2a_license_grant_title"] = inner_html(s2a.b)
        else:
            print(f"How do I handle {s2a}?")
            sys.exit(1)

        # s2a1: rights
        messages["s2a_license_grant_intro"] = str(list(soup.find(id="s2a1"))[0]).strip()

        messages["s2a_license_grant_share"] = str(
            list(soup.find(id="s2a1A"))[0]
        ).strip()
        messages["s2a_license_grant_adapted"] = str(
            list(soup.find(id="s2a1B"))[0]
        ).strip()

        # s2a2: exceptions and limitations
        nt = name_and_text(soup.find(id="s2a2"))
        messages[
            "s2a2_license_grant_exceptions"
        ] = f"<strong>{nt['name']}</strong>{nt['text']}"

        # s2a3: term
        nt = name_and_text(soup.find(id="s2a3"))
        messages[
            "s2a3_license_grant_term"
        ] = f"<strong>{nt['name']}</strong>{nt['text']}"

        # s2a4: media
        nt = name_and_text(soup.find(id="s2a4"))
        messages[
            "s2a4_license_grant_media"
        ] = f"<strong>{nt['name']}</strong>{nt['text']}"

        # s2a5: scope/grant/downstream
        # The title is just the prefix to the list of items, which are in their
        # own div, so this is slightly messy. Using the name from name_and_text
        # will get us the text we want without wrappings.
        nt = name_and_text(soup.find(id="s2a5"))
        messages["s2a5_license_grant_downstream_title"] = nt["name"]

        expected_downstreams = [
            "offer",
            "no_restrictions",
        ]
        if license_code in ["by-sa", "by-nc-sa"]:
            expected_downstreams.insert(1, "adapted_material")

        # Process top-level "li" elements under the ol
        for i, li in enumerate(
            soup.find(id="s2a5").div.ol.find_all("li", recursive=False)
        ):
            key = expected_downstreams[i]
            thing = name_and_text(li)
            messages[f"s2a5_license_grant_downstream_{key}_name"] = thing["name"]
            messages[f"s2a5_license_grant_downstream_{key}_text"] = thing["text"]

        nt = name_and_text(soup.find(id="s2a6"))
        messages["s2a6_license_grant_no_endorsement_name"] = nt["name"]
        messages["s2a6_license_grant_no_endorsement_text"] = nt["text"]

        # s2b: other rights
        s2b = soup.find(id="s2b")
        if s2b.p and s2b.p.strong:
            messages["s2b_other_rights_title"] = nested_text(s2b.p.strong)
        elif s2b.p:
            messages["s2b_other_rights_title"] = nested_text(s2b.p)
        elif s2b.strong:
            messages["s2b_other_rights_title"] = nested_text(s2b.strong)
        else:
            print(str(s2b))
            raise ValueError("Where is s2b's title?")
        list_items = soup.find(id="s2b").ol.find_all("li", recursive=False)
        assert list_items[0].name == "li"
        messages["s2b1_other_rights_moral"] = nested_text(list_items[0])
        messages["s2b2_other_rights_patent"] = nested_text(list_items[1])
        messages["s2b3_other_rights_waive"] = nested_text(list_items[2])

        # Section 3: conditions
        s3 = soup.find(id="s3")
        messages["s3_conditions_title"] = nested_text(s3)
        messages["s3_conditions_intro"] = nested_text(
            soup.find(id="s3").find_next_sibling("p")
        )

        # <p id="s3"><strong>Section 3 – License Conditions.</strong></p>
        #
        #      <p>Your exercise of the Licensed Rights is expressly made subject to the following conditions.</p>
        #
        #      <ol type="a">
        #          <li id="s3a"><p><strong>Attribution</strong>.</p>
        #          <ol>

        s3a = soup.find(id="s3a")
        inside = str(inner_html(s3a))
        if inside.startswith(" "):  # ar translation takes liberties with whitespace
            s3a = BeautifulSoup(inside.strip(), "lxml")
        if s3a.p and s3a.p.strong:
            messages["s3_conditions_attribution"] = nested_text(s3a.p.strong)
        elif s3a.strong:
            messages["s3_conditions_attribution"] = nested_text(s3a.strong)
        else:
            print(str(s3a))
            raise ValueError("Fix s3a's attribution string")

        messages["s3_conditions_if_you_share"] = text_up_to(soup.find(id="s3a1"), "ol")

        messages["s3_conditions_retain_the_following"] = text_up_to(
            soup.find(id="s3a1A"), "ol"
        )
        messages["s3a1Ai_conditions_identification"] = inner_html(
            soup.find(id="s3a1Ai")
        )
        messages["s3a1Aii_conditions_copyright"] = inner_html(soup.find(id="s3a1Aii"))
        messages["s3a1Aiii_conditions_license"] = inner_html(soup.find(id="s3a1Aiii"))
        messages["s3a1Aiv_conditions_disclaimer"] = inner_html(soup.find(id="s3a1Aiv"))
        messages["s3a1Av_conditions_link"] = inner_html(soup.find(id="s3a1Av"))
        messages["s3a1B_conditions_modified"] = inner_html(soup.find(id="s3a1B"))
        messages["s3a1C_conditions_licensed"] = inner_html(soup.find(id="s3a1C"))
        messages["s3a2_conditions_satisfy"] = inner_html(soup.find(id="s3a2"))
        messages["s3a3_conditions_remove"] = inner_html(soup.find(id="s3a3"))
        if soup.find(id="s3a4"):
            # Only present if neither SA or ND
            messages["s3a4_if_you_share_adapted_material"] = nested_text(
                soup.find(id="s3a4")
            )

        # share-alike is only in some licenses
        if license_code.endswith("-sa"):
            messages["sharealike_name"] = nested_text(soup.find(id="s3b").strong)
            messages["sharealike_intro"] = nested_text(soup.find(id="s3b").p)

            messages["s3b1"] = nested_text(soup.find(id="s3b1"))
            messages["s3b2"] = nested_text(soup.find(id="s3b2"))
            messages["s3b3"] = nested_text(soup.find(id="s3b3"))

        # Section 4: Sui generis database rights
        messages["s4_sui_generics_database_rights_titles"] = nested_text(
            soup.find(id="s4")
        )
        messages["s4_sui_generics_database_rights_intro"] = (
            soup.find(id="s4").find_next_sibling("p").string
        )
        messages["s4_sui_generics_database_rights_extract_reuse"] = nested_text(
            soup.find(id="s4a")
        )
        s4b = soup.find(id="s4b").get_text()
        messages["s4_sui_generics_database_rights_adapted_material"] = s4b
        messages["s4_sui_generics_database_rights_comply_s3a"] = soup.find(
            id="s4c"
        ).get_text()
        # The next text comes after the 'ol' after s4, but isn't inside a tag itself!
        parent = soup.find(id="s4").parent
        s4_seen = False
        take_rest = False
        parts = []
        for item in parent.children:
            if take_rest:
                if item.name == "p":
                    # Stop at the next paragraph
                    break
                parts.append(str(item))
            elif not s4_seen:
                if isinstance(item, Tag) and item.get("id") == "s4":
                    s4_seen = True
                    continue
            elif not take_rest and item.name == "ol":
                # already seen s4, this is the ol, so the next child is our text
                take_rest = True
        messages["s4_sui_generics_database_rights_postscript"] = " ".join(parts)

        # Section 5: Disclaimer
        messages["s5_disclaimer_title"] = soup.find(id="s5").string
        messages["s5_a"] = soup.find(id="s5a").string  # bold
        messages["s5_b"] = soup.find(id="s5b").string  # bold
        messages["s5_c"] = soup.find(id="s5c").string  # not bold

        # Section 6: Term and Termination
        messages["s6_termination_title"] = nested_text(soup.find(id="s6"))
        messages["s6_termination_applies"] = nested_text(soup.find(id="s6a"))
        s6b = soup.find(id="s6b")
        if s6b.p:
            # most languages put the introductory text in a paragraph, making it easy
            messages["s6_termination_reinstates_where"] = soup.find(
                id="s6b"
            ).p.get_text()
        else:
            # if they don't, we have to pick out the text from the beginning of s6b's
            # content until the beginning of the "ol" inside it.
            s = ""
            for child in s6b:
                if child.name == "ol":
                    break
                s += str(child)
            messages["s6_termination_reinstates_where"] = s
        messages["s6_termination_reinstates_automatically"] = soup.find(
            id="s6b1"
        ).get_text()
        messages["s6_termination_reinstates_express"] = soup.find(id="s6b2").get_text()

        children_of_s6b = list(soup.find(id="s6b").children)
        messages["s6_termination_reinstates_postscript"] = (
            "".join(str(x) for x in children_of_s6b[4:7])
        ).strip()
        messages["s6_separate_terms"] = inner_html(soup.find(id="s6c"))
        messages["s6_survival"] = inner_html(soup.find(id="s6d"))

        # Section 7: Other terms and conditions
        messages["s7_other_terms_title"] = soup.find(id="s7").string
        messages["s7_a"] = soup.find(id="s7a").string
        messages["s7_b"] = soup.find(id="s7b").string

        # Section 8: Interpretation
        messages["s8_interpretation_title"] = soup.find(id="s8").string
        for key in ["s8a", "s8b", "s8c", "s8d"]:
            messages[key] = inner_html(soup.find(id=key))

        validate_dictionary_is_all_text(messages)

        return messages
