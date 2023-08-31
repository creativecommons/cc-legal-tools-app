# Standard library
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
        # license URI
        license_uri = URIRef(convert_https_to_http(tool_obj.base_url))

        g.set((license_uri, RDF.type, CC.License))

        g.add((license_uri, DCTERMS.identifier, Literal(f"{tool_obj.unit}")))
        version = Literal(f"{tool_obj.version}")
        g.add((license_uri, DCTERMS.hasVersion, version))
        g.add((license_uri, OWL.sameAs, URIRef(tool_obj.base_url)))
        creator = URIRef(convert_https_to_http(tool_obj.creator_url))
        g.add((license_uri, DCTERMS.creator, creator))

        # adding cc:licenseClass
        if tool_obj.category == "publicdomain":
            license_class_uriref = URIRef(
                convert_https_to_http(
                    f"{tool_obj.creator_url}/choose/{tool_obj.unit}/"
                )
            )
        elif tool_obj.unit in ["sampling", "sampling+"]:
            license_class_uriref = URIRef(
                convert_https_to_http(
                    f"{tool_obj.creator_url}/{tool_obj.category}/sampling/"
                )
            )
        else:
            license_class_uriref = URIRef(
                convert_https_to_http(
                    f"{tool_obj.creator_url}/{tool_obj.category}/"
                )
            )
        g.add((license_uri, CC.licenseClass, license_class_uriref))

        if tool_obj.jurisdiction_code:
            logo_prefix = (
                f"{FOAF_LOGO_URL}{tool_obj.unit}"
                f"/{tool_obj.version}/{tool_obj.jurisdiction_code}"
            )
            jurisdiction_uri = URIRef(
                convert_https_to_http(
                    f"{tool_obj.creator_url}/international/"
                    f"{tool_obj.jurisdiction_code}"
                )
            )
            g.add((license_uri, CC.jurisdiction, jurisdiction_uri))
        else:
            logo_prefix = f"{FOAF_LOGO_URL}{tool_obj.unit}/{tool_obj.version}"

        logo_url_large = f"{logo_prefix}/{LARGE_LOGO}"
        logo_url_small = f"{logo_prefix}/{SMALL_LOGO}"
        g.add((license_uri, FOAF.logo, URIRef(logo_url_large)))
        g.add((license_uri, FOAF.logo, URIRef(logo_url_small)))

        # Extracted the corresponding id of the Tool from LegalCode and then
        # created according entries (CC.legalcode, DCTERMS.title)
        # using appropriate property of LegalCode.
        legal_code_ids = tool_obj.legal_codes.values_list("id", flat=True)
        for legal_code_id in legal_code_ids:
            legal_code_object = LegalCode.objects.get(id=legal_code_id)

            get_tool_title = legal_code_object.title
            tool_lang = legal_code_object.language_code
            tool_title_data = Literal(get_tool_title, lang=tool_lang)
            g.add((license_uri, DCTERMS.title, (tool_title_data)))

            legal_code_url = legal_code_object.legal_code_url
            cc_legal_code = URIRef(
                convert_https_to_http(
                    f"{tool_obj.creator_url}{legal_code_url}"
                )
            )
            g.add((license_uri, CC.legalcode, cc_legal_code))

            # added DCTERMS.language for every legal_code_url
            if not generate_all_licenses:
                g.add(
                    (CC[legal_code_url], DCTERMS.language, Literal(tool_lang))
                )

        if tool_obj.deprecated_on:
            deprecated_on = Literal(tool_obj.deprecated_on, datatype=XSD.date)
            g.add((license_uri, CC.deprecatedOn, deprecated_on))

        if tool_obj.is_replaced_by:
            replaced_by = URIRef(
                convert_https_to_http(tool_obj.is_replaced_by.base_url)
            )
            g.add((license_uri, DCTERMS.isReplacedBy, replaced_by))

        if tool_obj.is_based_on:
            based_on = URIRef(
                convert_https_to_http(tool_obj.is_based_on.base_url)
            )
            g.add((license_uri, DCTERMS.source, based_on))

        # Adding properties
        # Permits
        if tool_obj.permits_derivative_works:
            g.add((license_uri, CC.permits, CC.DerivativeWorks))
        if tool_obj.permits_distribution:
            g.add((license_uri, CC.permits, CC.Distribution))
        if tool_obj.permits_reproduction:
            g.add((license_uri, CC.permits, CC.Reproduction))
        if tool_obj.permits_sharing:
            g.add((license_uri, CC.permits, CC.Sharing))

        # Requires
        if tool_obj.requires_attribution:
            g.add((license_uri, CC.requires, CC.Attribution))
        if tool_obj.requires_notice:
            g.add((license_uri, CC.requires, CC.Notice))
        if tool_obj.requires_share_alike:
            g.add((license_uri, CC.requires, CC.ShareAlike))
        if tool_obj.requires_source_code:
            g.add((license_uri, CC.requires, CC.SourceCode))

        # Prohibits
        if tool_obj.prohibits_commercial_use:
            g.add((license_uri, CC.prohibits, CC.CommercialUse))
        if tool_obj.prohibits_high_income_nation_use:
            g.add((license_uri, CC.prohibits, CC.HighIncomeNationUse))

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
