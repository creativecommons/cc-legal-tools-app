# Standard library
import os.path
from urllib.parse import urlparse, urlunparse

# Third-party
from lxml import etree
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


def generate_foaf_logo_uris(unit, version, jurisdiction_code):
    uri_prefix = os.path.join(FOAF_LOGO_URL, unit, version)
    if jurisdiction_code:
        logo_uris = {
            "large": URIRef(
                os.path.join(uri_prefix, jurisdiction_code, LARGE_LOGO)
            ),
            "small": URIRef(
                os.path.join(uri_prefix, jurisdiction_code, SMALL_LOGO)
            ),
        }
    else:
        logo_uris = {
            "large": URIRef(os.path.join(uri_prefix, LARGE_LOGO)),
            "small": URIRef(os.path.join(uri_prefix, SMALL_LOGO)),
        }
    return logo_uris


def generate_images_rdf():
    all_tools = Tool.objects.all()

    EXIF = Namespace("http://www.w3.org/2003/12/exif/ns#")
    image_graph = Graph()
    image_graph.bind("exif", EXIF)

    for tool in all_tools:
        logo_uris = generate_foaf_logo_uris(
            tool.unit, tool.version, tool.jurisdiction_code
        )
        image_graph.add((logo_uris["large"], EXIF.width, Literal("88")))
        image_graph.add((logo_uris["large"], EXIF.height, Literal("31")))

        image_graph.add((logo_uris["small"], EXIF.width, Literal("80")))
        image_graph.add((logo_uris["small"], EXIF.height, Literal("15")))

    return image_graph


