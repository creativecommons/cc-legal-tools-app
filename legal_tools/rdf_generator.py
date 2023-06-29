# Third-party
from rdflib import Graph, Literal, Namespace, URIRef

# First-party/Local
from legal_tools.models import Tool


def generate_rdf_triples(unit, version):
    # Retrieving license data from the database based on the unit and version arguments.
    license_data = Tool.objects.filter(unit=unit, version=version).first()

    # The relevant namespaces for RDF elements
    RDF = Namespace("http://www.w3.org/1999/02/22-rdf-syntax-ns#")
    CC = Namespace("https://creativecommons.org/ns#")
    DCTYPES = Namespace("http://purl.org/dc/dcmitype/")
    DCT = Namespace("http://purl.org/dc/terms/")
    FOAF = Namespace("http://xmlns.com/foaf/0.1/")
    XSD = Namespace("http://www.w3.org/2001/XMLSchema#")
    DC = Namespace("http://purl.org/dc/elements/1.1/")

    g = Graph()

    # Bind namespaces
    g.bind("rdf", RDF)
    g.bind("cc", CC)
    g.bind("dctypes", DCTYPES)
    g.bind("dct", DCT)
    g.bind("foaf", FOAF)
    g.bind("xsd", XSD)
    g.bind("dc", DC)

    # license URI
    license_uri = URIRef(license_data.base_url)

    g.add((license_uri, RDF.type, CC.License))
    g.add((license_uri, DCT.title, Literal(f"CC {unit.upper()} {version}")))
    g.add((license_uri, CC.licenseVersion, Literal(f"{version}")))
    g.add(
        (
            license_uri,
            DCT.description,
            Literal(" NEED SUGGESTIONS ON WHAT TO PUT HERE."),
        )
    )
    g.add((license_uri, CC.legalcode, URIRef(license_uri + "legalcode")))
    g.add((license_uri, FOAF.homepage, URIRef(license_uri)))
    g.add((license_uri, FOAF.maker, URIRef("https://creativecommons.org/")))

    # Adding permit properties

    if license_data.permits_derivative_works:
        g.add((license_uri, CC.permits, CC.DerivativeWorks))

    if license_data.permits_reproduction:
        g.add((license_uri, CC.permits, CC.Reproduction))

    if license_data.permits_distribution:
        g.add((license_uri, CC.permits, CC.Distribution))

    if license_data.permits_sharing:
        g.add((license_uri, CC.permits, CC.Sharing))

    if license_data.requires_share_alike:
        g.add((license_uri, CC.requires, CC.ShareAlike))

    if license_data.requires_notice:
        g.add((license_uri, CC.requires, CC.Notice))

    if license_data.requires_attribution:
        g.add((license_uri, CC.requires, CC.Attribution))

    if license_data.requires_source_code:
        g.add((license_uri, CC.requires, CC.SourceCode))

    if license_data.prohibits_commercial_use:
        g.add((license_uri, CC.prohibits, CC.CommercialUse))

    if license_data.prohibits_high_income_nation_use:
        g.add((license_uri, CC.prohibits, CC.HighIncomeNationUse))

    return g
