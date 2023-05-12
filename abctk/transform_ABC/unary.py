import logging

from abctk.obj.ABCCat import Annot
logger = logging.getLogger(__name__)
from typing import Union, TypeVar

from nltk.tree import Tree
from abctk.obj.ID import RecordID

X = TypeVar("X")
def collapse_unary_nodes(
    tree: X,
    ID: Union[RecordID, str] = "<UNKNOWN>",
) -> X:
    if isinstance(tree, Tree):
        if len(tree) == 1:
            only_child = collapse_unary_nodes(tree[0], ID)

            if isinstance(only_child, Tree):
                node_collapsed = f"{tree.label()}☆{only_child.label()}"

                return tree.__class__(
                    node = node_collapsed,
                    children = [collapse_unary_nodes(child, ID) for child in only_child]
                )
            else:
                return tree.__class__(
                    node = tree.label(),
                    children = [only_child]
                )
        else:
            return tree.__class__(
                node = tree.label(),
                children = [collapse_unary_nodes(child, ID) for child in tree]
            )
    else:
        return tree
    
def restore_unary_nodes(
    tree,
    ID: Union[RecordID, str] = "<UNKNOWN>",
) -> Tree:
    if isinstance(tree, Tree):
        label: Union[str, Annot[str]] = tree.label()

        if isinstance(label, Annot):
            cat = label.cat
            if cat.find("☆", 1):
                unary_cats = cat.split("☆")

                if len(unary_cats) > 0:
                    unarized_tree = tree.__class__(
                        node = Annot(
                            cat = unary_cats.pop(),
                            feats = label.feats,
                            pprinter_cat = label.pprinter_cat,
                        ),
                        children = [
                            restore_unary_nodes(child, ID) 
                            for child in tree
                        ]
                    )

                    while unary_cats:
                        unarized_tree = tree.__class__(
                            node = Annot(
                                cat = unary_cats.pop(),
                                feats = label.feats,
                                pprinter_cat = label.pprinter_cat,
                            ),
                            children = [unarized_tree]
                        )

                    return unarized_tree
                else:
                    return tree.__class__(
                        node = label,
                        children = [restore_unary_nodes(child, ID) for child in tree],
                    )
            else:
                return tree.__class__(
                    node = label,
                    children = [restore_unary_nodes(child, ID) for child in tree]
                )
        else:
            if label.find("☆", 1):
                unary_nodes = label.split("☆")

                if len(unary_nodes) > 0:
                    unarized_tree = tree.__class__(
                        node = unary_nodes.pop(),
                        children = [restore_unary_nodes(child, ID) for child in tree]
                    )

                    while unary_nodes:
                        unarized_tree = tree.__class__(
                            node = unary_nodes.pop(),
                            children = [unarized_tree]
                        )

                    return unarized_tree
                else:
                    return tree.__class__(
                        node = label,
                        children = [restore_unary_nodes(child, ID) for child in tree],
                    )
            else:
                return tree.__class__(
                    node = label,
                    children = [restore_unary_nodes(child, ID) for child in tree]
                )
    else:
        return tree