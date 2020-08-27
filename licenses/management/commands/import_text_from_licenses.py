import os
import sys
from collections import defaultdict, OrderedDict
from itertools import takewhile

from bs4 import BeautifulSoup, NavigableString, Tag
from django.core.management import BaseCommand
from django.utils.translation import to_language, to_locale
from django.utils.translation.trans_real import DjangoTranslation
from polib import POFile, POEntry

from licenses.models import LegalCode


class FatalUnclobberableDictionary(defaultdict):
    """
    Dictionary that you can add items to, but if
    you try to change an existing item *to a different value*,
    it throws an exception.  (Or if `is_fatal` was falsey,
    just print a warning.)

    Except... if you're trying to set it to an empty dictionary,
    and there's already a dictionary there, that's okay.

    And... if you try to set it to an empty dictionary, and the
    key isn't already here, we set it to an empty UnclobberableDictionary
    instead.

    And... if you try to get the value of a missing key, it
    sets it to a new UnclobberableDictionary and returns that.

    (This all sounds crazy, but it's really useful for collecting
    the messages and spotting places where messages that should be
    the same, aren't.)
    """

    # By default, changes to existing messages are a fatal error.
    # Use subclass NonFatalUnclobberableDictionary to make them just a warning.
    is_fatal = True

    def __init__(self, *args, **kwargs):
        # This will be a subclass of defaultdict whose default value is its own class.
        super().__init__(type(self), *args, **kwargs)

    def change_attempted(self, key, newvalue):
        """
        We're not allowed to change a value once entered.
        Warn - or die - depending on the "fatal" setting.
        See also NonFatalUnclobberableDictionary.
        """
        msg = f"Attempted to change {key} from \n{self[key]} to \n{newvalue}"
        if self.is_fatal:
            raise ValueError(msg)
        else:
            # FIXME: put this back once we get the parsing working
            pass  # print(msg)

    def __setitem__(self, key, value):
        if value == {}:
            if key in self:
                if isinstance(self[key], dict):
                    # Setting an empty dictionary where one already exists is okay.
                    return
                # Otherwise, we're trying to change a value.
                self.change_attempted(key, value)
            else:
                # Setting a value on a new key is okay.
                super().__setitem__(key, type(self)())
            return
        elif key in self and self[key] != value:
            self.change_attempted(key, value)
            return
        super().__setitem__(key, value)


class NonFatalUnclobberableDictionary(FatalUnclobberableDictionary):
    is_fatal = False


def name_and_text(tag: Tag):
    """
    This is for parsing dictionary-like elements in the license.

    Finds the tag with the given id.

    If a tag contains text, where the first part has a tag around it
    for formatting (typically 'strong' or 'span'). Extract the part
    inside the first tag as the "name", and the html (markup included)
    of the rest.

    E.g. "<strong>Truck</strong> is a heavy vehicle."

    Returns a dictionary {"name": str, "text": str}
    """
    top_level_children = list(tag.children)

    strings_from_top_level_children_after_first = [
        str(i) for i in top_level_children[1:]
    ]
    joined_strings = "".join(strings_from_top_level_children_after_first)
    stripped = joined_strings.strip()
    de_newlined = stripped.replace("\n", " ")

    return {
        "name": str(top_level_children[0].string),
        "text": de_newlined,
    }


def validate_list_is_all_text(l):
    """
    Just for sanity, make sure all the elements of a list are types that
    we expect to be in there.
    """
    newlist = []
    for i, value in enumerate(l):
        if type(value) == NavigableString:
            newlist.append(str(value))
            continue
        elif type(value) not in (str, list, dict, OrderedDict):
            raise ValueError(f"Not a str, list, or dict: {type(value)}: {value}")
        if isinstance(value, list):
            newlist.append(validate_list_is_all_text(value))
        elif isinstance(value, dict):
            newlist.append(validate_dictionary_is_all_text(value))
        else:
            newlist.append(value)
    return newlist


