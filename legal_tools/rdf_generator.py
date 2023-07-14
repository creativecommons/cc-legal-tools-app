# Third-party
from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import DC, DCTERMS, FOAF, RDF, XSD

# First-party/Local
from legal_tools.models import LegalCode, Tool


def generate_rdf_triples(unit, version, jurisdiction=None):
    # Retrieving license data from the database based on the arguments.
    if jurisdiction:
        license_data = Tool.objects.filter(
            unit=unit, version=version, jurisdiction_code=jurisdiction
        ).first()
    else:
        license_data = Tool.objects.filter(unit=unit, version=version).first()

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
    license_uri = URIRef(license_data.base_url)

    g.add((license_uri, DC.identifier, Literal(f"{unit}")))
    g.add((license_uri, DCTERMS.hasVersion, Literal(f"{version}")))
    g.add((license_uri, DC.creator, URIRef(license_data.creator_url)))

    # This will be changed as other types of license types are added
    g.add(
        (
            license_uri,
            CC.licenseClass,
            URIRef(license_data.creator_url + "/license/"),
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
                    "https://creativecommons.org/international/"
                    + f"{jurisdiction}"
                ),
            )
        )

    # Extracted the corresponding id of the Tool from LegalCode and then
    # created according entries (CC.legalcode, DC.title)
    # using appropriate property of LegalCode.
    legal_code_ids = license_data.legal_codes.values_list("id", flat=True)
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
                URIRef(license_data.creator_url + legal_code_url),
            )
        )
        # added DCTERMS.language for every legal_code_url
        # currently the output is not sorted as it should be; but it is expected soon.
        g.add((CC[legal_code_url], DCTERMS.language, Literal(tool_lang)))

    # Adding properties
    # Permits
    if license_data.permits_derivative_works:
        g.add((license_uri, CC.permits, CC.DerivativeWorks))
    if license_data.permits_distribution:
        g.add((license_uri, CC.permits, CC.Distribution))
    if license_data.permits_reproduction:
        g.add((license_uri, CC.permits, CC.Reproduction))
    if license_data.permits_sharing:
        g.add((license_uri, CC.permits, CC.Sharing))

    # Requires
    if license_data.requires_attribution:
        g.add((license_uri, CC.requires, CC.Attribution))
    if license_data.requires_notice:
        g.add((license_uri, CC.requires, CC.Notice))
    if license_data.requires_share_alike:
        g.add((license_uri, CC.requires, CC.ShareAlike))
    if license_data.requires_source_code:
        g.add((license_uri, CC.requires, CC.SourceCode))

    # Prohibits
    if license_data.prohibits_commercial_use:
        g.add((license_uri, CC.prohibits, CC.CommercialUse))
    if license_data.prohibits_high_income_nation_use:
        g.add((license_uri, CC.prohibits, CC.HighIncomeNationUse))

    return g
