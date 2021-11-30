
import re
import nltk
from nltk.sem.logic import Variable
from nltk.sem.drt import DRS
from nltk.sem.drt import DrtApplicationExpression
from nltk.sem.drt import DrtEqualityExpression
from nltk.sem.drt import DrtNegatedExpression
from nltk.sem.drt import DrtOrExpression
from nltk.sem.drt import DrtLambdaExpression
from nltk.sem.drt import DrtConstantExpression
from nltk.sem.drt import DrtIndividualVariableExpression

dp = nltk.sem.DrtExpression.fromstring

constant_symbols = ['cause', 'wh', 'mod', 'excl', 'content', 'part']


def convert_constant(expr):
    expr = re.sub('(arg)_([a-z0-9]+)', r'\\ConSym{\1}\\_\\ConSym{\2}', expr)
    expr = re.sub('\\*([a-zA-Z]+)\\*', r'*\\ConSym{\1}*', expr)
    for symbol in constant_symbols:
        br = r'\\ConSym{' + symbol + '}'
        expr = re.sub(symbol, br, expr)
    return expr


def nltk2latex(expr):
    expr = expr.replace('\\', r'\lambda ') \
               .replace('exists ', r'\exists ') \
               .replace('all ', r'\forall ') \
               .replace(' & ', r' \wedge ') \
               .replace(' | ', r' \vee ') \
               .replace('->', r' \to ') \
               .replace('-', r'\neg ')
    expr = re.sub(u'([ぁ-んァ-ン一-龥]+)', r'\\LF{\1}', expr)
    expr = convert_constant(expr)
    expr = re.sub('([xyzdeFX])([0-9]+)', r'\1_{\2}', expr)
    return expr


def drs2latex(drs):
    if isinstance(drs, DRS):
        refs = drs.refs
        conds = drs.conds
        refs_str = [drs2latex(ref) for ref in refs]
        conds_str = [drs2latex(cond) for cond in conds]
        if drs.consequent:
            consequent = drs.consequent
            antecedent = DRS(refs, conds)
            ant = drs2latex(antecedent)
            cns = drs2latex(consequent)
            return ant + ' $\\Rightarrow$ ' + cns
        else:
            res_refs = r'\drs{$' + ','.join(refs_str) + '$}'
            res_conds = '{' + ' \\\\ '.join(conds_str) + '}'
            return res_refs + res_conds
    elif isinstance(drs, DrtApplicationExpression):
        predicate = drs.uncurry()[0]
        args = drs.uncurry()[1]
        args_str = [drs2latex(arg) for arg in args]
        pred_str = drs2latex(predicate)
        res = '$' + pred_str + '(' + ','.join(args_str) + ')$'
        return res
    elif isinstance(drs, DrtNegatedExpression):
        neg_str = r'$\neg$\,'
        term = drs.term
        return neg_str + drs2latex(term)
    elif isinstance(drs, DrtOrExpression):
        res1 = drs2latex(drs.first)
        res2 = drs2latex(drs.second)
        return res1 + r'$\vee$' + res2
    elif isinstance(drs, DrtLambdaExpression):
        var_str = drs2latex(drs.variable)
        term_str = drs2latex(drs.term)
        return r'\lambda' + ' ' + var_str + '.' + term_str
    elif isinstance(drs, DrtEqualityExpression):
        res1 = drs2latex(drs.first)
        res2 = drs2latex(drs.second)
        return '$' + res1 + ' = ' + res2 + '$'
    elif isinstance(drs, DrtConstantExpression):
        drs_str = str(drs)
        res = convert_constant(drs_str)
        if not res.startswith('\\ConSym'):
            res = r'\LF{' + drs_str + '}'
        return res
    elif isinstance(drs, DrtIndividualVariableExpression) \
         or isinstance(drs, Variable):
        var = str(drs)
        if len(var) > 1:
            var_str = var[0]
            idx = var[1:]
            res = var_str + '_{' + idx + '}'
        else:
            res = var
        return res
    else:
        return str(drs)
