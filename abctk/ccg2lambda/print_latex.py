
import argparse
import re
import glob
import os.path

import nltk
from nltk.sem.logic import Expression
from nltk.sem.logic import LogicalExpressionException

from lxml import etree

from .nltk2normal import remove_true
from .nltk2normal import rename
from .nltk2drs import convert_to_drs
from .latextool import drs2latex
from .latextool import nltk2latex

dp = nltk.sem.DrtExpression.fromstring
lexpr = Expression.fromstring
silent = ['pos', 'dgr']


def decorate(word):
    word = word.replace('_', '-')
    if word in silent:
        word = '(' + word + ')'
    return word


def get_sentences_from_xml(doc):
    sentences = doc.xpath('./sentences/sentence')
    res = []
    for sen in sentences:
        words = [s.get('surf', None) for s in sen.xpath('./tokens[1]/token')]
        words = [decorate(w) for w in words]
        if words[-1] == ".":
            txt = ' '.join(words[:-1]) + '.'
        else:
            txt = ' '.join(words)
        res.append(txt)
    return res


def get_formulas_from_xml(doc):
    sentences = doc.xpath('./sentences/sentence')
    res = []
    for sen in sentences:
        sems = [s.get('sem', None) for s in sen.xpath('./semantics[1]/span[1]')]
        if sems:
            expr = sems[0]
        else:
            expr = "error"
        sem = normalize(expr)
        res.append(sem)
    return res


def normalize(expr):
    try:
        formula = lexpr(expr)
    except LogicalExpressionException:
        formula = "error"
    formula = remove_true(formula)
    res = rename(formula)
    return res


def numericalSort(value):
    numbers = re.compile(r'(\d+)')
    parts = numbers.split(value)
    parts[1::2] = map(int, parts[1::2])
    return parts


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("dir")

    ARGS = parser.parse_args()
    dir = ARGS.dir

    latex_src = ("\\documentclass{jsarticle}\n"
                 "\\usepackage{drs}\n"
                 "\\newcommand{\\LF}[1]{\\ensuremath{\\mathbf{#1}}}\n"
                 "\\newcommand{\\ConSym}[1]{\\mathsf{#1}}\n"
                 "\\begin{document}")

    for file in sorted(glob.glob(dir + "/cache/*[0-9].sem.xml"), key=numericalSort):
        bname = os.path.basename(file)
        bname = bname.replace('.sem.xml', '')\
                     .replace('_', ' ')
        with open(file) as f:
            parser = etree.XMLParser(remove_blank_text=True)
            root = etree.parse(f, parser)

            DOCS = root.findall('.//document')
            doc = DOCS[0]

            latex_src += '\n\n\\noindent\n' + '\\fbox{' + bname + '}'
            text = get_sentences_from_xml(doc)[0]
            formula = get_formulas_from_xml(doc)[0]
            latex_src += '\n\\begin{itemize}'
            formula_str = str(formula)
            # TODO: remove dp here
            drs = str(convert_to_drs(formula))
            drs_str = drs2latex(dp(drs))

            latex = '$' + nltk2latex(formula_str) + '$'
            out = '\n\\item[S:] ' + text + '\\\\\n' + latex + '\\\\\n' + drs_str + '\n'
            latex_src += out
            latex_src += '\n\\end{itemize}'

    print(latex_src + r'\end{document}')


if __name__ == '__main__':
    main()
