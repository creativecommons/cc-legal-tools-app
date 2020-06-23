"""
Import data from CC's index.rdf file into the database, creating records containing
the same data.

SEE https://www.w3.org/Submission/ccREL/ for information about CC's RDF schema.

FYI, starting from an empty database, this takes almost 5 minutes on my laptop.
I don't see much point in investing effort to speed it up, though, since we'll
only really be running it once.
"""

import datetime
import xml.etree.ElementTree as ET
from typing import Optional

from django.core.management import BaseCommand

from licenses.models import (
    License,
    TranslatedLicenseName,
    Language,
    LicenseLogo,
    Jurisdiction,
    Creator,
    LicenseClass,
    LegalCode,
)

NO_DEFAULT = object()  # Marker meaning don't allow use of a default value.

# Namespaces in the RDF
namespaces = {
    "cc": "http://creativecommons.org/ns#",
    "dc": "http://purl.org/dc/elements/1.1/",
    "dcq": "http://purl.org/dc/terms/",
    "foaf": "http://xmlns.com/foaf/0.1/",
    "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
    "xml": "http://www.w3.org/XML/1998/namespace",
}

# The following licenses are refered to but do not exist in the data.
# We will be reporting these elsewhere, but for the time being, ignore
# these in the import.
MISSING_LICENSES = [
    "http://creativecommons.org/licenses/by-nc/2.1/",
    "http://creativecommons.org/licenses/by-nd/2.1/",
    "http://creativecommons.org/licenses/by-nc-nd/2.1/",
    "http://creativecommons.org/licenses/by-sa/2.1/",
    "http://creativecommons.org/licenses/by-nc-sa/2.1/",
    "http://creativecommons.org/licenses/nc/2.0/",
    "http://creativecommons.org/licenses/nc-sa/2.0/",
    "http://creativecommons.org/licenses/by/2.1/",
    "http://creativecommons.org/licenses/nd-nc/2.0/",
    "http://creativecommons.org/licenses/by-nd-nc/2.0/",
    "http://creativecommons.org/licenses/nd/2.0/",
    "http://creativecommons.org/licenses/sa/2.0/",
]