def validate_dictionary_is_all_text(d):
    """
    Just for sanity, make sure all the keys and values of a dictionary are types that
    we expect to be in there.
    """
    newdict = dict()
    for k, v in d.items():
        assert isinstance(k, str)
        if type(v) == NavigableString:
            newdict[k] = str(v)
            continue
        elif type(v) not in (
            str,
            list,
            dict,
            OrderedDict,
            FatalUnclobberableDictionary,
            NonFatalUnclobberableDictionary,
        ):
            raise ValueError(f"Not a str, list, or dict: k={k} {type(v)}: {v}")
        if isinstance(v, dict):
            newdict[k] = validate_dictionary_is_all_text(v)
        elif isinstance(v, list):
            newdict[k] = validate_list_is_all_text(v)
        else:
            newdict[k] = v
    return newdict


def save_dict_to_pofile(pofile: POFile, parts: dict, keyprefix: list = None):
    """
    We have a dictionary mapping string message keys to string message values
    or dictionaries of the same.
    Write out a .po file of the data.
    """
    if keyprefix is None:
        keyprefix = []
    for key, value in parts.items():
        if isinstance(value, dict):
            save_dict_to_pofile(pofile, value, keyprefix + [key])
        elif isinstance(value, str):
            message_key = ".".join(keyprefix + [key])
            pofile.append(POEntry(msgid=message_key, msgstr=value.strip()))
        else:
            raise ValueError(f"Value of unknown type in translations: {value}")


