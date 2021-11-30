
import argparse

from lxml import etree
from visualization_tools import get_surf_from_xml_node


def main():
    parser = argparse.ArgumentParser('')
    parser.add_argument('XML')
    args = parser.parse_args()

    xml_parser = etree.XMLParser(remove_blank_text=True)
    root = etree.parse(args.XML, xml_parser)

    doc = root.xpath('./document')[0]

    surfs = []
    for sentence in doc.xpath('./sentences/sentence'):
        surf = get_surf_from_xml_node(sentence)
        surfs.append(surf)

    for surf in surfs:
        print(surf)


if __name__ == '__main__':
    main()