class Command(BaseCommand):
    def handle(self, *args, **options):
        # https://docs.python.org/3/library/xml.etree.elementtree.html#xml.etree.ElementTree.Element
        root = ET.parse("index.rdf").getroot()  # type: ET.Element

        # We're going to start by building license_elements, which is just a dictionary
        # mapping license URLs to the elements from the RDF file that define them.
        # That way if we're working on importing one license and come across a reference
        # to another license that doesn't exist yet, we can easily find its definition
        # and import it first.

        self.license_elements = {
            license_element.attrib[namespaced("rdf", "about")]: license_element
            for license_element in root.findall("cc:License", namespaces)
        }

        print(
            "There are {} licenses in the RDF file".format(
                len(self.license_elements.keys())
            )
        )
        print(
            "There are {} licenses in the database already".format(
                License.objects.all().count()
            )
        )

        # Now do the importing
        # First the licenses (<cc:License>)
        # (We do them in order by name just for the convenience of anyone watching the output.)
        for url in sorted(self.license_elements.keys()):
            self.get_license_object(url)

        # Next the <rdf:Description>s
        # The Description elements just add some language information about the legalcodes.
        description_elements = root.findall("rdf:Description", namespaces)
        for d in description_elements:
            # These could be anything, but in index.rdf they all seem to be legalcodes
            legal_code = LegalCode.objects.get(url=d.attrib[namespaced("rdf", "about")])
            language_code = get_element_text(d, "dcq:language", None)
            if language_code is not None:
                legal_code.language = Language.objects.get_or_create(
                    code=language_code
                )[0]

    def get_license_object(self, license_url: str) -> Optional[License]:
        """
        Return the License model object for the given URL, creating it and adding to
        the database if necessary. license_elements is a dictionary mapping license
        URLs to the ElementTree objects that define them.
        """

        # Note: as we build the license object, we remove the XML elements we use
        # from the tree. If we have any left over, we know we've missed converting
        # something.
        try:
            # If the License already exists, just return it
            return License.objects.get(about=license_url)
        except License.DoesNotExist:
            pass

        if license_url not in self.license_elements:
            raise ValueError(
                "There is a reference to a license {} that does not exist".format(
                    license_url
                )
            )

        license_element = self.license_elements[license_url]  # type: ET.Element
        print("Importing {}".format(license_element.attrib[namespaced("rdf", "about")]))

        #
        # References to other licenses
        #

        # If this is a translation, it will link to the "source" license.
        source_url = get_element_attribute(
            license_element, "dc:source", "rdf:resource", None
        )
        if source_url and source_url not in MISSING_LICENSES:
            source_license = self.get_license_object(source_url)
        else:
            source_license = None

        is_based_on_url = get_element_attribute(
            license_element, "dc:isBasedOn", "rdf:resource", None
        )
        if is_based_on_url and is_based_on_url not in MISSING_LICENSES:
            if is_based_on_url not in self.license_elements:
                raise ValueError(
                    "isBasedOn = {} but that license does not exist".format(
                        is_based_on_url
                    )
                )
            is_based_on = self.get_license_object(is_based_on_url)
        else:
            is_based_on = None

        replacement_url = get_element_attribute(
            license_element, "dcq:isReplacedBy", "rdf:resource", None
        )
        if replacement_url and replacement_url not in MISSING_LICENSES:
            if replacement_url not in self.license_elements:
                raise ValueError(
                    "isReplacedBy = {} but that license does not exist".format(
                        replacement_url
                    )
                )
            is_replaced_by = self.get_license_object(replacement_url)
        else:
            is_replaced_by = None

        elt = license_element.find("dc:isReplacedBy", namespaces)
        if elt is not None:
            print(
                "WARNING: This license is using <dc:isReplacedBy>. "
                "It probably should be <dcq:isReplacedBy> and that's "
                "how we are treating it."
            )
            url = elt.attrib[namespaced("rdf", "resource")]
            license_element.remove(elt)
            is_replaced_by = self.get_license_object(url)

        #
        # Values that refer to other records that aren't licenses.
        #

        jurisdiction_url = get_element_attribute(
            license_element, "cc:jurisdiction", "rdf:resource", None
        )
        jurisdiction = (
            Jurisdiction.objects.get_or_create(url=jurisdiction_url)[0]
            if jurisdiction_url
            else None
        )

        creator_url = get_element_attribute(
            license_element, "dc:creator", "rdf:resource", None
        )
        creator = (
            Creator.objects.get_or_create(url=creator_url)[0] if creator_url else None
        )

        license_class_url = get_element_attribute(
            license_element, "cc:licenseClass", "rdf:resource"
        )
        license_class = (
            LicenseClass.objects.get_or_create(url=license_class_url)[0]
            if license_class_url
            else None
        )

        #
        # Other values
        #

        deprecated_on_string = get_element_text(
            license_element, "cc:deprecatedOn", None
        )
        if deprecated_on_string:
            # "YYYY-MM-DD"
            year, month, day = [int(s) for s in deprecated_on_string.split("-")]
            deprecated_on = datetime.date(year, month, day)
        else:
            deprecated_on = None

        # permissions
        permits_urls = set()
        for elt in license_element.findall("cc:permits", namespaces):
            permits_urls.add(elt.attrib[namespaced("rdf", "resource")])
            license_element.remove(elt)

        # requirements
        requires_urls = set()
        for elt in license_element.findall("cc:requires", namespaces):
            requires_urls.add(elt.attrib[namespaced("rdf", "resource")])
            license_element.remove(elt)

        # prohibitions
        prohibits_urls = set()
        for prohibition in license_element.findall("cc:prohibits", namespaces):
            prohibits_urls.add(prohibition.attrib[namespaced("rdf", "resource")])
            license_element.remove(prohibition)

        # Create the License object
        license = License.objects.create(
            about=license_url,
            identifier=get_element_text(license_element, "dc:identifier"),
            version=get_element_text(license_element, "dcq:hasVersion", ""),
            source=source_license,
            jurisdiction=jurisdiction,
            creator=creator,
            license_class=license_class,
            is_replaced_by=is_replaced_by,
            is_based_on=is_based_on,
            deprecated_on=deprecated_on,
            permits_derivative_works="http://creativecommons.org/ns#DerivativeWorks"
            in permits_urls,
            permits_distribution="http://creativecommons.org/ns#Distribution"
            in permits_urls,
            permits_reproduction="http://creativecommons.org/ns#Reproduction"
            in permits_urls,
            permits_sharing="http://creativecommons.org/ns#Sharing" in permits_urls,
            requires_attribution="http://creativecommons.org/ns#Attribution"
            in requires_urls,
            requires_notice="http://creativecommons.org/ns#Notice" in requires_urls,
            requires_share_alike="http://creativecommons.org/ns#ShareAlike"
            in requires_urls,
            requires_source_code="http://creativecommons.org/ns#SourceCode"
            in requires_urls,
            prohibits_commercial_use="http://creativecommons.org/ns#CommercialUse"
            in prohibits_urls,
            prohibits_high_income_nation_use="http://creativecommons.org/ns#HighIncomeNationUse"
            in prohibits_urls,
        )

        # Other objects that link to the License object

        # legal code
        for legal_code in license_element.findall("cc:legalcode", namespaces):
            code_url = legal_code.attrib[namespaced("rdf", "resource")]
            code_object = LegalCode.objects.get_or_create(url=code_url)[0]
            license.legalcodes.add(code_object)
            license_element.remove(legal_code)

        # titles
        for title_element in license_element.findall("dc:title", namespaces):
            # attribute "xml:lang" is almost always present - but missing every now and then.
            lang_key = namespaced("xml", "lang")
            if lang_key in title_element.attrib:
                lang_code = title_element.attrib[lang_key]
                language = Language.objects.get_or_create(code=lang_code)[0]
            else:
                language = None
            TranslatedLicenseName.objects.create(
                license=license, language=language, name=title_element.text,
            )
            license_element.remove(title_element)

        # logos
        for logo_element in license_element.findall("foaf:logo", namespaces):
            logo_url = logo_element.attrib[namespaced("rdf", "resource")]
            LicenseLogo.objects.create(image=logo_url, license=license)
            license_element.remove(logo_element)

        if len(list(license_element)):
            for child in list(license_element):
                print(child)
            raise Exception("MISSED SOMETHING - see list just above this")

        return license


