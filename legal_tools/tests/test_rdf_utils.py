# Third-party
from django.test import TestCase

# First-party/Local
from legal_tools.rdf_utils import convert_https_to_http, order_rdf_xml

EXPECTED_RDF_XML = """\
<?xml version='1.0' encoding='utf-8'?>
<rdf:RDF\
 xmlns:cc="http://creativecommons.org/ns#"\
 xmlns:dcterms="http://purl.org/dc/terms/"\
 xmlns:foaf="http://xmlns.com/foaf/0.1/"\
 xmlns:owl="http://www.w3.org/2002/07/owl#"\
 xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"\
>
  <cc:License rdf:about="http://creativecommons.org/licenses/by-nc-sa/4.0/">
    <cc:legalcode xml:lang="ar">legalcode.ar</cc:legalcode>
    <cc:legalcode xml:lang="en">legalcode.en</cc:legalcode>
    <cc:legalcode xml:lang="nl">legalcode.nl</cc:legalcode>
    <cc:licenseClass rdf:resource="http://creativecommons.org/license/"/>
    <cc:permits rdf:resource="http://creativecommons.org/ns#DerivativeWorks"/>
    <cc:permits rdf:resource="http://creativecommons.org/ns#Distribution"/>
    <cc:permits rdf:resource="http://creativecommons.org/ns#Reproduction"/>
    <cc:prohibits rdf:resource="http://creativecommons.org/ns#CommercialUse"/>
    <cc:requires rdf:resource="http://creativecommons.org/ns#Attribution"/>
    <cc:requires rdf:resource="http://creativecommons.org/ns#Notice"/>
    <cc:requires rdf:resource="http://creativecommons.org/ns#ShareAlike"/>
    <dcterms:LicenseDocument xml:lang="ar">ar</dcterms:LicenseDocument>
    <dcterms:LicenseDocument xml:lang="en">en</dcterms:LicenseDocument>
    <dcterms:LicenseDocument xml:lang="nl">nl</dcterms:LicenseDocument>
    <dcterms:creator rdf:resource="http://creativecommons.org"/>
    <dcterms:hasVersion>4.0</dcterms:hasVersion>
    <dcterms:identifier>by-nc-sa</dcterms:identifier>
    <dcterms:source>licenses/by-nc-sa/3.0/</dcterms:source>
    <foaf:logo rdf:resource="l/by-nc-sa/4.0/80x15.png"/>
    <foaf:logo rdf:resource="l/by-nc-sa/4.0/88x31.png"/>
    <owl:sameAs rdf:resource="licenses/by-nc-sa/4.0/"/>
  </cc:License>
</rdf:RDF>
"""
UNORDERED_RDF_XML = """\
<?xml version='1.0' encoding='utf-8'?>
<rdf:RDF
    xmlns:owl="http://www.w3.org/2002/07/owl#"
    xmlns:dcterms="http://purl.org/dc/terms/"
    xmlns:foaf="http://xmlns.com/foaf/0.1/"
    xmlns:cc="http://creativecommons.org/ns#"
    xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">
  <cc:License rdf:about="http://creativecommons.org/licenses/by-nc-sa/4.0/">
    <cc:legalcode xml:lang="ar">legalcode.ar</cc:legalcode>
    <cc:legalcode xml:lang="nl">legalcode.nl</cc:legalcode>
    <cc:requires rdf:resource="http://creativecommons.org/ns#ShareAlike"/>
    <cc:requires rdf:resource="http://creativecommons.org/ns#Notice"/>
    <cc:requires rdf:resource="http://creativecommons.org/ns#Attribution"/>
    <cc:prohibits rdf:resource="http://creativecommons.org/ns#CommercialUse"/>
    <cc:permits rdf:resource="http://creativecommons.org/ns#Distribution"/>
    <cc:permits rdf:resource="http://creativecommons.org/ns#DerivativeWorks"/>
    <cc:licenseClass rdf:resource="http://creativecommons.org/license/"/>
    <dcterms:LicenseDocument xml:lang="en">en</dcterms:LicenseDocument>
    <dcterms:LicenseDocument xml:lang="nl">nl</dcterms:LicenseDocument>
    <cc:permits rdf:resource="http://creativecommons.org/ns#Reproduction"/>
    <dcterms:LicenseDocument xml:lang="ar">ar</dcterms:LicenseDocument>
    <dcterms:creator rdf:resource="http://creativecommons.org"/>
    <dcterms:hasVersion>4.0</dcterms:hasVersion>
    <dcterms:identifier>by-nc-sa</dcterms:identifier>
    <dcterms:source>licenses/by-nc-sa/3.0/</dcterms:source>
    <foaf:logo rdf:resource="l/by-nc-sa/4.0/80x15.png"/>
    <cc:legalcode xml:lang="en">legalcode.en</cc:legalcode>
    <foaf:logo rdf:resource="l/by-nc-sa/4.0/88x31.png"/>
    <owl:sameAs rdf:resource="licenses/by-nc-sa/4.0/"/>
  </cc:License>
</rdf:RDF>
"""


class TestRdfUtils(TestCase):
    def test_convert_https_to_http(self):
        test_url = "https://https-https.test"
        expected_url = "http://https-https.test"
        converted_url = convert_https_to_http(test_url)
        self.assertEqual(expected_url, converted_url)

        test_url = "http://https-https.test"
        expected_url = "http://https-https.test"
        converted_url = convert_https_to_http(test_url)
        self.assertEqual(expected_url, converted_url)

    def test_order_rdf_xml(self):
        test_rdf = UNORDERED_RDF_XML
        expected_rdf = EXPECTED_RDF_XML
        ordered_rdf = order_rdf_xml(test_rdf)
        self.assertEqual(expected_rdf, ordered_rdf)
