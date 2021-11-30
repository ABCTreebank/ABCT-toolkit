
import argparse

from lxml import etree
from convert_formulas import get_formulas_from_xml


def main():
    parser = argparse.ArgumentParser('')
    parser.add_argument('SEMXML')
    args = parser.parse_args()

    xml_parser = etree.XMLParser(remove_blank_text=True)
    root = etree.parse(args.SEMXML, xml_parser)
    doc = root.xpath('./document')[0]

    res_str = get_formulas_from_xml(doc)[0]

    print(res_str)


if __name__ == '__main__':
    main()