def namespaced(ns_name: str, tag_name: str) -> str:
    """
    Given a namespace name/abbreviation, look up its full name
    and return the tag_name prefixed appropriately.
    E.g. namespaced("cc", "License") -> "{http://creativecommons.org/ns#}License"
    This is the syntax we need to retrieve attributes from an Element.
    """
    return "{%s}%s" % (namespaces[ns_name], tag_name)


def get_element_text(parent: ET.Element, tagname: str, default_value=NO_DEFAULT) -> str:
    """
    Find the child of 'parent' with tag name 'tagname' and return its
    text. If the tag is not found and a default is given, return that;
    if the tag is not found and there's no default, raise an exception.
    """

    element = parent.find(tagname, namespaces)

    # Important: we must compare against None here. If we just say "if element", it's
    # True only if the element has children, and that's not what we want to know.
    if element is not None:
        value = element.text
        parent.remove(element)
        return value
    elif default_value is NO_DEFAULT:
        raise Exception("{} not found and no default allowed".format(tagname))
    else:
        return default_value


def get_element_attribute(
    parent: ET.Element, tag: str, attrname: str, default_value=NO_DEFAULT
) -> str:
    """
    Find the child of 'parent' with tag name 'tagname' and return the value
    of its attribute 'attrname'. If the tag is not found and a
    default is given, return that; if the tag is not found and there's no
    default, raise an exception.

    If the tag is found but it doesn't have the requested attribute, that's always
    an error.
    """
    element = parent.find(tag, namespaces)

    # Important: we must compare against None here. If we just say "if element", it's
    # True only if the element has children, and that's not what we want to know.
    if element is not None:
        value = element.attrib[namespaced(*attrname.split(":"))]
        parent.remove(element)
        return value
    elif default_value is NO_DEFAULT:
        raise Exception("{} not found and no default allowed".format(tag))
    else:
        return default_value
