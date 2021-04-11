import typing 
import logging
logger = logging.getLogger(__name__)

import functools
import itertools
import pathlib
import os
import re
import sys

import attr

import abctk.config as CONF
import abctk.types as at

def __chaining_conjuncts(
    root: at.ABCCat_ABCCatPlus,
    children_rev: typing.Iterator[
        typing.Callable[
            [at.ABCCat],
            at.ABCTree_ABCCatPlus,
        ],
    ]
) -> at.ABCTree_ABCCatPlus:
    def __internal(
        root_cat,
        conjunct_1,
        children_remaining,
    ):
        conjunct_2 = next(children_rev, None)

        if conjunct_2 is None:
            # conjunct_1 is the rightmost child
            return conjunct_1(root_cat)
        else:
            intermediate_label_new = at.ABCCatPlus(
                cat = root_cat
            )
            setattr(intermediate_label_new, "trace.binconj", "interm")

            return at.TypedTree(
                root = intermediate_label_new,
                children = [ # a binary tree
                    conjunct_1(
                        at.ABCCatFunctor.make_adjunct(
                            mode = at.ABCCatFunctorMode.RIGHT,
                            cat = root_cat
                        ) # <root_cat/root_cat>
                    ), # left
                    __internal( # right
                        root_cat,
                        conjunct_2,
                        children_remaining,
                    )
                ]
            )
        #== END IF ===
    # === END ===

    conjunct_leftmost = next(children_rev) # take the first child
    res =  __internal(
        root.cat,
        conjunct_leftmost,
        children_rev,
    )
    # Mark the root

    tree_label_new = attr.evolve(
        root,
        deriv = ""
    )
    setattr(tree_label_new, "trace.binconj", "root")

    return attr.evolve(
        res,
        root = tree_label_new,
    )
# === END ===

_re_P_PU = re.compile(r"^(P|PU|CONJ)$")

class _ConjunctSpan(typing.NamedTuple):
    """
    [Internal] represents a pair of conjunct (e.g. NP) and a conjunctor (e.g. P, CONJ, PU).
    """
    conj: typing.Optional[at.ABCTree_ABCCatPlus]
    p:    typing.Optional[at.ABCTree_ABCCatPlus]


    def to_TypedTree_radical(
        self,
        surrounding_cat: at.ABCCat,
    ) -> at.ABCTree_ABCCatPlus:
        """
        Convert this into a radical of an (at most binary) `TypedTree`
        which completes what `ABCCat` it assumes as a whole.
        """
        if self.conj is not None and self.p is not None:
            # Binary conjunct
            entire_label = at.ABCCatPlus(
                cat = surrounding_cat,
            )
            setattr(entire_label, "trace.binconj", "conjunctor")

            return at.TypedTree(
                root = entire_label,
                children = [
                    # conjunct
                    self.conj,
                    # conjunctor
                    attr.evolve(
                        self.p,
                        root = at.ABCCatPlus(
                            cat = at.ABCCatFunctor(
                                mode = at.ABCCatFunctorMode.LEFT,
                                ant = self.conj.root.cat,
                                conseq = surrounding_cat
                            )
                        )
                    )
                ]
            )
        elif self.conj is not None: 
            # unary conjunct
            entire_label = at.ABCCatPlus(
                cat = surrounding_cat,
                deriv = "unary-binconj-conjunctor",
            )
            setattr(entire_label, "trace.binconj", "conjunctor")

            return at.TypedTree(
                root = entire_label,
                children = [self.conj],
            )
        elif self.p is not None:
            entire_label = attr.evolve(
                self.p.root,
                cat = surrounding_cat,
            )
            setattr(entire_label, "trace.binconj", "orphan-conjunctor")

            return attr.evolve(
                self.p,
                root = entire_label,
            )
        else:
            raise ValueError(f"Meets a vacuous conjunct span")
        # === END IF ===
    # === END ===

    @classmethod
    def chop_children(
        cls,
        children: typing.Iterator[at.ABCTree_ABCCatPlus]
    ) -> typing.Iterator["_ConjunctSpan"]:
        pt: typing.Optional[at.ABCTree_ABCCatPlus]
        pt2: typing.Optional[at.ABCTree_ABCCatPlus]

        pt = next(children, None)

        if pt is None:
            # end of iter
            return
        else:
            pt_label_cat: at.ABCCat = pt.root.cat

            if isinstance(pt_label_cat, str) and _re_P_PU.match(pt_label_cat):
                # Orphan P
                yield _ConjunctSpan(
                    conj = None,
                    p = pt,
                )
                yield from cls.chop_children(children)
            else:
                pt2 = next(children, None)
                if pt2 is None:
                    # unary conjunct, end
                    yield _ConjunctSpan(
                        conj = pt,
                        p = None,
                    )
                    return
                else:
                    pt2_label_cat: at.ABCCat = pt2.root.cat

                    if isinstance(pt2_label_cat, str) and _re_P_PU.match(pt2_label_cat):
                        # binary conjunct
                        yield _ConjunctSpan(
                            conj = pt, 
                            p = pt2
                        )
                        yield from cls.chop_children(children)
                    else:
                        # unary conjunct + extra
                        yield _ConjunctSpan(
                            conj = pt, 
                            p = None
                        )
                        yield from cls.chop_children(
                            itertools.chain(
                                (pt2, ), # pushing back pt2
                                children
                            )
                        )
                # === END IF ===
            # === END IF ===
        # === END IF ===
    # === END ===
