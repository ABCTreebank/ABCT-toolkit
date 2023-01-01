import itertools
import re
import typing

from nltk.tree import Tree 

import abctk.obj.ABCCat as abcc

_re_P_PU = re.compile(r"^(P|PU|CONJ)$")

class _ConjunctSpan(typing.NamedTuple):
    conj: typing.Optional[Tree]
    p   : typing.Optional[Tree]

    def to_Tree(
        self,
        surrounding_cat: abcc.ABCCatReady,
    ) -> Tree:
        if self.conj is not None and self.p is not None:
            # binary conjunct
            return Tree(
                node = abcc.Annot(
                    cat = abcc.ABCCat.p(surrounding_cat),
                    feats = {"trace.binconj": "conjunctor"},
                    pprinter_cat = abcc.ABCCat.pprint,
                ),
                children = [
                    self.conj,
                    Tree(
                        node = abcc.Annot(
                            self.conj.label().cat.l(surrounding_cat),
                            pprinter_cat = abcc.ABCCat.pprint,
                        ),
                        children = list(self.p)
                    )
                ]
            )
        elif self.conj is not None:
            # unary conjunct 
            return Tree(
                node = abcc.Annot(
                    cat = abcc.ABCCat.p(surrounding_cat),
                    feats = {
                        "deriv": "unary-binconj-conjunctor",
                        "trace.binconj": "conjunctor"
                    },
                    pprinter_cat = abcc.ABCCat.pprint,
                ),
                children = [self.conj]
            )
        elif self.p is not None:
            # orphan conjunctor
            return Tree(
                node = abcc.Annot(
                    cat = abcc.ABCCat.p(surrounding_cat),
                    feats = {
                        "trace.binconj": "orphan-conjunctor"
                    },
                    pprinter_cat = abcc.ABCCat.pprint,
                ),
                children = list(self.p)
            )
        else:
            raise ValueError("Meets a vacuous conjunct span")
            
    @classmethod
    def chop_children(
        cls,
        children: typing.Iterator[Tree]
    ) -> typing.Iterator["_ConjunctSpan"]:
        pt: typing.Optional[Tree] = next(children, None)
        pt2: typing.Optional[Tree] = None

        if pt is None:
            # end of iteration
            return
        else:
            pt_label: abcc.Annot[abcc.ABCCat] = pt.label()
            pt_label_cat = pt_label.cat

            if (
                isinstance(pt_label_cat, abcc.ABCCatBase) 
                and _re_P_PU.match(pt_label_cat.name)
            ):
                # orphan P
                yield cls(
                    conj = None,
                    p = pt,
                )
                yield from cls.chop_children(children)
            elif (pt2 := next(children, None)):
                pt2_label: abcc.Annot[abcc.ABCCat] = pt2.label()
                pt2_label_cat = pt2_label.cat

                if (
                    isinstance(pt2_label_cat, abcc.ABCCatBase)
                    and _re_P_PU.match(pt2_label_cat.name)
                ):
                    # conjunct + P
                    yield cls(
                        conj = pt,
                        p = pt2,
                    )
                    yield from cls.chop_children(children)
                else:
                    # pt is an orphan conjucnt
                    yield cls(
                        conj = pt,
                        p = None,
                    )

                    # The status of pt2 is underdetermined.
                    # It should be pushed back.
                    yield from cls.chop_children(
                        itertools.chain(
                            (pt2, ), 
                            children
                        )
                    )
            else:
                # pt1 is the last child and a unary conjunct
                yield cls(
                    conj = pt,
                    p = None,
                )

def __chaining_conjuncts(
    given_label: abcc.Annot[abcc.ABCCat],
    conjuncts: typing.List[
         typing.Callable[
            [abcc.ABCCatReady],
            Tree,
        ],
    ],
    is_root: bool = True,
) -> Tree:
    root_cat = given_label.cat
    if len(conjuncts) == 1:
        # just one conjunct, hence no conjunction is actually there
        conjunct_leftmost = conjuncts[0]
        return conjunct_leftmost(root_cat)
    else:
        conjunct_leftmost, conjunct_remainder = conjuncts[0], conjuncts[1:]

        if is_root:
            tree_label_feats = dict(**given_label.feats)
            tree_label_feats["trace.binconj"] = "root"
        else:
            tree_label_feats = {
                "trace.binconj": "interm"
            }

        tree_label: abcc.Annot[abcc.ABCCat] = abcc.Annot(
            cat = root_cat,
            feats = tree_label_feats,
            pprinter_cat = abcc.ABCCat.pprint,
        )

        return Tree(
            node = tree_label,
            children = [
                conjunct_leftmost(
                    root_cat.adj_l() # <root_cat/root_cat>
                ), 
                __chaining_conjuncts(
                    given_label,
                    conjunct_remainder,
                    is_root = False,
                ),
            ]
        )

def binarize_conj_tree(
    tree: Tree, 
    ID: str = "<UNKNOWN>"
) -> Tree:
    """
    Given a tree, binarize recursively its parts that is marked as a conjunction phrase.

    Notes
    -----
    This method always creates a new Tree instance.
    """
    label: abcc.Annot[abcc.ABCCat] = tree.label()
    children_binarized = [
        (
            binarize_conj_tree(child, ID) 
            if isinstance(child, Tree)
            else child
        )
        for child in tree
    ]

    if (
        len(tree) > 1 
        and label.feats.get("deriv", "none").startswith("conj")
    ):
        return __chaining_conjuncts(
            given_label = label,
            conjuncts = [
                span.to_Tree
                for span in _ConjunctSpan.chop_children(
                    iter(children_binarized)
                )
            ],
        )
    else:
        return Tree(
            node = label,
            children = children_binarized
        )