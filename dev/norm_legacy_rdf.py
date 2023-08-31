#!/usr/bin/env python3
"""
Temporary utility (expect to only have value in 2023Q3) to normalize legacy
RDF/XML (update namespaces, prefixes, domains, and sort output) so that it can
better be compared with new RDF/XML generation.
"""

# Standard library
import argparse
import glob
import sys
import traceback

# Third-party
from lxml import etree


class ScriptError(Exception):
    def __init__(self, message, code=None):
        self.code = code if code else 1
        message = f"({self.code}) {message}"
        super(ScriptError, self).__init__(message)


def setup():
    """Instantiate and configure argparse and logging.

    Return argsparse namespace.
    """
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawTextHelpFormatter
    )
    default_paths = [
        "../cc-legal-tools-data/docs/licenses/**/rdf",
        "../cc-legal-tools-data/docs/publicdomain/**/rdf",
        "../cc-legal-tools-data/docs/rdf/*.rdf",
    ]
    default_paths_string = "\n    ".join(default_paths)
    default_paths_string = f"    {default_paths_string}"
    ap.add_argument(
        "paths",
        nargs="*",
        default=default_paths,
        help="path(s) to RDF/XML file(s)\n  default paths:\n"
        f"{default_paths_string}",
        metavar="RDF_XML_FILE",
    )
    args = ap.parse_args()
    return args


def normalize_rdf_xml(serialized_rdf_content):
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

    # Step 1: manually modernize RDF/XML
    #   - combine dc and dcq namespaces/prefixes into dcterms
    #   - update license buttons domain
    if "xmlns:dcq" in serialized_rdf_content:
        replacement_pairs = [
            # update to use dcterms namespace instead of dcq (singe quotes)
            [
                "xmlns:dcq='http://purl.org/dc/terms/'",
                'xmlns:dcterms="http://purl.org/dc/terms/"',
            ],
            # update to use dcterms namespace instead of dcq (double quotes)
            [
                'xmlns:dcq="http://purl.org/dc/terms/"',
                'xmlns:dcterms="http://purl.org/dc/terms/"',
            ],
            # remove dc namespace (singe quotes)
            ["xmlns:dc='http://purl.org/dc/elements/1.1/'", ""],
            # remove dc namespace (double quotes)
            ['xmlns:dc="http://purl.org/dc/elements/1.1/"', ""],
        ]
    else:
        replacement_pairs = [
            # update to use dcterms namespace instead of dc (singe quotes)
            [
                "xmlns:dc='http://purl.org/dc/elements/1.1/'",
                'xmlns:dcterms="http://purl.org/dc/terms/"',
            ],
            # update to use dcterms namespace instead of dc (double quotes)
            [
                'xmlns:dc="http://purl.org/dc/elements/1.1/"',
                'xmlns:dcterms="http://purl.org/dc/terms/"',
            ],
        ]
    replacement_pairs += [
        # update to use newer licensebuttons.net domain
        ["i.creativecommons.org", "licensebuttons.net"],
        # update to use dcterms prefix instead of dc
        ["dc:", "dcterms:"],
        # update to use dcterms prefix instead of dcq
        ["dcq:", "dcterms:"],
    ]
    for old_value, new_value in replacement_pairs:
        serialized_rdf_content = serialized_rdf_content.replace(
            old_value, new_value
        )

    # Step 2: lxml
    #   - order XML elements by tag and attribute (using prefixes so they are
    #     sorted appropriately when serialized)
    #   - lxml, however, does not support deterministic output of the namespace
    parser = etree.XMLParser(remove_blank_text=True)
    root = etree.fromstring(serialized_rdf_content.encode(), parser)
    sort_children(root)
    serialized_rdf_content = etree.tostring(
        root, encoding="utf-8", xml_declaration=True, pretty_print=True
    )

    # Step 3: manually sort namespaces in line 2 of serialized RDF/XML content
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


def main():
    args = setup()
    rdf_paths = []
    for path in args.paths:
        rdf_paths += glob.glob(path, recursive=True)
    rdf_paths.sort()
    for path in rdf_paths:
        rdf = ""
        with open(path, "rt") as file_obj:
            rdf = file_obj.read()
        rdf = normalize_rdf_xml(rdf)
        with open(path, "wt") as file_obj:
            file_obj.write(rdf)


if __name__ == "__main__":
    try:
        main()
    except SystemExit as e:
        sys.exit(e.code)
    except KeyboardInterrupt:
        print("INFO (130) Halted via KeyboardInterrupt.", file=sys.stderr)
        sys.exit(130)
    except ScriptError:
        error_type, error_value, error_traceback = sys.exc_info()
        print(f"CRITICAL {error_value}", file=sys.stderr)
        sys.exit(error_value.code)
    except Exception:
        print("ERROR (1) Unhandled exception:", file=sys.stderr)
        print(traceback.print_exc(), file=sys.stderr)
        sys.exit(1)
