import typing

import attr

from nltk.tree import Tree
import abctk.obj.ABCCat as abcc
from abctk.obj.ABCCat import ABCCatBot, Annot, ABCCat, ABCCatBase

def minimize_tree(
    tree: typing.Union[str, Tree],
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

    Notes
    -----
    This method is destructive in the sense that the given `tree` is modified in situ.
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

def elaborate_cat_annotations(
    tree,
    ID: str = "<UNKNOWN>",
) -> typing.Optional[ABCCat]:
    """
    Elaborate the labels of a tree by calculating and verifying compositions.
    Note: `tree` is modified in situ.

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

        if (
            isinstance(self_label_cat, ABCCatBase) and self_label_cat.name == "COMMENT"
            or self_label_cat == "COMMENT"
        ):
            return None

        # RECURSION
        children_cats = tuple(
            filter(
                None,
                (elaborate_cat_annotations(child, ID) for child in tree)
            )
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
                    # self_label has a cat & the only_child also has a cat
                    self_label_cat_parsed = abcc.ABCCat.p(self_label_cat)

                    if (
                        isinstance(self_label_cat_parsed, abcc.ABCCatFunctor)
                        and self_label_cat_parsed.func_mode == abcc.ABCCatFunctorMode.VERT
                        and abcc.ABCCat.parse(only_child) == self_label_cat_parsed.conseq
                    ):
                        # found a |-intro situation
        
                        # Try finding indices
                        index = "unary-unknown"
                        comp_list = self_label_feats.get("comp", "").split(",")
                        if comp_list and "bind" in comp_list:
                            index = f"{comp_list[1]}{comp_list[0]}"

                        self_label_feats["deriv"] = f"|intro-{index}"
                    else:
                        # found an ordinary unary branching
                        self_label_feats["deriv"] = "unary-unknown"
                else:
                    pass
            else:
                pass
        
        return self_label_cat
    else:
        # do nothing
        return None
    

def elaborate_char_spans(
    tree: typing.Union[str, Tree],
    ID: str = "<UNKNOWN>",
    offset: int = 0,
) -> typing.Tuple[int, int]:
    """
    Elaborate the labels of a tree with character span information.

    Arguments
    ---------
    tree: str or Tree
    ID: str
    start: int
        The char offset for `tree`. For internal use only.

    Returns
    -------
    span
        For internal recursion only.

    Notes
    -----
    This method is destructive in the sense that the given `tree` is modified in situ.
    """

    if isinstance(tree, Tree):
        self_label: Annot[ABCCat] = tree.label()
        
        self_cat = self_label.cat
        if (
            isinstance(self_cat, ABCCatBase) and self_cat.name == "COMMENT"
            or self_cat == "COMMENT"
        ):
            return (offset, offset)
        else:
            span_start = offset
            span_end = offset

            for child in tree:
                # RECURSION and collect the end
                _, span_end = elaborate_char_spans(child, ID, offset)
                # move the offset
                offset = span_end

            self_label.feats["char-start"] = span_start
            self_label.feats["char-end"] = span_end
            return (span_start, span_end)
    elif isinstance(tree, str):
        l = (
            0 
            if tree.startswith("*") or tree.startswith("__") 
            else len(tree) 
        )
        return (offset, offset + l)
    else:
        return (offset, offset)

def delete_all_feats_with_white_list(
    tree: typing.Union[str, Tree],
    ID: str = "<UNKNOWN>",
    white_list: typing.Set[str] = set(),
) -> None:
    """
    Delete all meta-features in a given tree except for those specified in `white_list`.

    Notes
    -----
    This method is destructive in the sense that the given `tree` is modified in situ.
    """
    if isinstance(tree, Tree):
        self_label = tree.label()
        if isinstance(self_label, Annot):
            tree.set_label(
                Annot(
                    cat = self_label.cat,
                    feats = {
                        k:v for k, v in self_label.feats.items()
                        if k in white_list
                    }
                )
            )
        for child in tree:
            delete_all_feats_with_white_list(child, ID, white_list)

def delete_feats(
    tree: typing.Union[str, Tree],
    ID: str = "<UNKNOWN>",
    black_list: typing.Set[str] = set(),
) -> None:
    """
    Delete given features in a given trees.

    Notes
    -----
    This method is destructive in the sense that the given `tree` is modified in situ.
    """
    if isinstance(tree, Tree):
        self_label = tree.label()
        if isinstance(self_label, Annot):
            tree.set_label(
                Annot(
                    cat = self_label.cat,
                    feats = {
                        k:v for k, v in self_label.feats.items()
                        if k not in black_list
                    }
                )
            )
        for child in tree:
            delete_feats(child, ID, black_list)
