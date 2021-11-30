#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function

import argparse
import codecs
import logging
import lxml.etree as etree
import sys, os

# from pudb import set_trace; set_trace()

from ccg2lambda_tools import build_ccg_tree, assign_semantics
# from ccg2lambda_tools import BuildCCGTree, AssignSemantics
from semantic_index import SemanticIndex
from visualization_tools import convert_doc_to_mathml
# from visualization_tools import ConvertTreesToMathML

def main(args = None):
  import textwrap
  USAGE=textwrap.dedent("""\
      Usage:
          python ccg2mathml.py <ccg_trees.xml> <categories_template.txt> <nbest>

          ccg_trees.xml should contain sentences parsed by transccg.
    """)
  parser = argparse.ArgumentParser()
  parser.add_argument("ccg_trees_filename")
  parser.add_argument("templates_filename", nargs='?', type=str, default="")
  parser.add_argument("--arbi-types", action="store_true", default=False)
  parser.add_argument("--nbest", nargs='?', type=int, default="1")
  args = parser.parse_args()

  if not os.path.exists(args.ccg_trees_filename):
    print('File does not exist: {0}'.format(args.ccg_trees_filename))
    print(USAGE)
    sys.exit(1)
  if not args.templates_filename or not os.path.exists(args.templates_filename):
    semantic_index = None
  else:
    semantic_index = SemanticIndex(args.templates_filename)

  logging.basicConfig(level=logging.WARNING)

  parsed_sentences = etree.parse(args.ccg_trees_filename).findall('.//sentence')
  # print(etree.tostring(sentences[0], encoding = 'utf-8', pretty_print = True).decode('utf-8'))

  # Create sentence IDs of the form:
  # Hypothesis 0, tree 0: surf1 surf2 ... surfN.
  # Hypothesis 0, tree 1: surf1 surf2 ... surfN.
  # ...
  # Conclusion, tree 0: ...
  # Conclusion, tree 1: ...
  sentence_ids = []
  num_hypotheses = len(parsed_sentences) - 1

  # TODO: limit N-best by the maximum between parameter and n-best trees available.
  ccg_tree_list = []
  ccg_tokens_list = []
  for sent_id, parsed_sentence in enumerate(parsed_sentences):
    ccg_tokens = parsed_sentence.find("tokens")
    ccg_trees = parsed_sentence.findall('.//ccg')
    for tree_id, ccg_tree_xml in enumerate(ccg_trees):
      if tree_id >= args.nbest:
        break
      try:
        ccg_tree = build_ccg_tree(ccg_tree_xml)
      except Exception as e:
        print('Failed to build tree at sentence ID {0}, tree {1}. Message {2}'.format(
          sent_id, tree_id, e), file=sys.stderr)
        continue
      if semantic_index:
        assign_semantics(ccg_tree, semantic_index, ccg_tokens)
      ccg_tree_list.append(ccg_tree)
      ccg_tokens_list.append(ccg_tokens)
      # Make the sentence id to visualize in HTML.
      if sent_id >= num_hypotheses:
        sentence_id = 'Conclusion, '
      else:
        sentence_id = 'Premise ' + str(sent_id) + ', '
      sentence_id += 'tree ' + str(tree_id) + ': '
      sentence_ids.append(sentence_id)
  html_str = convert_doc_to_mathml(
    ccg_tree_list, ccg_tokens_list)
  # html_str = convert_doc_to_mathml(
  #   ccg_tree_list, ccg_tokens_list, sentence_ids=sentence_ids)
  print(html_str, file=sys.stdout)

  # ccg_tree_list = []
  # ccg_tokens_list = []
  # for sentence in sentences:
  #   ccg_tree = build_ccg_tree(sentence.find("ccg"))  # TODO: support n-best output from transccg
  #   ccg_tokens = sentence.find("tokens")
  #   if semantic_index:
  #     assign_semantics(ccg_tree, semantic_index, ccg_tokens)
  #   ccg_tree_list.append(ccg_tree)
  #   ccg_tokens_list.append(ccg_tokens)
  # html_str = convert_doc_to_mathml(ccg_tree_list, ccg_tokens_list)
  # print(html_str, file=sys.stdout)
    
if __name__ == '__main__':
  main()
