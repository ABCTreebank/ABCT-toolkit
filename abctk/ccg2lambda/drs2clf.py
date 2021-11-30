
import argparse
from lxml import etree
from nltk.sem.drt import DRS
from nltk.sem.drt import DrtApplicationExpression
from nltk.sem.drt import DrtNegatedExpression
from nltk.sem.drt import DrtOrExpression

from logic_parser import lexpr
from convert_formulas import get_formulas_from_xml
from nltk2drs import convert_to_drs
from nltk2normal import is_wff

# Example of clausal form (clf)
# %%% I have n't touched anything .
# % I [0...1]
# % have [2...6]
# b1 NEGATION b2         % n't [6...9]
# b1 REF t1              % touched [10...17]
# b1 TPR t1 "now"        % touched [10...17]
# b1 time "n.08" t1      % touched [10...17]
# b2 REF e1              % touched [10...17]
# b2 Agent e1 "speaker"  % touched [10...17]
# b2 Experiencer e1 x1   % touched [10...17]
# b2 Time e1 t1          % touched [10...17]
# b2 touch "v.01" e1     % touched [10...17]
# b2 REF x1              % anything [18...26]
# b2 entity "n.01" x1    % anything [18...26]
# % . [26...27]


def convert_to_clausal_forms(drs):
    cls = convert_to_clf(1, [], drs)
    return cls


def is_variable(drs_str):
    prefix = ['x', 'e']
    if len(drs_str) <= 1:
        return False
    elif drs_str[0] in prefix and drs_str[1].isdigit():
        return True
    else:
        return False


def check_constant_and_add_quotes(drs_str):
    if is_variable(drs_str):
        return drs_str
    else:
        return '"' + drs_str + '"'


def convert_to_clf(idx, clfs, drs):
    if isinstance(drs, str):
        clfs.append(drs)
    elif isinstance(drs, DRS):
        refs = drs.refs
        conds = drs.conds
        if drs.consequent:
            consequent = drs.consequent
            boxvar = 'b' + str(idx)
            idx1 = idx + 1
            idx2 = idx + 2
            boxarg1 = 'b' + str(idx1)
            boxarg2 = 'b' + str(idx2)
            res = boxvar + ' IMP ' + boxarg1 + ' ' + boxarg2
            clfs.append(res)
            antecedent = DRS(refs, conds)
            convert_to_clf(idx1, clfs, antecedent)
            convert_to_clf(idx2, clfs, consequent)
        else:
            boxvar = 'b' + str(idx)
            for ref in refs:
                clf = boxvar + ' REF ' + str(ref)
                clfs.append(clf)
            for cond in conds:
                convert_to_clf(idx, clfs, cond)
    elif isinstance(drs, DrtApplicationExpression):
        predicate = drs.uncurry()[0]
        args = drs.uncurry()[1]
        op = str(predicate)
        boxvar = 'b' + str(idx)
        if len(args) == 1:
            arg = args[0]
            if isinstance(arg, DRS):
                next_idx = idx + 1
                boxarg = 'b' + str(next_idx)
                res = boxvar + ' ' + op + ' ' + boxarg
                convert_to_clf(next_idx, clfs, arg)
            else:
                out = check_constant_and_add_quotes(str(arg))
                res = boxvar + ' ' + op + ' ' + out
                # adding dummy synset
                # res = boxvar + ' ' + op + ' "n.01" ' + out
        if len(args) == 2:
            arg1 = args[0]
            arg2 = args[1]
            if isinstance(arg2, DRS):
                out = check_constant_and_add_quotes(str(arg1))
                next_idx = idx + 1
                box_arg = 'b' + str(next_idx)
                res = boxvar + ' ' + op + ' ' + out + ' ' + box_arg
                convert_to_clf(next_idx, clfs, arg2)
            else:
                out1 = check_constant_and_add_quotes(str(arg1))
                out2 = check_constant_and_add_quotes(str(arg2))
                # if op in roles:
                res = 'b' + str(idx) + ' ' + op + ' ' + out1 + ' ' + out2
        clfs.append(res)
    elif isinstance(drs, DrtNegatedExpression):
        boxvar = 'b' + str(idx)
        idx = idx + 1
        drs_var = 'b' + str(idx)
        neg = boxvar + ' NOT ' + drs_var
        clfs.append(neg)
        term = drs.term
        convert_to_clf(idx, clfs, term)
    elif isinstance(drs, DrtOrExpression):
        boxvar = 'b' + str(idx)
        idx1 = idx + 1
        idx2 = idx + 2
        boxarg1 = 'b' + str(idx1)
        boxarg2 = 'b' + str(idx2)
        res = boxvar + ' DIS ' + boxarg1 + ' ' + boxarg2
        clfs.append(res)
        convert_to_clf(idx1, clfs, drs.first)
        convert_to_clf(idx2, clfs, drs.second)
#     elif isinstance(drs, DrtLambdaExpression):
#     elif isinstance(drs, DrtEqualityExpression):
    else:
        return str(drs)
    return clfs


def main():
    parser = argparse.ArgumentParser('')
    parser.add_argument('XML')
    ARGS = parser.parse_args()
    parser = etree.XMLParser(remove_blank_text=True)
    root = etree.parse(ARGS.XML, parser)
    DOCS = root.findall('.//document')
    doc = DOCS[0]

    formulas = get_formulas_from_xml(doc)
    try:
        formula = lexpr(formulas[0])
        if is_wff(formula):
            drs = convert_to_drs(formula)
            lines = convert_to_clausal_forms(drs)
            for line in lines:
                print(line)
    except IndexError:
        print('')


if __name__ == '__main__':
    main()
