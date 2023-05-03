import typing
from typing import Any

from nltk.tree import Tree 

from abctk.obj.ABCCat import Annot
from abctk.obj.comparative import CompSpan

import numpy as np
from scipy.optimize import linear_sum_assignment

def incorporate_all_comps(
    spans: typing.Sequence[CompSpan],
    tree: typing.Union[Tree, str],
    ID: str = "<UNKNOWN>",
) -> None: 
    """
    Incorporate all given comparative span annotations to a :class:`nltk.Tree`.

    Arguments
    ---------
    spans : list of <CompSpan>
        An iterable of comparative spans. 
        These spans must be diced 
            by the function :func:`abctk.obj.comparative.dice_CompRecord` beforehand.

    tree : Tree or str
        A :class:`nltk.Tree` with its character span annotations already added 
        by the function :func:`abctk.transform_ABC.elaborate_char_spans`.

    ID : str

    Notes
    -----
    This method is destructive in the sense that the given `tree` is modified in situ.
    """
    # collect annotation features on the tree
    node_stack = [tree]
    feats_list: list[dict[str, Any]]= []

    while node_stack:
        current_node = node_stack.pop()

        if isinstance(current_node, Tree):
            label: Annot = current_node.label()
            feats = label.feats
            if "char-start" in feats:
                feats_list.append(feats)

            node_stack.extend(current_node)

    cost_matrix = np.zeros(
        shape = (len(spans), len(feats_list)),
        dtype = np.float_
    )

    for idx_comp, comp_span in enumerate(spans):
        for idx_feats, feats in enumerate(feats_list):
            gap = min(
                comp_span.end - comp_span.start,
                feats["char-end"] - feats["char-start"],
            )
            offset_start = min(gap, abs(comp_span.start - feats["char-start"]))
            offset_end = min(gap, abs(comp_span.end - feats["char-end"]))
            
            # scoring by the logit function
            cost_matrix[idx_comp, idx_feats] = -np.log(
                (2 * gap - offset_start - offset_end) 
                / (2 * gap + offset_start + offset_end)
            )

    # print(ID, cost_matrix)
    # print()
    row_ind, col_ind = linear_sum_assignment(cost_matrix)

    # apply the results to the relevant nodes
    for idx_comp, idx_feats in zip(row_ind, col_ind):
        feats_list[idx_feats]["comp"] = f"1,{spans[idx_comp].label}"