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

        children_count = len(children_cats)
        deriv: str = self_label_feats.get("deriv", "none")

        if children_count == 2:
            if abcc.ElimType.is_compatible_repr(deriv):
                child_1, child_2 = children_cats
                if child_1 is None or child_2 is None:
                    pass
                else:
                    cat_applied_res_set = ABCCat.simplify_exh(child_1, child_2)
                    if cat_applied_res_set:
                        # simp successful
                        new_cat, elimtype = next(iter(cat_applied_res_set))
                        if not self_label_cat and deriv == "none":
                            # self_label_cat is empty, no deriv speficied
                            # supplement it with the result
                            self_label_cat = new_cat

                            self_label_feats["deriv"] = str(elimtype)
                            tree.set_label(
                                attr.evolve(
                                    self_label,
                                    cat = new_cat,
                                )
                            )
                        elif abcc.ABCCat.p(self_label_cat) == new_cat:
                            # successful
                            # check deriv
                            if deriv == "none":
                                # no deriv 
                                # fill it
                                self_label_feats["deriv"] = str(elimtype)
                            else:
                                deriv_parsed = abcc.ElimType.maybe_parse(deriv)
                                if deriv_parsed != elimtype:
                                    self_label_feats["trace.elab.wrong-rule"] = str(elimtype)
                        else:
                            # categories are not identical
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
        elif children_count == 1:
            if deriv == "none":
                # check if it is actually a |-intro
                only_child = children_cats[0]
                if only_child is not None and self_label_cat:
                    self_label_cat_parsed = abcc.ABCCat.p(self_label_cat)

                    if (
                        isinstance(self_label_cat_parsed, abcc.ABCCatFunctor)
                        and self_label_cat_parsed.func_mode == abcc.ABCCatFunctorMode.VERT
                        and abcc.ABCCat.parse(only_child) == self_label_cat_parsed.conseq
                    ):
                        # found a |-intro situation
        
                        # Try finding indices
                        index = "unknown"
                        comp_list = self_label_feats.get("comp", "").split(",")
                        if comp_list and "bind" in comp_list:
                            index = f"{comp_list[1]}{comp_list[0]}"

                        self_label_feats["deriv"] = f"|intro-{index}"
                else:
                    pass
            else:
                pass
        
        return self_label_cat
    else:
        # do nothing
        return None