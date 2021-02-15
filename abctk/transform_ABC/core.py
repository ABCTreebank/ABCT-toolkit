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

__re_P_PU = re.compile(r"^(P|PU|CONJ)$")

def __binarize_internal(
    root_cat: at.ABCCat,
    children: typing.Iterator[typing.Callable[[at.ABCCat], at.Tree]],
) -> typing.Optional[at.Tree]:
    conjunct_1 = next(children, None)
    if conjunct_1 is None:
        return None
    else:
        conjunct_2 = next(children, None)
        if conjunct_2 is None:
            return conjunct_1(root_cat)
        else:
            intermediate_label_new = at.ABCCatPlus(
                cat = root_cat
            )
            setattr(intermediate_label_new, "trace.binconj", "interm")

            return at.Tree(
                intermediate_label_new,
                [
                    conjunct_1(
                        at.ABCCatFunctor.make_adjunct(
                            mode = at.ABCCatFunctorMode.RIGHT,
                            cat = root_cat
                        )
                    ),
                    __binarize_internal(
                        root_cat,
                        itertools.chain((conjunct_2, ), children)
                    )
                ]
            )
        # === END IF ===
    # === END IF ===
# === END ===

def __chop_children(
    children: typing.Iterator[at.Tree]
) -> typing.Iterator[
    typing.Tuple[
        typing.Optional[at.Tree],
        typing.Optional[at.Tree],
    ]
]:
    pt: typing.Optional[at.Tree]
    pt2: typing.Optional[at.Tree]

    pt = next(children, None)

    if not isinstance(pt, at.Tree):
        # end of iter
        return
    else:
        pt_label_cat: at.ABCCat = pt.label().cat

        if isinstance(pt_label_cat, str) and __re_P_PU.match(pt_label_cat):
            # Orphan P
            yield (None, pt)
            yield from __chop_children(children)
        else:
            pt2 = next(children, None)
            if pt2 is None:
                # unary conjunct, end
                yield (pt, None)
                return
            else:
                pt2_label_cat: at.ABCCat = pt2.label().cat

                if isinstance(pt2_label_cat, str) and __re_P_PU.match(pt2_label_cat):
                    # binary conjunct
                    yield (pt, pt2)
                    yield from __chop_children(children)
                else:
                    # unary conjunct + extra
                    yield (pt, None)
                    yield from __chop_children(
                        itertools.chain(
                            (pt2, ), # pushing back pt2
                            children
                        )
                    )
            # === END IF ===
        # === END IF ===
    # === END IF ===
# === END ===

def __binarize_conjunct(
    conjunctee: typing.Optional[at.Tree],
    conjunctor: typing.Optional[at.Tree],
) -> typing.Callable[[at.ABCCat], at.Tree]:
    if conjunctor is None:
        if conjunctee is None:
            raise ValueError
        else:
            # unary conjunct
            def __factory(c: at.ABCCat): #-> at.ABCCatPlus[at.ABCCat]:
                res_cat = at.ABCCatPlus(
                    cat = c,
                    deriv = "unary-binconj-conjunctor"
                )
                setattr(res_cat, "trace.binconj", "conjunctor")
                return res_cat
            # === END ===

            return lambda c: at.Tree(
                __factory(c),
                [conjunctee],
            )
        # === END IF ===
    else:
        if conjunctee is None:
            # Orphan P
            def __factory(c: at.ABCCat):
                res_label = at.ABCCatPlus(
                    cat = c,
                )
                setattr(res_label, "trace.binconj", "orphan-conjunctor")
                return res_label
            # === END ===

            return lambda c: at.Tree(
                __factory(c),
                conjunctor
            )
        else:
            # Binary conjunct
            def __factory_conjunctor(parent: at.ABCCat, left: at.ABCCat): 
                #-> at.ABCCatPlus[at.ABCCat]:
                res_cat = at.ABCCatPlus(
                    cat = at.ABCCatFunctor(
                        mode = at.ABCCatFunctorMode.LEFT,
                        ant = left,
                        conseq = parent
                    )
                )
                return res_cat
            # === END ===

            def __factory_conjunct(c: at.ABCCat):
                res_cat = at.ABCCatPlus(
                    cat = c
                ) 
                setattr(res_cat, "trace.binconj", "conjunctor")
                return res_cat
            # === END ===

            return lambda c: at.Tree(
                __factory_conjunct(c),
                [
                    conjunctee,
                    at.Tree(
                        __factory_conjunctor(
                            parent = c,
                            left = conjunctee.label().cat
                        ),
                        conjunctor
                    )
                ]
            )
        # === END IF ===
    # === END IF ===
# === END ===

def binarize_conj_tree(
    subtree: at.Tree, 
    Id: str = ""
) -> at.Tree:
    if isinstance(subtree, at.Tree):
        tree_label: at.ABCCatPlus[at.ABCCat] = subtree.label()

        if subtree.height() > 2 and tree_label.deriv.startswith("conj"):
            tree_new_children = __binarize_internal(
                tree_label.cat,
                reversed(
                    tuple(
                        map(
                            lambda args: __binarize_conjunct(*args),
                            __chop_children(iter(subtree)),
                        )
                    )
                )
            )
            
            if tree_new_children is None:
                raise ValueError(
                    f"Failed CONJ binarization at the node {subtree} "
                    f"of the tree {Id}"
                )
            # === END IF ===

            tree_label_new = attr.evolve(tree_label, deriv = "")
            setattr(tree_label_new, "trace.binconj", "root")

            return at.Tree(
                tree_label_new,
                map(
                    functools.partial(binarize_conj_tree, Id = Id),
                    tree_new_children
                )
            )
        else:
            return at.Tree(
                tree_label,
                map(
                    functools.partial(binarize_conj_tree, Id = Id),
                    subtree
                )
            )
    elif isinstance(subtree, str):
        return subtree
    else:
        raise ValueError(f"Ill-formed Tree, ID: {Id}")
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
    trees_Maybe_wID: typing.Iterable[at.Tree_with_ID] = at.parse_ManyTrees_Maybe_with_ID(
            f_src.read(),
            parser_non_terminal = at.parser_ABCCatPlus(),
        )

    def __func(tree_wID: at.Tree_with_ID):
        return attr.evolve(
            tree_wID,
            content = binarize_conj_tree(tree_wID.content, tree_wID.ID)
        )
    # === END ===

    trees_converted = map(__func, trees_Maybe_wID)

    f_dest.write(
        "\n".join(
            map(lambda t: t.print_oneline(), trees_converted)
        )
    )
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