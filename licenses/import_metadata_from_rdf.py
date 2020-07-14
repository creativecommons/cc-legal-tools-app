"""
Import data from CC's index.rdf file into the database, creating records containing
the same data.

SEE https://www.w3.org/Submission/ccREL/ for information about CC's RDF schema.

This takes about 7 seconds on my laptop, due to all the messing around so we
can avoid individual queries and creates. Before that, it was more like 5 minutes.
Now that it's so fast, we can just run it from a migration and tests will always
have valid data to work with.

The management command "import_index_rdf" uses this, as does one of the "licenses"
migrations.
"""
import datetime
import xml.etree.ElementTree as ET
from typing import Optional

from licenses import MISSING_LICENSES
from i18n import DEFAULT_LANGUAGE_CODE, DEFAULT_JURISDICTION_LANGUAGES
from licenses.models import (
    License,
    TranslatedLicenseName,
    Language,
    LicenseLogo,
    Creator,
    LicenseClass,
    LegalCode,
    Jurisdiction,
)
from licenses.utils import get_code_from_jurisdiction_url


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


CREATOR_CACHE = {}  # Map URL to Creator objects (mostly unsaved)
JURISDICTION_CACHE = {}  # Map URL to Jurisdiction objects (mostly unsaved)
LANGUAGE_CACHE = {}  # Map URL to Language objects (mostly unsaved)
LEGAL_CODE_CACHE = {}  # Map URL to LegalCode objects (mostly unsaved)
LICENSE_CLASS_CACHE = {}  # Map URL to LicenseClass objects (mostly unsaved)
TRANSLATED_LICENSE_NAME_CACHE = (
    {}
)  # Map of unsaved TranslatedLicenseName objects. key=license_about|lang_code.
LICENSE_LOGOS = []  # List of unsaved LicenseLogo objects


def get_instance_with_caching(model, cache, argname, value, **extra_kwargs):
    """
    If we have a cached object in 'cache' with argname=value, return it.
    Otherwise, create (but don't save) an object of type 'model' using
    argname=value + any other kwargs provided.
    """

    kwargs = {argname: value}
    if value not in cache:
        kwargs = dict(extra_kwargs, **kwargs)
        cache[value] = model(**kwargs)

    return cache[value]


def get_creator_for_url(url):
    return get_instance_with_caching(Creator, CREATOR_CACHE, "url", url)


def get_jurisdiction_for_code(code):
    kwargs = {}
    if code not in JURISDICTION_CACHE:
        if code in DEFAULT_JURISDICTION_LANGUAGES:
            langs = DEFAULT_JURISDICTION_LANGUAGES[code]
            if len(langs) == 1:
                kwargs = {"default_language": get_language_for_code(langs[0])}
    return get_instance_with_caching(
        Jurisdiction, JURISDICTION_CACHE, "code", code, **kwargs
    )


def get_language_for_code(code):
    return get_instance_with_caching(Language, LANGUAGE_CACHE, "code", code)


def get_legal_code_for_url(url, language):
    return get_instance_with_caching(
        LegalCode, LEGAL_CODE_CACHE, "url", url, language=language,
    )


def get_license_class_for_url(url):
    return get_instance_with_caching(LicenseClass, LICENSE_CLASS_CACHE, "url", url)


def get_translated_license_name(license, language, name):
    key = f"{license.about}|{language.code}"
    if key not in TRANSLATED_LICENSE_NAME_CACHE:
        TRANSLATED_LICENSE_NAME_CACHE[key] = TranslatedLicenseName(
            license=license, language=language, name=name
        )
    return TRANSLATED_LICENSE_NAME_CACHE[key]


def do_bulk_create(objects):
    """
    Given a list of instances of the same model, bulk_create
    the ones that haven't already been saved.
    """
    objects_to_create = [obj for obj in objects if not obj.pk]
    if not objects_to_create:  # pragma: no cover
        return  # Nothing to create
    model = type(objects_to_create[0])
    model.objects.bulk_create(objects_to_create)