# === END CLASS ===

def binarize_conj_tree(
    subtree: at.ABCTree_ABCCatPlus, 
    Id: str = ""
) -> at.ABCTree_ABCCatPlus:
    """
    Given a tree, binarize recursively its parts that is marked as a conjunction phrase.
    """
    if not subtree.is_terminal():
        tree_label: at.ABCCat_ABCCatPlus = subtree.root

        if (
            not subtree.is_holding_only_terminals()
            and tree_label.deriv.startswith("conj")
        ):
            tree_binarized = __chaining_conjuncts(
                root = tree_label,
                children_rev = (
                    span.to_TypedTree_radical
                    for span in _ConjunctSpan.chop_children(
                        iter(subtree.children)
                    )
                )
            )

            return binarize_conj_tree(tree_binarized)
        else:
            return attr.evolve(
                subtree,
                children = list(
                    binarize_conj_tree(child, Id) 
                    for child in subtree.children
                ),
            )
    else:
        # meet a ternimal node
        return subtree
    # === END IF ===
# === END ===

def binarize_conj_stream(
    f_src: typing.TextIO,
    f_dest: typing.TextIO,
    src_name: typing.Any = "<INPUT>",
    dest_name: typing.Any = "<OUTPUT>",
    matcher: typing.Pattern[str] = re.compile(r"closed"),
    **kwargs
) -> int:
    treebank: at.TypedTreebank[str, str, str] = at.TypedTreebank.from_PTB_basic_stream(
        source = f_src,
        name = "",
    )
    
    treebank_conv: at.TypedTreebank[
        str,
        at.ABCCat_ABCCatPlus, str
    ] = attr.evolve(
        treebank, # type: ignore
        index = {
            ID:binarize_conj_tree(
                tree.fmap(
                    func_nonterm = lambda label: at.ABCCatPlus.from_str(
                        label,
                        cat_parser = at.parser_ABCCat.parse_partial,
                    )
                ),
                Id = ID,
            )
            for ID, tree in treebank.index.items()
        }
    )

    treebank_conv.to_PTB_single_stream(f_dest)
    return 0
# === END ===

def binarize_conj_file(
    src: pathlib.Path, 
    dest: pathlib.Path,
    **kwargs
) -> int:
    try:
        with open(src, "r") as h_src, open(dest, "w") as h_dest:
            res = binarize_conj_stream(
                h_src, h_dest,
                src, dest,
            )
        # === END WITH h_src, h_dest ===
        return res
    except IOError:
        logger.exception(f"IO Error occurred when processing the file: {src}")
        raise
    except Exception as e:
        logger.exception(f"Exception {e} occurred when processing the file: {src}")
        raise
# === END ===