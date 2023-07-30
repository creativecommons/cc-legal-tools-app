# Standard library
from urllib.parse import urlparse, urlunparse

# Third-party
from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import DC, DCTERMS, FOAF, OWL, RDF, XSD

# First-party/Local
from legal_tools.models import LegalCode, Tool


def convert_https_to_http(url):
    parsed_url = urlparse(url)
    if parsed_url.scheme == "https":
        parsed_url = parsed_url._replace(scheme="http")
    return urlunparse(parsed_url)


# FOAF logo data
foaf_logo_url = "http://licensebuttons.net/l/"
small_logo = "80x15.png"
large_logo = "88x31.png"


def generate_rdf_file(category, unit, version, jurisdiction=None):
    # Retrieving license data from the database based on the arguments.
    if jurisdiction:
        tool_obj = Tool.objects.filter(
            category=category,
            unit=unit,
            version=version,
            jurisdiction_code=jurisdiction,
        ).first()
    else:
        tool_obj = Tool.objects.filter(
            category=category, unit=unit, version=version
        ).first()

    # The relevant namespaces for RDF elements
    CC = Namespace("http://creativecommons.org/ns#")

    g = Graph()

    # Bind namespaces
    g.bind("cc", CC)
    g.bind("dc", DC)
    g.bind("dcterms", DCTERMS)
    g.bind("foaf", FOAF)
    g.bind("owl", OWL)
    g.bind("rdf", RDF)
    g.bind("xsd", XSD)

    # license URI
    license_uri = URIRef(convert_https_to_http(tool_obj.base_url))

    g.set((license_uri, RDF.type, CC.License))
    g.add((license_uri, DC.identifier, Literal(f"{unit}")))
    g.add((license_uri, DCTERMS.hasVersion, Literal(f"{version}")))
    g.add((license_uri, OWL.sameAs, URIRef(tool_obj.base_url)))

    g.add(
        (
            license_uri,
            DC.creator,
            URIRef(convert_https_to_http(tool_obj.creator_url)),
        )
    )

    # adding cc:licenseClass
    if category == "publicdomain":
        g.add(
            (
                license_uri,
                CC.licenseClass,
                URIRef(
                    convert_https_to_http(
                        f"{tool_obj.creator_url}/choose/{tool_obj.unit}/"
                    )
                ),
            )
        )

    elif unit in ["sampling", "sampling+"]:
        g.add(
            (
                license_uri,
                CC.licenseClass,
                URIRef(
                    convert_https_to_http(
                        f"{tool_obj.creator_url}/{tool_obj.category}/sampling/"
                    )
                ),
            )
        )
    else:
        g.add(
            (
                license_uri,
                CC.licenseClass,
                URIRef(
                    convert_https_to_http(
                        f"{tool_obj.creator_url}/{tool_obj.category}/"
                    )
                ),
            )
        )

    # g.add(
    #     (
    #         license_uri,
    #         DCT.description,
    #         Literal(" NEED SUGGESTIONS ON WHAT TO PUT HERE."),
    #     )
    # )

    if jurisdiction:
        g.add(
            (
                license_uri,
                CC.jurisdiction,
                URIRef(
                    "http://creativecommons.org/international/"
                    + f"{jurisdiction}"
                ),
            )
        )
        g.add(
            (
                license_uri,
                FOAF.logo,
                URIRef(
                    f"{foaf_logo_url}{unit}/{version}/{jurisdiction}/{large_logo}"
                ),
            )
        )
        g.add(
            (
                license_uri,
                FOAF.logo,
                URIRef(
                    f"{foaf_logo_url}{unit}/{version}/{jurisdiction}/{small_logo}"
                ),
            )
        )
    else:
        g.add(
            (
                license_uri,
                FOAF.logo,
                URIRef(f"{foaf_logo_url}{unit}/{version}/{large_logo}"),
            )
        )
        g.add(
            (
                license_uri,
                FOAF.logo,
                URIRef(f"{foaf_logo_url}{unit}/{version}/{small_logo}"),
            )
        )

    # Extracted the corresponding id of the Tool from LegalCode and then
    # created according entries (CC.legalcode, DC.title)
    # using appropriate property of LegalCode.
    legal_code_ids = tool_obj.legal_codes.values_list("id", flat=True)
    for legal_code_id in legal_code_ids:
        legal_code_object = LegalCode.objects.get(id=legal_code_id)

        get_tool_title = legal_code_object.title
        tool_lang = legal_code_object.language_code
        tool_title_data = Literal(get_tool_title, lang=tool_lang)
        g.add((license_uri, DC.title, (tool_title_data)))

        legal_code_url = legal_code_object.legal_code_url
        g.add(
            (
                license_uri,
                CC.legalcode,
                URIRef(
                    convert_https_to_http(
                        f"{tool_obj.creator_url}{legal_code_url}"
                    )
                ),
            )
        )
        # added DCTERMS.language for every legal_code_url
        # currently the output is not sorted as it should be;
        # but it is expected soon
        g.add((CC[legal_code_url], DCTERMS.language, Literal(tool_lang)))

    if tool_obj.deprecated_on:
        g.add(
            (
                license_uri,
                CC.deprecatedOn,
                Literal(tool_obj.deprecated_on, datatype=XSD.date),
            )
        )

    if tool_obj.is_replaced_by:
        g.add(
            (
                license_uri,
                DCTERMS.isReplacedBy,
                URIRef(
                    convert_https_to_http(tool_obj.is_replaced_by.base_url)
                ),
            )
        )

    if tool_obj.is_based_on:
        g.add(
            (
                license_uri,
                DC.source,
                URIRef(convert_https_to_http(tool_obj.is_based_on.base_url)),
            )
        )

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
            uriref_with_juris = {
                "large": URIRef(
                    f"{foaf_logo_url}{tool.unit}/{tool.version}/{tool.jurisdiction_code}/{large_logo}"
                ),
                "small": URIRef(
                    f"{foaf_logo_url}{tool.unit}/{tool.version}/{tool.jurisdiction_code}/{small_logo}"
                ),
            }
            image_graph.add(
                (uriref_with_juris["large"], EXIF.width, Literal("88"))
            )
            image_graph.add(
                (uriref_with_juris["large"], EXIF.height, Literal("31"))
            )

            image_graph.add(
                (uriref_with_juris["small"], EXIF.width, Literal("80"))
            )
            image_graph.add(
                (uriref_with_juris["small"], EXIF.height, Literal("15"))
            )

        else:
            uriref = {
                "large": URIRef(
                    f"{foaf_logo_url}{tool.unit}/{tool.version}/{large_logo}"
                ),
                "small": URIRef(
                    f"{foaf_logo_url}{tool.unit}/{tool.version}/{small_logo}"
                ),
            }
            image_graph.add((uriref["large"], EXIF.width, Literal("88")))
            image_graph.add((uriref["large"], EXIF.height, Literal("31")))

            image_graph.add((uriref["small"], EXIF.width, Literal("80")))
            image_graph.add((uriref["small"], EXIF.height, Literal("15")))

    return image_graph
