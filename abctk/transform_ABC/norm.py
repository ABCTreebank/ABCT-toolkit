import typing

import attr

from nltk.tree import Tree
import abctk.types.ABCCat as abcc
from abctk.types.ABCCat import ABCCatBot, Annot, ABCCat

def minimize_tree(
    tree,
    ID: str = "<UNKNOWN>",
    discard_trace: bool = True,
    reduction_check: bool = True,
) -> typing.Optional[ABCCat]:
    """
    Minimize the labels of a tree.

    Arguments
    ---------
    discard_trace: bool, default : True

    Returns
    -------
    category: ABCCat or None
        For internal recursion only.
    """

    if isinstance(tree, Tree):
        self_label: Annot = tree.label()
        self_label_cat = self_label.cat
        self_label_feats = self_label.feats

        children_cats = tuple(
            minimize_tree(child, ID, discard_trace)
            for child in tree
        )
        # NOTE: subtrees tampered

        cat_new: typing.Union[ABCCat, str]
        feat_new: typing.Dict[str, typing.Any]

        if reduction_check:
            if (
                len(children_cats) == 2
                and self_label_feats.get("deriv", "") in ["", "none"] 
            ):
                child1_cat, child2_cat = children_cats
                cat_new = "" if (
                    child1_cat 
                    and child2_cat 
                    and ABCCat.simplify_exh(child1_cat, child2_cat)
                ) else self_label_cat
            else:
                cat_new = self_label_cat
        else:
            cat_new = (
                "" 
                if self_label_feats.get("deriv", "") in ["", "none"]
                else self_label_cat
            )

        feat_new = dict(
            (key, val) for key, val in self_label_feats.items()
            if not (
                (discard_trace and key.startswith("trace."))
                or (
                    discard_trace and 
                    key == "role"
                    #and self_label_feats.get("deriv", "") in ["", "none"] 
                )
            )
        )

        tree.set_label(
            Annot(cat_new, feat_new)
        )
        
        return self_label_cat
    else:
        # do nothing
        return None

def elaborate_tree(
    tree,
    ID: str = "<UNKNOWN>",
) -> typing.Optional[ABCCat]:
    """
    Elaborate the labels of a tree by calculating and verifying compositions.

    Arguments
    ---------

    Returns
    -------
    category: ABCCat or None
        For internal recursion only.
    """

    if isinstance(tree, Tree):
        self_label: Annot = tree.label()
        self_label_cat = self_label.cat
        self_label_feats = self_label.feats

        children_cats = tuple(
            elaborate_tree(child, ID)
            for child in tree
        )
        # NOTE: subtrees tampered

        if len(children_cats) == 2:
            deriv = self_label_feats.get("deriv", "none")
            if deriv == "none":
                child_1, child_2 = children_cats
                if child_1 is None or child_2 is None:
                    pass
                else:
                    cat_applied_res_set = ABCCat.simplify_exh(child_1, child_2)
                    if cat_applied_res_set:
                        # simp successful
                        new_cat, elimtype = next(iter(cat_applied_res_set))
                        if not self_label_cat:
                            # self_label_cat is empty
                            # supplement it with the result
                            self_label_cat = new_cat

                            self_label_feats["trace.elab.res-deriv"] = str(elimtype)
                            tree.set_label(
                                attr.evolve(
                                    self_label,
                                    cat = new_cat,
                                )
                            )
                        elif self_label_cat == new_cat:
                            # successful
                            # do nothing
                            pass
                        else:
                            # not matching
                            self_label_feats["trace.elab.error"] = "cat-discrepancy"
                            self_label_feats["trace.elab.res"] = new_cat.pprint()
                            self_label_feats["trace.elab.res-deriv"] = str(elimtype)
                    else:
                        if not self_label_cat:
                            # self_label_cat is empty
                            # supplement it with ⊥
                            self_label_cat = ABCCatBot.BOT
                            tree.set_label(
                                attr.evolve(
                                    self_label,
                                    cat = ABCCatBot.BOT,
                                )
                            )
                        # === END IF ===

                        self_label_feats["trace.elab.error"] = "failed-simp"
            else:
                # special derivations
                # do nothing
                pass
        else:
            pass
        
        return self_label_cat
    else:
        # do nothing
        return None