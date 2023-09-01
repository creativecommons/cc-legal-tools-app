# Standard library
import os.path
from urllib.parse import urlparse, urlunparse

# Third-party
from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import DCTERMS, FOAF, OWL, RDF, XSD

# First-party/Local
from legal_tools.models import LegalCode, Tool

# FOAF logo data
FOAF_LOGO_URL = "http://licensebuttons.net/l/"
SMALL_LOGO = "80x15.png"
LARGE_LOGO = "88x31.png"


def convert_https_to_http(url):
    parsed_url = urlparse(url)
    if parsed_url.scheme == "https":
        parsed_url = parsed_url._replace(scheme="http")
    return urlunparse(parsed_url)


def generate_rdf_file(
    category=None,
    unit=None,
    version=None,
    jurisdiction=None,
    generate_all_licenses=False,
):
    # Retrieving license data from the database based on the arguments.
    if generate_all_licenses is True:
        retrieved_tools = Tool.objects.all()
    else:
        if jurisdiction:
            retrieved_tool = Tool.objects.filter(
                category=category,
                unit=unit,
                version=version,
                jurisdiction_code=jurisdiction,
            ).first()
        else:
            retrieved_tool = Tool.objects.filter(
                category=category, unit=unit, version=version
            ).first()
        retrieved_tools = []
        retrieved_tools.append(retrieved_tool)

    # The relevant namespaces for RDF elements
    CC = Namespace("http://creativecommons.org/ns#")

    g = Graph()

    # Bind namespaces
    g.bind("cc", CC)
    g.bind("dcterms", DCTERMS)
    g.bind("foaf", FOAF)
    g.bind("owl", OWL)
    g.bind("rdf", RDF)
    g.bind("xsd", XSD)

    for tool_obj in retrieved_tools:
        legal_code_ids = tool_obj.legal_codes.values_list("id", flat=True)
        license_uri = URIRef(convert_https_to_http(tool_obj.base_url))

        # set cc:License (parent)
        g.set((license_uri, RDF.type, CC.License))

        # set cc:deprecatedOn, if applicable
        if tool_obj.deprecated_on:
            deprecated_on = Literal(tool_obj.deprecated_on, datatype=XSD.date)
            g.set((license_uri, CC.deprecatedOn, deprecated_on))

        # set cc:jurisdiction, if applicable
        if tool_obj.jurisdiction_code:
            jurisdiction_uri = URIRef(
                convert_https_to_http(
                    os.path.join(
                        tool_obj.creator_url,
                        "international",
                        tool_obj.jurisdiction_code,
                        "",  # legacy rdf has a trailing slash
                    )
                )
            )
            g.set((license_uri, CC.jurisdiction, jurisdiction_uri))

        # add cc:legalcode
        # (utilize LegalCode object(s) assciated with the current Tool object)
        for legal_code_id in legal_code_ids:
            lc_object = LegalCode.objects.get(id=legal_code_id)
            legal_code_uri = URIRef(
                convert_https_to_http(
                    f"{tool_obj.creator_url}{lc_object.legal_code_url}"
                )
            )
            data = Literal(legal_code_uri, lang=lc_object.language_code)
            g.add((license_uri, CC.legalcode, data))

        # set cc:licenseClass
        # (trailing "" creates a trailing slash to match legacy rdf)
        license_class_uriref = convert_https_to_http(tool_obj.creator_url)
        if tool_obj.category == "publicdomain":
            license_class_uriref = os.path.join(
                license_class_uriref, "choose", "publicdomain", ""
            )
        elif "sampling" in tool_obj.unit:
            license_class_uriref = os.path.join(
                license_class_uriref, "license", "sampling", ""
            )
        else:
            license_class_uriref = os.path.join(
                license_class_uriref, "license", ""
            )
        g.set((license_uri, CC.licenseClass, URIRef(license_class_uriref)))

        # add cc:permits, as applicable
        if tool_obj.permits_derivative_works:
            g.add((license_uri, CC.permits, CC.DerivativeWorks))
        if tool_obj.permits_distribution:
            g.add((license_uri, CC.permits, CC.Distribution))
        if tool_obj.permits_reproduction:
            g.add((license_uri, CC.permits, CC.Reproduction))
        if tool_obj.permits_sharing:
            g.add((license_uri, CC.permits, CC.Sharing))

        # add cc:prohibits, as applicable
        if tool_obj.prohibits_commercial_use:
            g.add((license_uri, CC.prohibits, CC.CommercialUse))
        if tool_obj.prohibits_high_income_nation_use:
            g.add((license_uri, CC.prohibits, CC.HighIncomeNationUse))

        # add cc:requires, as applicable
        if tool_obj.requires_attribution:
            g.add((license_uri, CC.requires, CC.Attribution))
        if tool_obj.requires_notice:
            g.add((license_uri, CC.requires, CC.Notice))
        if tool_obj.requires_share_alike:
            g.add((license_uri, CC.requires, CC.ShareAlike))

        # set dcterms:creator
        creator = URIRef(convert_https_to_http(tool_obj.creator_url))
        g.set((license_uri, DCTERMS.creator, creator))

        # set dcterms:Jurisdiction
        if tool_obj.jurisdiction_code:
            if tool_obj.jurisdiction_code == "igo":
                jurisdiction_code = "un"
            else:
                jurisdiction_code = tool_obj.jurisdiction_code
            data = Literal(jurisdiction_code, datatype=DCTERMS.ISO3166)
            g.set((license_uri, DCTERMS.Jurisdiction, data))

        # set dcterms:hasVersion
        version = Literal(f"{tool_obj.version}")
        g.set((license_uri, DCTERMS.hasVersion, version))

        # set dcterms:identifier
        g.set((license_uri, DCTERMS.identifier, Literal(f"{tool_obj.unit}")))

        # set dcterms:isReplacedBy, if applicable
        if tool_obj.is_replaced_by:
            # Convert to Literal so that the URL string is stored instead of
            # the object referenced
            replaced_by = Literal(
                URIRef(convert_https_to_http(tool_obj.is_replaced_by.base_url))
            )
            g.set((license_uri, DCTERMS.isReplacedBy, replaced_by))

        # add dcterms:LicenseDocument
        # (utilize LegalCode object(s) assciated with the current Tool object)
        for legal_code_id in legal_code_ids:
            lc_object = LegalCode.objects.get(id=legal_code_id)
            legal_code_uri = URIRef(
                f"{tool_obj.creator_url}{lc_object.legal_code_url}"
            )
            data = Literal(legal_code_uri, lang=lc_object.language_code)
            g.add((license_uri, DCTERMS.LicenseDocument, data))

        # set dcterms:source, if applicable
        if tool_obj.source:
            based_on = URIRef(convert_https_to_http(tool_obj.source))
            g.set((license_uri, DCTERMS.source, based_on))

        # add dcterms:title
        # (utilize LegalCode object(s) assciated with the current Tool object)
        for legal_code_id in legal_code_ids:
            lc_object = LegalCode.objects.get(id=legal_code_id)
            data = Literal(lc_object.title, lang=lc_object.language_code)
            g.add((license_uri, DCTERMS.title, data))

        # add foaf:logo
        if tool_obj.jurisdiction_code:
            logo_prefix = (
                f"{FOAF_LOGO_URL}{tool_obj.unit}"
                f"/{tool_obj.version}/{tool_obj.jurisdiction_code}"
            )
        else:
            logo_prefix = f"{FOAF_LOGO_URL}{tool_obj.unit}/{tool_obj.version}"
        logo_url_large = f"{logo_prefix}/{LARGE_LOGO}"
        logo_url_small = f"{logo_prefix}/{SMALL_LOGO}"
        g.add((license_uri, FOAF.logo, URIRef(logo_url_large)))
        g.add((license_uri, FOAF.logo, URIRef(logo_url_small)))

        # set owl:sameAs (alias HTTPS)
        g.set((license_uri, OWL.sameAs, URIRef(tool_obj.base_url)))

    return g


