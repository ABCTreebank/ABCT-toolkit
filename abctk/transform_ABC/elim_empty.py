import typing

from nltk.tree import Tree
import abctk.obj.ABCCat as abcc
from abctk.obj.ABCCat import ABCCatBot, Annot, ABCCat

def elim_empty_terminals(
    tree,
    ID: str = "<UNKNOWN>",
) -> bool:
    """
    Minimize the labels of a tree.

    Notes
    -----
    The given tree is tampered.
    Make a copy beforehand to avoid any data loss.

    Returns
    -------
    is_empty: bool
        For internal recursion only.
    """

    if isinstance(tree, Tree):
        children_cats = tuple(
            elim_empty_terminals(child, ID)
            for child in tree
        )
        # NOTE: subtrees tampered

        children_num = len(children_cats)
        if children_num == 1:
            return children_cats[0] # propagate the result of the only child
        elif any(children_cats):
            children = list(tree)

            tree.clear()
            tree.extend(
                child for child, is_empty in zip(children, children_cats)
                if not is_empty
            )
            
            if children_num == 2:
                self_label: Annot = tree.label()
                self_label.feats["deriv"] = "unary-elim-empty"
            # === END IF ===

            return False 
        else:
            # do nothing
            return False
    elif isinstance(tree, str):
        return tree.startswith("*") or tree.startswith("__")
    else:
        # do nothing
        return False