def generate_legal_code_rdf(
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

    for tool in retrieved_tools:
        legal_code_ids = tool.legal_codes.values_list("id", flat=True)
        license_uri = URIRef(convert_https_to_http(tool.base_url))

        # set cc:License (parent)
        g.set((license_uri, RDF.type, CC.License))

        # set cc:deprecatedOn, if applicable
        if tool.deprecated_on:
            deprecated_on = Literal(tool.deprecated_on, datatype=XSD.date)
            g.set((license_uri, CC.deprecatedOn, deprecated_on))

        # set cc:jurisdiction, if applicable
        if tool.jurisdiction_code:
            jurisdiction_uri = URIRef(
                convert_https_to_http(
                    os.path.join(
                        tool.creator_url,
                        "international",
                        tool.jurisdiction_code,
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
                    f"{tool.creator_url}{lc_object.legal_code_url}"
                )
            )
            data = Literal(legal_code_uri, lang=lc_object.language_code)
            g.add((license_uri, CC.legalcode, data))

        # set cc:licenseClass
        # (trailing "" creates a trailing slash to match legacy rdf)
        license_class_uriref = convert_https_to_http(tool.creator_url)
        if tool.category == "publicdomain":
            license_class_uriref = os.path.join(
                license_class_uriref, "choose", "publicdomain", ""
            )
        elif "sampling" in tool.unit:
            license_class_uriref = os.path.join(
                license_class_uriref, "license", "sampling", ""
            )
        else:
            license_class_uriref = os.path.join(
                license_class_uriref, "license", ""
            )
        g.set((license_uri, CC.licenseClass, URIRef(license_class_uriref)))

        # add cc:permits, as applicable
        if tool.permits_derivative_works:
            g.add((license_uri, CC.permits, CC.DerivativeWorks))
        if tool.permits_distribution:
            g.add((license_uri, CC.permits, CC.Distribution))
        if tool.permits_reproduction:
            g.add((license_uri, CC.permits, CC.Reproduction))
        if tool.permits_sharing:
            g.add((license_uri, CC.permits, CC.Sharing))

        # add cc:prohibits, as applicable
        if tool.prohibits_commercial_use:
            g.add((license_uri, CC.prohibits, CC.CommercialUse))
        if tool.prohibits_high_income_nation_use:
            g.add((license_uri, CC.prohibits, CC.HighIncomeNationUse))

        # add cc:requires, as applicable
        if tool.requires_attribution:
            g.add((license_uri, CC.requires, CC.Attribution))
        if tool.requires_notice:
            g.add((license_uri, CC.requires, CC.Notice))
        if tool.requires_share_alike:
            g.add((license_uri, CC.requires, CC.ShareAlike))

        # set dcterms:creator
        creator = URIRef(convert_https_to_http(tool.creator_url))
        g.set((license_uri, DCTERMS.creator, creator))

        # set dcterms:Jurisdiction
        if tool.jurisdiction_code:
            if tool.jurisdiction_code == "igo":
                jurisdiction_code = "un"
            else:
                jurisdiction_code = tool.jurisdiction_code
            data = Literal(jurisdiction_code, datatype=DCTERMS.ISO3166)
            g.set((license_uri, DCTERMS.Jurisdiction, data))

        # set dcterms:hasVersion
        version = Literal(f"{tool.version}")
        g.set((license_uri, DCTERMS.hasVersion, version))

        # set dcterms:identifier
        g.set((license_uri, DCTERMS.identifier, Literal(f"{tool.unit}")))

        # set dcterms:isReplacedBy, if applicable
        if tool.is_replaced_by:
            # Convert to Literal so that the URL string is stored instead of
            # the object referenced
            replaced_by = Literal(
                URIRef(convert_https_to_http(tool.is_replaced_by.base_url))
            )
            g.set((license_uri, DCTERMS.isReplacedBy, replaced_by))

        # add dcterms:LicenseDocument
        # (utilize LegalCode object(s) assciated with the current Tool object)
        for legal_code_id in legal_code_ids:
            lc_object = LegalCode.objects.get(id=legal_code_id)
            legal_code_uri = URIRef(
                f"{tool.creator_url}{lc_object.legal_code_url}"
            )
            data = Literal(legal_code_uri, lang=lc_object.language_code)
            g.add((license_uri, DCTERMS.LicenseDocument, data))

        # set dcterms:source, if applicable
        if tool.source:
            # Convert to Literal so that the URL string is stored instead of
            # the object referenced
            source = Literal(
                URIRef(convert_https_to_http(tool.source.base_url))
            )
            g.set((license_uri, DCTERMS.source, source))

        # add dcterms:title
        # (utilize LegalCode object(s) assciated with the current Tool object)
        for legal_code_id in legal_code_ids:
            lc_object = LegalCode.objects.get(id=legal_code_id)
            data = Literal(lc_object.title, lang=lc_object.language_code)
            g.add((license_uri, DCTERMS.title, data))

        # add foaf:logo
        logo_uris = generate_foaf_logo_uris(
            tool.unit, tool.version, tool.jurisdiction_code
        )
        g.add((license_uri, FOAF.logo, logo_uris["large"]))
        g.add((license_uri, FOAF.logo, logo_uris["small"]))

        # set owl:sameAs (alias HTTPS)
        g.set((license_uri, OWL.sameAs, URIRef(tool.base_url)))

    return g


def order_rdf_xml(serialized_rdf_content):
    def uri2prefix(name, nsmap):
        """
        Convert QNAME URI to prefix
        """
        qname = etree.QName(name)
        # rdflib assumes xml namespace, but lxml does not
        nsmap["xml"] = "http://www.w3.org/XML/1998/namespace"
        uri_map = {y: x for x, y in nsmap.items()}
        prefix = f"{uri_map[qname.namespace]}:{qname.localname}"
        return prefix

    def get_node_key(node):
        """
        Return the sorting key of an xml node using tag and attributes (using
        prefixes so that order matches expectations when files are read by
        humans)
        """
        tag = uri2prefix(node.tag, node.nsmap)
        attributes = []
        for qname, value in sorted(node.attrib.items()):
            prefix = uri2prefix(qname, node.nsmap)
            attributes.append(f"{prefix}:{value}")
        key = f"{tag} {' '.join(attributes)}"
        return key

    def sort_children(node):
        """
        Sort children by tag and attributes
        """
        if not isinstance(node.tag, str):
            # Only sort tags (not comments or data)
            return
        # sort this node
        node[:] = sorted(node, key=lambda child: get_node_key(child))
        # sort this node's children
        for child in node:
            sort_children(child)

    # Step 0: rdflib
    #   - rdflib's pretty-xml serializer does not support deterministic output.
    #   - left alone, this would result in unnecessary and obfuscating changes
    #     in git commits

    # Step 1: lxml
    #   - order XML elements by tag and attribute (using prefixes so they are
    #     sorted appropriately when serialized)
    #   - lxml, however, does not support deterministic output of the namespace
    parser = etree.XMLParser(remove_blank_text=True)
    root = etree.fromstring(serialized_rdf_content.encode(), parser)
    sort_children(root)
    serialized_rdf_content = etree.tostring(
        root, encoding="utf-8", xml_declaration=True, pretty_print=True
    )

    # Step 2: manually sort namespaces in line 2 of serialized RDF/XML content
    serialized_rdf_content = serialized_rdf_content.decode().split("\n")
    namespace_line = serialized_rdf_content[1].split()
    rdf_rdf = namespace_line.pop(0)
    namespace_line[-1] = namespace_line[-1].rstrip(">")
    namespace_line.sort()
    namespace_line.insert(0, rdf_rdf)
    namespace_line[-1] = f"{namespace_line[-1]}>"
    serialized_rdf_content[1] = " ".join(namespace_line)
    serialized_rdf_content = "\n".join(serialized_rdf_content)

    return serialized_rdf_content