class Command(BaseCommand):
    """
    Management command to parse the HTML from our LegalCode records to get
    all the English and translated text for the 4.0 BY licenses.

    It then creates .po and .mo files under f"locale.licenses/{language_code}/LC_MESSAGES"
    """

    def handle(self, **options):
        # We'll accumulate our messages in this dictionary. See save_dict_to_pofile().
        by_text = {}

        # We're just doing these license codes and version 4.0 for now.
        LICENSE_CODES = ["by", "by-sa", "by-nc-nd", "by-nc", "by-nc-sa", "by-nd"]
        version = "4.0"

        # We'll call the translation domain 'by_4.0' for now.
        domain = f"by_{version}"

        # What are the language codes we have translations for?
        language_codes = list(
            LegalCode.objects.filter(
                license__version=version, license__license_code__startswith="by"
            )
            .order_by("language_code")
            .distinct("language_code")
            .values_list("language_code", flat=True)
        )

        # Start with english, then do the others. (I guess we're doing English
        # twice, something to fix if anyone cares.)
        for language_code in ["en"] + language_codes:
            # For non-English, for now, make changes in messages non-fatal.
            dict_type = (
                FatalUnclobberableDictionary
                if language_code == "en"
                else NonFatalUnclobberableDictionary
            )
            by_text[language_code] = dict_type()

            # Import the text from each license for this language/version
            # and save in by_text[language_code].
            for license_code in LICENSE_CODES:
                self.import_by_40_license_html(
                    license_code, version, language_code, by_text[language_code]
                )

            # Save to a .po file for this language.
            pofile = POFile()
            pofile.metadata = {
                "Project-Id-Version": domain,
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
            save_dict_to_pofile(pofile, by_text[language_code])

            # Dir name will be like "en_US" or "tr_TR" or "zh_CN" or "zh-Hans"

            django_language_code = to_language(language_code)
            django_locale_code = to_locale(language_code)
            # django_language_code=zh-hans django_locale_code=zh_Hans
            print(
                f"django_language_code={django_language_code} django_locale_code={django_locale_code}"
            )

            dir = f"locale.licenses/{django_locale_code}/LC_MESSAGES"
            po_filename = f"{domain}.po"
            if not os.path.isdir(dir):
                os.makedirs(dir)

            pofile.save(os.path.join(dir, po_filename))

            # Compile the messages to a .mo file so we can load them in the next step.
            mo_filename = f"{domain}.mo"
            pofile.save_as_mofile(os.path.join(dir, mo_filename))

            # To double-check, make sure we can load the translations in a way that Django would
            # if we were going to use them.
            DjangoTranslation(
                language=django_language_code,
                domain=domain,
                localedirs=["locale.licenses"],
            )

    def import_by_40_license_html(self, license_code, version, language_code, text):
        print(f"Importing {license_code} {version} {language_code}")

        # Make sure the LegalCode records we're looking for HTML in actually have some.
        for legalcode in LegalCode.objects.filter(
            license__license_code=license_code,
            license__version=version,
            language_code=language_code,
        ):
            if legalcode.raw_html == "":
                raise ValueError(f"{legalcode} has no raw HTML")

        # There *MIGHT* be multiple LegalCodes for this combination, but
        # they should all have the same HTML. Check that.
        legalcodes = LegalCode.objects.exclude(raw_html="").filter(
            license__license_code=license_code,
            license__version=version,
            language_code=language_code,
        )
        raw_html = legalcodes.first().raw_html
        for lc in legalcodes:
            if lc.raw_html != raw_html:
                print("Different legalcodes with different html!")
                sys.exit(1)

        # Some trivial making consistent - some translators changed 'strong' to 'b'
        # for some unknown reason.
        raw_html = raw_html.replace("<b>", "<strong>").replace("</b>", "</strong>")
        raw_html = raw_html.replace("<B>", "<strong>").replace("</B>", "</strong>")

        # Parse the raw HTML to a BeautifulSoup object.
        soup = BeautifulSoup(raw_html, "lxml")

        # Helper to find the element with a given id from the soup.
        def find_id(id):
            tag = soup.find(id=id)
            if tag is None:
                raise ValueError(f"Tag with id={id} not found")
            return tag

        # Return all the text/html INSIDE the given tag, but
        # not the tag element itself.
        def inner_html(tag):
            return "".join(str(item) for item in tag)

        # This is for processing parts of the document that might or might
        # not have some tags (p, span, strong, ...) wrapping around text,
        # to help extract the text - or whatever's inside when we strip
        # away all the simply nested tags around it.
        # Given a tag. If it's a string, return it. If it's got exactly
        # one child, recurse on that child. If you get to something more
        # complicated, just return the HTML remaining.
        def nested_text(tag):
            if isinstance(tag, NavigableString):
                return str(tag)
            if len(tag.contents) == 1:
                child = tag.contents[0]
                if isinstance(child, NavigableString):
                    return str(child)
                return nested_text(child)
            return inner_html(tag)

        def text_id(id):
            """
            Find the tag with the given id, then return the text inside it.
            """
            return nested_text(find_id(id))

        # Given a tag, return the text of the immediate children up to,
        # but not including the first child whose tagname is 'tagname'.
        def text_up_to(tag, tagname):
            children = list(
                takewhile(
                    lambda item: not hasattr(item, "name") or item.name != tagname,
                    tag.contents,
                )
            )
            if len(children) == 1:
                return nested_text(children[0])
            return "".join(str(child) for child in children)

        # Get the license titles and intro text.

        deed_main_content = find_id("deed-main-content")
        text["license_medium"][license_code] = inner_html(find_id("deed-license").h2)
        text["license_long"][license_code] = inner_html(deed_main_content.h3)
        text["license_intro"][license_code] = inner_html(
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
        text["s1_definitions_title"] = inner_html(find_id("s1").strong)
        for i, definition in enumerate(
            find_id("s1").find_next_siblings("ol")[0].find_all("li")
        ):
            thing = name_and_text(definition)
            defn_key = expected_definitions[i]
            text["s1_definitions"][defn_key] = f"*{thing['name']}* {thing['text']}"

        # Section 2 – Scope.
        text["s2_scope"] = inner_html(find_id("s2").strong)

        # Section 2a - License Grant
        # translation of "License grant"
        s2a = find_id("s2a")
        if s2a.strong:
            text["s2a_license_grant"]["title"] = inner_html(s2a.strong)
        elif s2a.b:
            text["s2a_license_grant"]["title"] = inner_html(s2a.b)
        else:
            print(f"How do I handle {s2a}?")
            sys.exit(1)

        # s2a1: rights
        text["s2a_license_grant"]["intro"] = str(list(find_id("s2a1"))[0]).strip()

        if "nc" in license_code:
            text["s2a_license_grant"]["share_nc"] = str(
                list(find_id("s2a1A"))[0]
            ).strip()
        else:
            text["s2a_license_grant"]["share"] = str(list(find_id("s2a1A"))[0]).strip()

        if "nc" in license_code and "nd" in license_code:
            text["s2a_license_grant"]["adapted_nc_nd"] = str(
                list(find_id("s2a1B"))[0]
            ).strip()
        elif "nc" in license_code:
            text["s2a_license_grant"]["adapted_nc"] = str(
                list(find_id("s2a1B"))[0]
            ).strip()
        elif "nd" in license_code:
            text["s2a_license_grant"]["adapted_nd"] = str(
                list(find_id("s2a1B"))[0]
            ).strip()
        else:
            text["s2a_license_grant"]["adapted"] = str(
                list(find_id("s2a1B"))[0]
            ).strip()

        # s2a2: exceptions
        text["s2a2_license_grant_exceptions"] = name_and_text(find_id("s2a2"))

        # s2a3: term
        text["s2a3_license_grant_term"] = name_and_text(find_id("s2a3"))

        # s2a4: media
        text["s2a4_license_grant_media"] = name_and_text(find_id("s2a4"))

        # s2a5: scope/grant/downstream
        text["s2a5_license_grant_downstream_title"] = str(find_id("s2a5").strong)

        expected_downstreams = [
            "offer",
            "no_restrictions",
        ]
        if license_code in ["by-sa", "by-nc-sa"]:
            expected_downstreams.insert(1, "adapted_material")

        # Process top-level "li" elements under the ol
        for i, li in enumerate(find_id("s2a5").div.ol.find_all("li", recursive=False)):
            key = expected_downstreams[i]
            thing = name_and_text(li)
            text[f"s2a5_license_grant_downstream_{key}"] = thing

        text["s2a6_license_grant_no_endorsement"] = name_and_text(find_id("s2a6"))

        # s2b: other rights
        text["s2b_other_rights_title"] = text_up_to(find_id("s2b"), "ol")
        text_items = find_id("s2b").ol.find_all("li", recursive=False)
        text["s2b_other_rights_moral"] = str(text_items[0].string)
        text["s2b_other_rights_patent"] = str(text_items[1].string)
        if "nc" in license_code:
            text["s2b_other_rights_waive_nc"] = str(text_items[2].string)
        else:
            text["s2b_other_rights_waive_non_nc"] = str(text_items[2].string)

        # s3: conditions
        text["s3_conditions_title"] = nested_text(find_id("s3"))
        text["s3_conditions_intro"] = nested_text(find_id("s3").find_next_sibling("p"))
        s3a = find_id("s3a")
        text["s3_conditions_attribution"] = text_up_to(s3a, "ol")

        if "nd" in license_code:
            text["s3_conditions"]["if_you_share_nd"] = text_up_to(find_id("s3a1"), "ol")
        else:
            text["s3_conditions"]["if_you_share_non_nd"] = text_up_to(
                find_id("s3a1"), "ol"
            )

        text["s3_conditions"]["retain_the_following"] = text_up_to(
            find_id("s3a1A"), "ol"
        )
        text["s3_conditions"]["identification"] = nested_text(find_id("s3a1Ai"))
        text["s3_conditions"]["copyright"] = find_id("s3a1Aii").string
        text["s3_conditions"]["license"] = find_id("s3a1Aiii").string
        text["s3_conditions"]["disclaimer"] = find_id("s3a1Aiv").string
        text["s3_conditions"]["link"] = find_id("s3a1Av").string
        text["s3_conditions"]["modified"] = find_id("s3a1B").string
        text["s3_conditions"]["licensed"] = find_id("s3a1C").string
        text["s3_conditions"]["satisfy"] = list(find_id("s3a2"))[0].string
        text["s3_conditions"]["remove"] = list(find_id("s3a3"))[0].string

        # share-alike is only in some licenses
        if license_code.endswith("-sa"):
            text["sharealike"]["name"] = nested_text(find_id("s3b").strong)
            text["sharealike"]["intro"] = nested_text(find_id("s3b").p)

        text["s4_sui_generics_database_rights_titles"] = nested_text(find_id("s4"))
        text["s4_sui_generics_database_rights"]["intro"] = (
            find_id("s4").find_next_sibling("p").string
        )
        if "nc" in license_code and "nd" in license_code:
            text["s4_sui_generics_database_rights"][
                "extract_reuse_nc_nd"
            ] = nested_text(find_id("s4a"))
        elif "nc" in license_code:
            text["s4_sui_generics_database_rights"]["extract_reuse_nc"] = str(
                find_id("s4a")
            )
        elif "nd" in license_code:
            text["s4_sui_generics_database_rights"]["extract_reuse_nd"] = str(
                find_id("s4a")
            )
        else:
            text["s4_sui_generics_database_rights"][
                "extract_reuse_non_nc_non_nd"
            ] = find_id("s4a").get_text()
        s4b = find_id("s4b").get_text()
        if license_code.endswith("-sa"):
            text["s4_sui_generics_database_rights"]["adapted_material_sa"] = s4b
        else:
            text["s4_sui_generics_database_rights"]["adapted_material_non-sa"] = s4b
        text["s4_sui_generics_database_rights"]["comply_s3a"] = find_id(
            "s4c"
        ).get_text()
        # The next text comes after the 'ol' after s4, but isn't inside a tag itself!
        parent = find_id("s4").parent
        s4_seen = False
        take_next = False
        for item in parent.children:
            if take_next:
                text["s4_sui_generics_database_rights"]["postscript"] = item.string
                break
            elif not s4_seen:
                if isinstance(item, Tag) and item.get("id") == "s4":
                    s4_seen = True
                    continue
            elif not take_next and item.name == "ol":
                # already seen s4, this is the ol, so the next child is our text
                take_next = True

        part = "s5_disclaimer"
        text["s5_disclaimer_title"] = find_id("s5").string
        text["s5_a"] = find_id("s5a").string  # bold
        text["s5_b"] = find_id("s5b").string  # bold
        text["s5_c"] = find_id("s5c").string  # not bold

        text["s6_termination_title"] = find_id("s6").get_text()
        text["s6_termination_applies"] = find_id("s6a").string
        s6b = find_id("s6b")
        if s6b.p:
            # most languages put the introductory text in a paragraph, making it easy
            text["s6_termination_reinstates_where"] = find_id("s6b").p.get_text()
        else:
            # if they don't, we have to pick out the text from the beginning of s6b's
            # content until the beginning of the "ol" inside it.
            s = ""
            for child in s6b:
                if child.name == "ol":
                    break
                s += str(child)
            text["s6_termination_reinstates_where"] = s
        text["s6_termination_reinstates_automatically"] = find_id("s6b1").get_text()
        text["s6_termination_reinstates_express"] = find_id("s6b2").get_text()

        children_of_s6b = list(find_id("s6b").children)
        text["s6_termination_reinstates_postscript"] = (
            "".join(str(x) for x in children_of_s6b[4:7])
        ).strip()

        text["s7_other_terms_title"] = find_id("s7").string
        text["s7_a"] = find_id("s7a").string
        text["s7_b"] = find_id("s7b").string

        text["s8_interpretation_title"] = find_id("s8").string

        text = validate_dictionary_is_all_text(text)

        # output_file = yaml.dump(parts)
        # print(output_file)
        # pprint(parts)
