from rdflib import Graph, Namespace, Literal, URIRef

def generate_rdf_triples(license_name, version):
    
    # The relevant namespaces for RDF elements
    RDF=Namespace("http://www.w3.org/1999/02/22-rdf-syntax-ns#")
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
    license_uri = URIRef(f"https://creativecommons.org/licenses/{license_name}/{version}/")

    if license_name == "by":
        g.add((license_uri, RDF.type, CC.License))
        g.add((license_uri, DCT.title, Literal(f"CC {license_name.upper()} {version}")))
        g.add((license_uri, DCT.description, Literal("A Creative Commons Attribution 4.0 International License.")))
        g.add((license_uri, DCT.type, DCTYPES.Text))
        g.add((license_uri, FOAF.homepage, URIRef(license_uri)))
        g.add((license_uri, CC.legalcode, URIRef(license_uri + "legalcode")))
        g.add((license_uri, CC.permits, CC.Reproduction))
        g.add((license_uri, CC.permits, CC.Distribution))
        g.add((license_uri, CC.requires, CC.Attribution))
        g.add((license_uri, CC.requires, CC.Notice))
        g.add((license_uri, CC.prohibits, CC.CommercialUse))
        g.add((license_uri, CC.prohibits, CC.DerivativeWorks))

    else:
        # here we'll add more triples for remaining licenses.
        pass
    
    
    return g

# Example usage:
'''def main():
    rdf_graph = generate_rdf_triples('by', '4.0')
    rdf_data=rdf_graph.serialize(format="xml").strip('utf-8')
    print(rdf_data)

# Execute the main function
if __name__ == "__main__":
    main()'''
