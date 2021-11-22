import logging
logger = logging.getLogger(__name__)

from nltk.tree import Tree
import abctk.types.ABCCat as abcc
from abctk.types.ABCCat import ABCCat, ABCCatReady, Annot

def elim_trace(
    tree: Tree,
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

    return False

def restore_rel_trace(
    tree,
    ID: str = "<UNKNOWN>",
) -> None:
    """
    Restore relative clause traces.

    Notes
    -----
    The following derivation is counted as relativization:
    `<N/N>#deriv=unary-IPREL <! <PP\\S>`
    
    Parameters
    -------
    tree: Tree
        An ABC Tree.
        The category-feature bundle must be parsed as `abctk.types.ABCCat.Annot` beforehand.
        Categories are not required to be parsed for better performance.
    ID
    """

    if isinstance(tree, Tree):
        label: Annot[ABCCatReady] = tree.label()
        feats = label.feats

        tree_rec_pointer = tree

        if (
            label.cat == "<N/N>"
            # ABCCat.p(label.cat) == ABCCat.p("<N/N>")
            and feats.get("deriv", "none") == "unary-IPREL"
        ):
            # Derivation of relativzation is found!
            # 1. check the number of the children
            if len(tree) != 1:
                logger.warning(
                    f"An illegal relativizing node is found. Problem: not unary. Tree ID: {ID}"
                )

                # abort the conversion
            else:
                # unary
                only_child = tree[0]

                if not isinstance(only_child, Tree):
                    logger.warning(
                        f"An illegal relativizing node is found. Problem: illegal subtree type. Tree ID: {ID}"
                    )

                    # abort the conversion
                    tree_rec_pointer = None
                else:
                    child_label: Annot[ABCCatReady] = only_child.label()
                    # take the trace argument type
                    child_cat = ABCCat.p(child_label.cat)

                    # check the only child has the category (Xbase → Y)
                    if not (
                        isinstance(child_cat, abcc.ABCCatFunctor)
                        and isinstance(child_cat.ant, abcc.ABCCatBase)
                    ):
                        logger.warning(
                            f"An illegal relativizing node is found. Problem: illegal subtree category ({child_cat.pprint()}). Tree ID: {ID}"
                        )
                    else:
                        arg_cat_str = child_cat.ant.pprint()

                        # rewrite the derivation
                        tree.clear()
                        tree.append(
                            Tree(
                                Annot(f"<Srel|{arg_cat_str}>"),
                                # ABCCat.v(ABCCat.p("Srel"), arg_cat),
                                [
                                    Tree(
                                        Annot("Srel"),
                                        [
                                            Tree(
                                                Annot(arg_cat_str),
                                                ["*T*"],
                                            ),
                                            only_child,
                                        ]
                                    )
                                ]
                            )
                        )
                    tree_rec_pointer = only_child

        # propagate to children
        if tree_rec_pointer:
            for child in tree_rec_pointer:
                restore_rel_trace(child, ID)
    else:
        # not a tree
        # do nothing
        pass