def generate_images_rdf():
    all_tools = Tool.objects.all()

    EXIF = Namespace("http://www.w3.org/2003/12/exif/ns#")

    image_graph = Graph()

    image_graph.bind("exif", EXIF)

    for tool in all_tools:
        if tool.jurisdiction_code:
            uriref = {
                "large": URIRef(
                    f"{FOAF_LOGO_URL}{tool.unit}/{tool.version}/"
                    f"{tool.jurisdiction_code}/{LARGE_LOGO}"
                ),
                "small": URIRef(
                    f"{FOAF_LOGO_URL}{tool.unit}/{tool.version}/"
                    f"{tool.jurisdiction_code}/{SMALL_LOGO}"
                ),
            }

        else:
            uriref = {
                "large": URIRef(
                    f"{FOAF_LOGO_URL}{tool.unit}/{tool.version}/{LARGE_LOGO}"
                ),
                "small": URIRef(
                    f"{FOAF_LOGO_URL}{tool.unit}/{tool.version}/{SMALL_LOGO}"
                ),
            }
        image_graph.add((uriref["large"], EXIF.width, Literal("88")))
        image_graph.add((uriref["large"], EXIF.height, Literal("31")))

        image_graph.add((uriref["small"], EXIF.width, Literal("80")))
        image_graph.add((uriref["small"], EXIF.height, Literal("15")))

    return image_graph
