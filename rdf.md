# RDF/XML


## Namespaces

```xml
<rdf:RDF
    xmlns:cc='http://creativecommons.org/ns#'
    xmlns:dcterms='http://purl.org/dc/terms/'
    xmlns:foaf='http://xmlns.com/foaf/0.1/'
    xmlns:owl='http://www.w3.org/2002/07/owl#'
    xmlns:rdf='http://www.w3.org/1999/02/22-rdf-syntax-ns#'
>
```

| Prefix | Name                | URL                                         |
| ------ | ------------------- | ------------------------------------------- |
| `cc`   | ccREL               | http://creativecommons.org/ns#              |
| `dcterms` | DCMI Metadata Terms | http://purl.org/dc/terms/                |
| `foaf` | FOAF Vocabulary     | http://xmlns.com/foaf/0.1/                  |
| `owl`  | OWL 2               | http://www.w3.org/2002/07/owl#              |
| `rdf`  | RDF XML Syntax      | http://www.w3.org/1999/02/22-rdf-syntax-ns# |


### ccREL

- [Describing Copyright in RDF - Creative Commons Rights Expression
  Language][ccrelns]
- [ccREL: The Creative Commons Rights Expression Language][ccrelpaper]
- [CC REL by Example][ccrelguide]

[ccrelpaper]: https://opensource.creativecommons.org/ccrel/
[ccrelns]: https://creativecommons.org/ns/
[ccrelguide]: https://opensource.creativecommons.org/ccrel-guide/


### DCMI Metadata Terms

- [DCMI: Dublin Core™][dublicore]
  - [DCMI: DCMI Metadata Terms][dcmiterms]

[dublincore]: https://www.dublincore.org/specifications/dublin-core/
[dcmiterms]: https://www.dublincore.org/specifications/dublin-core/dcmi-terms/


### FOAF Vocabulary

[FOAF - Wikipedia](https://en.wikipedia.org/wiki/FOAF) (retrieved 2023-07-20):
> FOAF (an acronym of friend of a friend) is a machine-readable ontology
> describing persons, their activities and their relations to other people and
> objects.

- [FOAF Vocabulary Specification][foafvocab]

[foafvocab]: http://xmlns.com/foaf/0.1/


### OWL 2

[OWL 2 Web Ontology Language Document Overview (Second Edition)][owl2overiew]
(retrieved 2023-07-20):
> The OWL 2 Web Ontology Language, informally OWL 2, is an ontology language
> for the Semantic Web with formally defined meaning. OWL 2 ontologies provide
> classes, properties, individuals, and data values and are stored as Semantic
> Web documents.

- [OWL 2 Web Ontology Language Document Overview (Second Edition)][owl2overiew]
- [OWL 2 Web Ontology Language Structural Specification and Functional-Style
  Syntax (Second Edition)][owl2spec]
- [OWL 2 Web Ontology Language XML Serialization (Second Edition)][owl2xml]
- [sameAs - Wikipedia][wikipediasameas]

[owl2overview]: https://www.w3.org/TR/owl2-overview/
[owl2spec]: https://www.w3.org/TR/owl2-syntax/
[owl2xml]: https://www.w3.org/TR/owl2-xml-serialization/
[wikipediasameas]: https://en.wikipedia.org/wiki/SameAs


### RDF XML Syntax

- [RDF 1.1 XML Syntax](https://www.w3.org/TR/rdf-syntax-grammar/)


## Changes

### Overview

The changes between the old legacy ccEngine RDF/XML and the new CC Legal Tools
App  RDF/XML aim to enhance clarity, accuracy, compatibility, and
standardization of the RDF representation of Creative Commons licenses.  The
improvements enhance the machine-readability and semantic understanding of the
licenses, enabling better integration and interpretation within digital
ecosystems. A general overview of what and why changes occured:


#### Improved Structure and Consistency

- What: The structure of the RDF/XML files has been improved for better
  clarity, consistency, and adherence to RDF standards.
- Why: A well-defined and consistent structure makes it easier for machines to
  process and interpret the RDF data accurately.
- Diff: The newer generated RDF/XML have a more organized and standardized
  structure compared to the older legacy RDF/XML, ensuring that elements and
  properties are consistently represented.


#### Updated License Information

- What: License information and conditions have been updated for some of the
  licenses.
- Why: Keeping license information up-to-date ensures that users and automated
  systems are aware of the current permissions and restrictions associated with
  the licenses.
- Diff: The newer generated RDF/XML include the most recent and updated license
  Information.


#### Alignment with RDF Best Practices

- What: Changes have been made to align the RDF/XML representation with best
  practices and recommendations in the RDF.
- Why: Following best practices ensures that the RDF data is structured in a
  way that maximizes interoperability and compatibility with other
  RDF-consuming applications.
- Diff: The newer generated RDF/XML adhere to established RDF conventions, such
  as using standardized namespaces, consistent naming conventions, and properly
  defined relationships.


### Version 1.0.0 RDF/XML Changes

Fixed wrong `cc:deprecatedOn` on the following legal tools:
- CC Sampling+ 1.0 BR
- CC Sampling+ 1.0 DE
- CC Sampling+ 1.0 TW
- CC Sampling+ 1.0

Updated RDF namespace
- `dcterms` replaced `dc` and `dcq`

Added missing license RDF/XML:
- CC BY-NC-ND 2.1 CA
- CC BY-NC-SA 2.1 CA
- CC BY-NC 2.1 CA
- CC BY-ND 2.1 CA
- CC BY 2.1 CA
- CC BY-NC-ND 3.0 AM
- CC BY-NC-SA 3.0 AM
- CC BY-NC 3.0 AM
- CC BY-ND 3.0 AM
- CC BY 3.0 AM
- CC BY-NC-ND 3.0 AZ
- CC BY-NC-SA 3.0 AZ
- CC BY-NC 3.0 AZ
- CC BY-ND 3.0 AZ
- CC BY 3.0 AZ
- CC BY-NC-ND 3.0 CA
- CC BY-NC-SA 3.0 CA
- CC BY-NC 3.0 CA
- CC BY-ND 3.0 CA
- CC BY 3.0 CA
- CC BY-NC-ND 3.0 GE
- CC BY-NC-SA 3.0 GE
- CC BY-NC 3.0 GE
- CC BY-ND 3.0 GE
- CC BY 3.0 GE

Removed legacy ccEngine RDF/XML for nonexistent license:
- ~~CC BY-ND-NC 2.0 JP~~

Added additional [DCMI: DCMI Metadata Terms][dcmiterms] to RDF/XML:
- `dcterms:LicenseDocument` (duplicates `cc:legalcode`)
- `dcterms:Jurisdiction` with `rdf:datatype="http://purl.org/dc/terms/ISO3166"`
  (duplicates `cc:jurisdiction` except for `igo` which uses `un`)

Improved multilingual support:
- Title translations now match legal code
- Added `xml:lang` to `cc:legalcode`
- Removed top level `rdf:Description` that were redundant with `cc:legalcode`
  and `dcterms:LicenseDocument`

Remove third-party license RDF/XML (the deeds and legal code were replaced by
redirects long ago):
- `/licenses/BSD/rdf`
- `/licenses/GPL/2.0/rdf`
- `/licenses/LGPL/2.1/rdf`
- `/licenses/MIT/rdf`
- `/licenses/by-nd-nc/2.0/jp/rdf`

Remove unused RDF/XML files:
- `/rdf/jurisdictions.rdf`
- `/rdf/selectors.rdf`


## History

*(describe history of ccREL and legacy implementation/resources)*
