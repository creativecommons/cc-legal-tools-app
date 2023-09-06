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


### 2023-09-07 CC Legal Tools machine layer added

Fixed wrong `cc:deprecatedOn` on the following legal tools:
- CC Sampling+ 1.0 BR
- CC Sampling+ 1.0 DE
- CC Sampling+ 1.0 TW
- CC Sampling+ 1.0

Updated RDF namespace prefix:
- `dcterms` replaced ~~`dc`~~ and ~~`dcq`~~

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

Improved compatibility:
- Added additional [DCMI: DCMI Metadata Terms][dcmiterms] to RDF/XML:
  - `dcterms:LicenseDocument` (duplicates `cc:legalcode`)
  - `dcterms:Jurisdiction` with
    `rdf:datatype="http://purl.org/dc/terms/ISO3166"` (duplicates
    `cc:jurisdiction` except for `igo` which uses `un` and for `scotland` for
    which this element is omitted)
    - Also see [ISO 3166-1 alpha-2 - Wikipedia][wp3166alpha2]
- Added `owl:sameAs` element with HTTPS URL

Improved multilingual support:
- Title translations now match legal code (removed title translatins languages
  that the legal code has not yet been translated into)
- Added `xml:lang` to `cc:legalcode`
- Removed top level `rdf:Description` elements that were redundant with
  `cc:legalcode` and `dcterms:LicenseDocument` elements

Removed third-party license RDF/XML (the deeds and legal codes were replaced by
redirects long ago):
- `/licenses/BSD/rdf`
- `/licenses/GPL/2.0/rdf`
- `/licenses/LGPL/2.1/rdf`
- `/licenses/MIT/rdf`
- `/licenses/by-nd-nc/2.0/jp/rdf`

Removed unused RDF/XML files:
- `/rdf/jurisdictions.rdf`
- `/rdf/selectors.rdf`

[wp3166alpha2]: https://en.wikipedia.org/wiki/ISO_3166-1_alpha-2


### More information needed

The following entries are non-exhaustive. More work is required.


### 2011-01-06: CC REL by Example published

- [CC REL by Example](https://opensource.creativecommons.org/ccrel-guide/)
- [creativecommons/ccrel-guide][ghccrelguide]: *A guide to using the Creative
  Commons Rights Expression Language (CC REL)*

[ghccrelguide]: https://github.com/creativecommons/ccrel-guide


### 2008-08-20: Received World Wide Web Consortium (W3C) team comment on ccREL

- [Team Comment on ccREL: The Creative Commons Rights Expression Language
  Member Submission][w3comment].

[w3comment]: https://www.w3.org/submissions/2008/02/Comment


### 2008-07-24: cc.license component of the ccEngine entered alpha

- [cc.license in alpha — Creative Commons Open Source][cclicblogalpha]
- [creativecommons/cc.license](https://github.com/creativecommons/cc.license):
  *Python app that runs part of the license engine on CC's website*
  - (the ccEngine was deprecated by this project, the CC Legal Tools)

[cclicblogalpha]: https://opensource.creativecommons.org/archives/old-tech-blog/entries/cclicense-in-alpha/


### 2008-05-01: Submitted ccREL to W3C

- [ccREL: The Creative Commons Rights Expression Language][w3ccrel]

[w3ccrel]: https://www.w3.org/submissions/ccREL/


### 2008-04-08: Published ccREL

- [ccREL: The Creative Commons Rights Expression Language][ccrel]

[ccrel]: https://opensource.creativecommons.org/ccrel/
