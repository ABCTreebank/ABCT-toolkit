# -*- coding: utf-8 -*-

from nltk.sem.drt import *
from .logic_parser import lexpr
from .nltk2drs import convert_to_drs

# lexpr = Expression.fromstring

kSize = 1.0
kColor = 'Blue'
entityVariableColor = '#ff6347'
eventVariableColor = 'Green'

def basic_exp(expression, color):
    if str(expression)[0] == '_':
         str_expression = str(expression)[1:]
    else:
         str_expression = str(expression)
    return "<mtext" \
           + " fontsize='" + str(kSize) + "'" \
           + " color='" + color + "'>" \
           + str_expression \
           + "</mtext>\n"

def convert_to_drs_mathml(expression):
    if isinstance(expression, str):
        expression = lexpr(expression)
        expression = convert_to_drs(expression)
    expr_drs_str = ''
    if isinstance(expression, DRS):
        referents = expression.refs
        conditions = expression.conds
        refs_str = [convert_to_drs_mathml(ref) for ref in referents]
        dref = '<mspace width=".3em"/>'.join(refs_str)

        if expression.consequent:
            conds_str = [convert_to_drs_mathml(f) for f in conditions]
            dcond = '</mtd></mtr><mtr><mtd>'.join(conds_str)
            dconst = convert_to_drs_mathml(expression.consequent)

            expr_drs_str = "<mfenced open='[' close=']'>\n" \
                           + "  <mtable columnalign='left'>" \
                           + "    <mtr>\n" \
                           + "      <mtd>\n" \
                           + dref \
                           + "      </mtd>\n" \
                           + "    </mtr>\n" \
                           + "    <mtr>\n" \
                           + "      <mtd>\n" \
                           + dcond \
                           + "    <mtr>\n" \
                           + "      <mtd>\n" \
                           + "  </mtable>\n" \
                           + "</mfenced>\n" \
                           + "  <mspace width='.1em'/>" \
                           + "  <mo> &rarr; </mo>\n" \
                           + "  <mspace width='.1em'/>" \
                           + dconst \
                           + "  </mtable>\n" \
                           + "</mfenced>\n"
        else:
            conds_str = [convert_to_drs_mathml(f) for f in conditions]
            dcond = '</mtd></mtr><mtr><mtd>'.join(conds_str)

            expr_drs_str = "<mfenced open='[' close=']'>\n" \
                           + "  <mtable columnalign='left'>" \
                           + "    <mtr>\n" \
                           + "      <mtd>\n" \
                           + dref \
                           + "      </mtd>\n" \
                           + "    </mtr>\n" \
                           + "    <mtr>\n" \
                           + "      <mtd>\n" \
                           + dcond \
                           + "      </mtd>\n" \
                           + "    </mtr>\n" \
                           + "  </mtable>\n" \
                           + "</mfenced>\n"

    elif isinstance(expression, DrtApplicationExpression):
        args = expression.args
        function = convert_to_drs_mathml(expression.pred)
        args_str = [convert_to_drs_mathml(arg) for arg in args]
        args_str = '<mtext>,</mtext><mspace width=".1em"/>'.join(args_str)
        expr_drs_str = function \
                       + "<mtext>(</mtext>" \
                       + args_str \
                       + "<mtext>)</mtext>\n"
    elif isinstance(expression, DrtLambdaExpression):
        binding_variable = str(expression.variable)
        body = convert_to_drs_mathml(expression.term)
        expr_drs_str = "<mtext" \
                       + " fontsize='" + str(kSize) + "'" \
                       + " color='" + kColor + "'>" \
                       + "&lambda;" \
                       + binding_variable \
                       + "." \
                       + "</mtext>" \
                       + "<mspace width='.1em'/>\n" \
                       + body
    elif isinstance(expression, DrtOrExpression):
        left = convert_to_drs_mathml(expression.first)
        right = convert_to_drs_mathml(expression.second)
        expr_drs_str = left \
                       + "<mspace width='.1em'/>" \
                       + "<mo> &or; </mo>\n" \
                       + "<mspace width='.1em'/>" \
                       + right
    elif isinstance(expression, DrtNegatedExpression):
        body = convert_to_drs_mathml(expression.term)
        expr_drs_str = "<mo> &not; </mo>\n" \
                       + body
    elif isinstance(expression, DrtEqualityExpression):
        left = convert_to_drs_mathml(expression.first)
        right = convert_to_drs_mathml(expression.second)
        expr_drs_str = left \
                       + "<mspace width='.1em'/>" \
                       + "<mo> = </mo>\n" \
                       + "<mspace width='.1em'/>" \
                       + right
    elif isinstance(expression, DrtConstantExpression):
        color = kColor
        expr_drs_str = basic_exp(expression, color)
    elif isinstance(expression, DrtAbstractVariableExpression) \
         or isinstance(expression, Variable):
        if str(expression)[0] == 'x':
            color = entityVariableColor
        elif str(expression)[0] == 'e':
            color = eventVariableColor
        else:
            color = kColor
        expr_drs_str = basic_exp(expression, color)
    else:
        color = kColor
        expr_drs_str = basic_exp(expression, color)
    return expr_drs_str
