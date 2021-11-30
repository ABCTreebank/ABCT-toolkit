#!/usr/bin/python3
# -*- coding: utf-8 -*-

import argparse
from lxml import etree
import os
import sys
import textwrap

from nltk.sem.drt import *
from nltk2drs import convert_to_drs
from nltk2tptp import convert_to_tptp_proof
from logic_parser import lexpr
# from theorem import get_formulas_from_doc

ARGS=None
DOCS=None

def get_formulas_from_doc(doc):
    """
    Returns string representations of logical formulas,
    as stored in the "sem" attribute of the root node
    of semantic trees.
    If a premise has no semantic representation, it is ignored.
    If there are no semantic representation at all, or the conclusion
    has no semantic representation, it returns None to signal an error.
    """
    # TODO: we need to parameterize the way we obtain formulas for N-best parsing.
    formulas = [s.get('sem', None) for s in doc.xpath(
        './sentences/sentence/semantics[1]/span[1]')]
    if len(formulas) < 2 or formulas[-1] == None:
        return None
    formulas = [f for f in formulas if f is not None]
    return formulas

def main(args = None):
    global ARGS
    global DOCS
    DESCRIPTION=textwrap.dedent("""\
            The input file sem should contain the parsed sentences. All CCG trees correspond
            to the premises, except the last one, which is the hypothesis.
      """)

    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=DESCRIPTION)
    parser.add_argument("sem", help="XML input filename with semantics")

    parser.add_argument("--format", nargs='?', type=str, default="drs",
        choices=["fol", "drs", "drsbox", "tptp"],
        help="Output format (default: drs).")
     
    ARGS = parser.parse_args()

    if not os.path.exists(ARGS.sem):
        print('File does not exist: {0}'.format(ARGS.sem), file=sys.stderr)
        parser.print_help(file=sys.stderr)
        sys.exit(1)
    
    parser = etree.XMLParser(remove_blank_text=True)
    root = etree.parse(ARGS.sem, parser)

    DOCS = root.findall('.//document')
    doc = DOCS[0]

    formulas = get_formulas_from_doc(doc)
    if ARGS.format == "drs" or ARGS.format == "drsbox":
        results = [convert_to_drs(lexpr(formula)) for formula in formulas]
    if ARGS.format == "fol":
        results = [convert_to_drs(lexpr(formula)).fol() for formula in formulas]
    if ARGS.format == "tptp":
        inference = [lexpr(f) for f in formulas]
        results = convert_to_tptp_proof(inference)

    for formula in results:
        formula_str = str(formula)
        if ARGS.format == "drsbox":
            formula.pretty_print()
        print(formula_str)

if __name__ == '__main__':
    main()
