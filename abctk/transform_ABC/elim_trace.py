import logging
from typing import Union

logger = logging.getLogger(__name__)

from nltk.tree import Tree

from abctk import ABCTException
from abctk.obj.ID import RecordID
import abctk.obj.ABCCat as abcc
from abctk.obj.ABCCat import ABCCat, ABCCatFunctor, ABCCatReady, Annot

class ElimTraceException(ABCTException):
    ID: str
    subtree: Tree

    def __init__(self, ID: str, subtree: Tree, reason: str = "unknown") -> None:
        self.ID = ID
        self.subtree = subtree

        super().__init__(
            "An illegal relativizing node is found. "
            f"Problem: {reason}."
            f"Tree ID: {ID}"
        )

class IllegalRelativizationSubtreeException(ElimTraceException):
    def __init__(self, ID: str, subtree: Tree, wrong_cat: abcc.ABCCatReady):
        if isinstance(wrong_cat, ABCCat):
            wrong_cat_str = wrong_cat.pprint()
        else:
            wrong_cat_str = str(wrong_cat)

        super().__init__(
            ID, subtree,
            f"illegal subtree category ({wrong_cat_str})"
        )

class UnexpectedLexicalNodeException(ElimTraceException):
    def __init__(self, ID: str, subtree: Tree, word: str):
        super().__init__(
            ID, subtree,
            f'unexpected lexical node "{word}"'
        )
class NonUnaryRelativizationSubtreeException(ElimTraceException):
    def __init__(self, ID: str, subtree: Tree):
        super().__init__(
            ID, subtree,
            f"not unary"
        )

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
    ID: Union[RecordID, str] = "<UNKNOWN>",
    generous: bool = False
) -> None:
    """
    Restore relative clause traces.

    Notes
    -----
    The following derivation is counted as relativization:
    `<N/N>#deriv=unary-IPREL <! <PP\\S>`
    
    Parameters
    -------
    tree
        An ABC Tree.
        The category-feature bundle must be parsed as `abctk.obj.ABCCat.Annot` beforehand.
        Categories are not required to be parsed for better performance.
    ID

    generous
        sdf
    """
    if isinstance(tree, Tree):
        label: Annot[ABCCatReady] = tree.label()
        feats = label.feats

        if (
            ABCCat.parse(label.cat) == ABCCat.p("<N/N>")
            and (
                 generous
                 or feats.get("deriv", "none") == "unary-IPREL"
            )
        ):
            # Derivation of relativzation is found!
            # 1. check the number of the children
            if len(tree) != 1:
                if generous:
                    logger.info(
                        "A subtree labeled <N/N> is deemed not to be an relativization structure. "
                        f"Reason: non-unary. Tree ID: {ID}"
                    )

                    # doing nothing on this node
                else:
                    raise NonUnaryRelativizationSubtreeException(ID, tree)
            else:
                # unary
                only_child = tree[0]

                # and ABCCat.parse(child.label().cat).equiv_to(
                #     "<PP\\S>",
                #     ignore_feature = True,
                # )
                if isinstance(only_child, str):
                    if generous:
                        logger.info(
                            "A subtree labeled <N/N> is deemed not to be an relativization structure. "
                            f'Reason: unexpected lexical node "{only_child}". '
                            f"Tree ID: {ID}"
                        )
                    else:
                        raise UnexpectedLexicalNodeException(
                            str(ID), tree, only_child
                    )
                elif not isinstance(only_child, Tree):
                    raise IllegalRelativizationSubtreeException(
                        str(ID), tree,
                        None,
                    )
                else:
                    child_label: Annot[ABCCatReady] = only_child.label()
                    # take the trace argument type
                    child_cat = ABCCat.p(child_label.cat)

                    # check the only child has the category (Xbase → Y)
                    if (
                        isinstance(child_cat, ABCCatFunctor)
                        and child_cat.equiv_to(
                            "<PP\\S>",
                            ignore_feature = True,
                        )
                    ):
                        logging.info(
                            f"Found a relativization structure in {ID}"
                        )
                        child_cat_ant = child_cat.ant

                        # rewrite the derivation
                        tree.clear()
                        tree.append(
                            Tree(
                                Annot(
                                    ABCCat.p("Srel").v(child_cat_ant),
                                    {"rel": "bind"},
                                    pprinter_cat = ABCCat.pprint,
                                ),
                                [
                                    Tree(
                                        Annot(
                                            ABCCat.p("Srel"),
                                            pprinter_cat = ABCCat.pprint,
                                        ),
                                        [
                                            Tree(
                                                Annot(
                                                    child_cat_ant,
                                                    pprinter_cat = ABCCat.pprint,
                                                ),
                                                ["*T*"],
                                            ),
                                            only_child,
                                        ]
                                    )
                                ]
                            )
                        )
                    else: 
                        if generous:
                            logger.info(
                                "A subtree labeled <N/N> is deemed not to be an relativization structure. "
                                f'Reason: category {child_cat.pprint()} not matching. '
                                f"Tree ID: {ID}"
                            )
                        else:
                            raise IllegalRelativizationSubtreeException(
                                str(ID), tree,
                                child_cat,
                            )

        # propagate to children
        for child in tree:
            restore_rel_trace(child, ID, generous)
    else:
        # not a tree
        # do nothing
        pass