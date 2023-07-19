# Standard library
from urllib.parse import urlparse, urlunparse

# Third-party
from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import DC, DCTERMS, FOAF, RDF, XSD

# First-party/Local
from legal_tools.models import LegalCode, Tool


def convert_https_to_http(url):
    parsed_url = urlparse(url)
    if parsed_url.scheme == "https":
        parsed_url = parsed_url._replace(scheme="http")
    return urlunparse(parsed_url)


def generate_rdf_triples(unit, version, jurisdiction=None):
    # Retrieving license data from the database based on the arguments.
    if jurisdiction:
        tool_obj = Tool.objects.filter(
            unit=unit, version=version, jurisdiction_code=jurisdiction
        ).first()
    else:
        tool_obj = Tool.objects.filter(unit=unit, version=version).first()

    # The relevant namespaces for RDF elements
    CC = Namespace("http://creativecommons.org/ns#")

    g = Graph()

    # Bind namespaces
    g.bind("cc", CC)
    g.bind("dc", DC)
    g.bind("dcq", DCTERMS)
    g.bind("foaf", FOAF)
    g.bind("rdf", RDF)
    g.bind("xsd", XSD)

    # license URI
    license_uri = URIRef(convert_https_to_http(tool_obj.base_url))

    g.add((license_uri, DC.identifier, Literal(f"{unit}")))
    g.add((license_uri, DCTERMS.hasVersion, Literal(f"{version}")))
    g.add(
        (
            license_uri,
            DC.creator,
            URIRef(convert_https_to_http(tool_obj.creator_url)),
        )
    )

    # This will be changed as other types of license types are added
    g.add(
        (
            license_uri,
            CC.licenseClass,
            URIRef(
                convert_https_to_http(tool_obj.creator_url + "/license/")
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
                        tool_obj.creator_url + legal_code_url
                    )
                ),
            )
        )
        # added DCTERMS.language for every legal_code_url
        # currently the output is not sorted as it should be;
        # but it is expected soon.
        g.add((CC[legal_code_url], DCTERMS.language, Literal(tool_lang)))

    if tool_obj.deprecated_on:
        g.add((license_uri, CC.deprecatedOn, Literal(tool_obj.deprecated_on, datatype=XSD.date)))



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