class MetadataImporter:
    def import_metadata(self, readable):
        global CREATOR_CACHE, JURISDICTION_CACHE, LANGUAGE_CACHE, LEGAL_CODE_CACHE, LICENSE_CLASS_CACHE, \
            TRANSLATED_LICENSE_NAME_CACHE, LICENSE_LOGOS, LEGAL_CODES_TO_ADD_TO_LICENSES

        print("Populating database with license data.")

        # https://docs.python.org/3/library/xml.etree.elementtree.html#xml.etree.ElementTree.Element
        rdf_string = readable.read().decode("utf-8")
        root = ET.fromstring(rdf_string)  # type: ET.Element

        # We're going to start by building license_elements, which is just a dictionary
        # mapping license URLs to the elements from the RDF file that define them.
        # That way if we're working on importing one license and come across a reference
        # to another license that doesn't exist yet, we can easily find its definition
        # and import it first.

        self.license_elements = {
            license_element.attrib[namespaced("rdf", "about")]: license_element
            for license_element in root.findall("cc:License", namespaces)
        }
        # Populate self.licenses with License objects that already exist in the database
        self.licenses = {  # Maps urls to License objects
            license.about: license for license in License.objects.all()
        }

        print(
            "There are {} licenses in the RDF file".format(
                len(self.license_elements.keys())
            )
        )
        print(
            "There are {} licenses in the database already".format(
                len(self.licenses.keys())
            )
        )

        # Populate the caches with whatever's in the database already
        CREATOR_CACHE = {c.url: c for c in Creator.objects.all()}
        JURISDICTION_CACHE = {j.code: j for j in Jurisdiction.objects.all()}
        LANGUAGE_CACHE = {lang.code: lang for lang in Language.objects.all()}
        LEGAL_CODE_CACHE = {lg.url: lg for lg in LegalCode.objects.all()}
        LICENSE_CLASS_CACHE = {lc.url: lc for lc in LicenseClass.objects.all()}

        for tln in TranslatedLicenseName.objects.select_related("license", "language"):
            TRANSLATED_LICENSE_NAME_CACHE[
                f"{tln.license.about}|{tln.language.code}"
            ] = tln

        print("Reading RDF")

        # First get the <rdf:Description>s - these tell us what the languages are for
        # the legalcode objects, so we can create them now.
        # <rdf:Description rdf:about="http://creativecommons.org/licenses/by-nd/3.0/es/legalcode.ca">
        #   <dcq:language>ca</dcq:language>
        # </rdf:Description>
        # Note: these all have languages specified
        for description in root.findall("rdf:Description", namespaces):
            url = description.attrib[namespaced("rdf", "about")]
            lang_code = get_element_text(description, "dcq:language")
            get_legal_code_for_url(
                url=url, language=get_language_for_code(lang_code),
            )

        # Now do the reading of the licenses (<cc:License>)
        for url in self.license_elements.keys():
            self.get_license_object(url)

        # Finally, carefully save everything not already saved, creating things first
        # that will need to be referred to later.
        print("Saving objects to database")
        do_bulk_create(CREATOR_CACHE.values())
        do_bulk_create(LANGUAGE_CACHE.values())
        # Update some objects to be saved with the now-saved Language objects.

        # Django seems kind of dumb about this - even though the object attribute
        # points to a saved Django model object, it doesn't recognize that it can
        # use the PK from that model object. I guess it only recognizes the pk
        # at the time when you assign a model object to the attribute.
        for legal_code in LEGAL_CODE_CACHE.values():
            legal_code.language = legal_code.language

        do_bulk_create(LEGAL_CODE_CACHE.values())
        for jurisdiction in JURISDICTION_CACHE.values():
            jurisdiction.default_language = jurisdiction.default_language
        do_bulk_create(JURISDICTION_CACHE.values())
        do_bulk_create(LICENSE_CLASS_CACHE.values())

        # update some objects on the licenses
        for license in self.licenses.values():
            if (
                not license.pk
            ):  # pragma: no cover (only really used if we're restarting after a partial import)
                license.creator = license.creator
                license.jurisdiction = license.jurisdiction
                license.license_class = license.license_class

        do_bulk_create(self.licenses.values())

        # Find licenses with references to other licenses that still need to be updated
        for license in self.licenses.values():
            if getattr(license, "source_url", False):
                license.source = self.licenses[license.source_url]
            if getattr(license, "is_replaced_by_url", False):
                license.is_replaced_by = self.licenses[license.is_replaced_by_url]
            if getattr(license, "is_based_on_url", False):
                license.is_based_on = self.licenses[license.is_based_on_url]
        License.objects.bulk_update(
            self.licenses.values(), ["source", "is_replaced_by", "is_based_on"]
        )

        # Update TranslatedLicenseName objects with the saved license and language objects
        # before saving them
        for tln in TRANSLATED_LICENSE_NAME_CACHE.values():
            if (
                not tln.pk
            ):  # pragma: no cover (only really used if we're restarting after a partial import)
                tln.language = tln.language
                tln.license = tln.license
        do_bulk_create(TRANSLATED_LICENSE_NAME_CACHE.values())

        for logo in LICENSE_LOGOS:
            logo.license = logo.license
        do_bulk_create(LICENSE_LOGOS)

        through_model = License.legal_codes.through
        through_models = []
        for license in self.licenses.values():
            for legal_code in getattr(license, "legal_codes_to_add", []):
                through_models.append(
                    through_model(license=license, legalcode=legal_code)
                )
        do_bulk_create(through_models)

    def get_license_object(self, license_url: str) -> Optional[License]:
        """
        Return the License model object for the given URL, creating it and adding to
        the database if necessary. license_elements is a dictionary mapping license
        URLs to the ElementTree objects that define them.
        """

        # Note: as we build the license object, we remove the XML elements we use
        # from the tree. If we have any left over, we know we've missed converting
        # something.
        if license_url not in self.license_elements:  # pragma: no cover
            raise ValueError(
                "There is a reference to a license {} that does not exist".format(
                    license_url
                )
            )
        if license_url in self.licenses:  # pragma: no cover
            # We've already done this one, return the License object.
            return self.licenses[license_url]

        license_element = self.license_elements[license_url]  # type: ET.Element

        #
        # References to other licenses
        #

        # If this is a translation, it will link to the "source" license.
        #     <dc:source rdf:resource="http://creativecommons.org/licenses/by-nc-nd/3.0/"/>
        source_url = get_element_attribute(
            license_element, "dc:source", "rdf:resource", ""
        )
        if source_url in MISSING_LICENSES:
            source_url = ""
        is_based_on_url = get_element_attribute(
            license_element, "dc:isBasedOn", "rdf:resource", ""
        )
        replacement_url = get_element_attribute(
            license_element, "dcq:isReplacedBy", "rdf:resource", ""
        )

        elt = license_element.find("dc:isReplacedBy", namespaces)
        if (
            elt is not None
        ):  # Note: Must compare directly to None. Just checking truthiness of an ET element does something else.
            print(
                f"WARNING: This license {license_url} is using <dc:isReplacedBy>. "
                f"It probably should be <dcq:isReplacedBy> and that's "
                f"how we are treating it."
            )
            replacement_url = elt.attrib[namespaced("rdf", "resource")]
            license_element.remove(elt)

        #
        # Values that refer to other records that aren't licenses.
        #

        jurisdiction_url = get_element_attribute(
            license_element, "cc:jurisdiction", "rdf:resource", ""
        )

        jurisdiction = (
            get_jurisdiction_for_code(get_code_from_jurisdiction_url(jurisdiction_url))
            if jurisdiction_url
            else None
        )

        creator_url = get_element_attribute(
            license_element, "dc:creator", "rdf:resource", ""
        )
        creator = get_creator_for_url(creator_url) if creator_url else None

        license_class_url = get_element_attribute(
            license_element, "cc:licenseClass", "rdf:resource"
        )
        license_class = (
            get_license_class_for_url(license_class_url) if license_class_url else None
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
        license = License(
            about=license_url,
            license_code=get_element_text(license_element, "dc:identifier"),
            version=get_element_text(license_element, "dcq:hasVersion", ""),
            jurisdiction=jurisdiction,
            creator=creator,
            license_class=license_class,
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
        # Save the URLs so we can find the licenses later and fix the fields
        license.source_url = source_url
        license.is_replaced_by_url = replacement_url
        license.is_based_on_url = is_based_on_url
        # And the legal codes
        license.legal_codes_to_add = []

        # Other objects that link to the License object

        # legal code
        #  <cc:legalcode rdf:resource="http://creativecommons.org/licenses/by-nc-nd/3.0/it/legalcode"/>
        # Does not specify language. For the non-english ones, we should already have
        # processed a <Description> that told us what the language is. There might be
        # no Description for the English ones, though.
        for legal_code_element in license_element.findall("cc:legalcode", namespaces):
            code_url = legal_code_element.attrib[namespaced("rdf", "resource")]
            # If we don't already know a language for this legalcode, assume it's English.
            legal_code = get_legal_code_for_url(
                code_url, language=get_language_for_code(DEFAULT_LANGUAGE_CODE)
            )
            license.legal_codes_to_add.append(legal_code)
            license_element.remove(legal_code_element)

        # titles
        for title_element in license_element.findall("dc:title", namespaces):
            # attribute "xml:lang" is almost always present - but missing every now and then.
            lang_key = namespaced("xml", "lang")
            if lang_key in title_element.attrib:
                lang_code = title_element.attrib[lang_key]
            else:
                lang_code = DEFAULT_LANGUAGE_CODE
            language = get_language_for_code(lang_code)
            get_translated_license_name(license, language, title_element.text)
            license_element.remove(title_element)

        # logos
        for logo_element in license_element.findall("foaf:logo", namespaces):
            logo_url = logo_element.attrib[namespaced("rdf", "resource")]
            LICENSE_LOGOS.append(LicenseLogo(image=logo_url, license=license))
            license_element.remove(logo_element)

        if len(list(license_element)):  # pragma: no cover
            for child in list(license_element):
                print(child)
            raise Exception("MISSED SOMETHING - see list just above this")

        self.licenses[license.about] = license
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
    elif default_value is NO_DEFAULT:  # pragma: no cover
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
    elif default_value is NO_DEFAULT:  # pragma: no cover
        raise Exception("{} not found and no default allowed".format(tag))
    else:
        return default_value
