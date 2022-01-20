import typing

import pytest

from nltk.tree import Tree

from abctk.types.ABCCat import Annot, ABCCat
import abctk.io.nltk_tree as at
import abctk.transform_ABC.binconj as abin

def parse_nodes(tree: typing.Union[Tree, str]):
    if isinstance(tree, Tree):
        label_new = Annot.parse(
            tree.label(),
            parser_cat = ABCCat.parse,
            pprinter_cat = ABCCat.pprint
        )

        tree.set_label(label_new)

        for child in tree:
            parse_nodes(child)
    else:
        # do nothing
        pass 

class TestItem(typing.NamedTuple):
    ID: str
    tree: Tree
    answer_chopped_cat: typing.Sequence[
        typing.Tuple[
            typing.Optional[str],
            typing.Optional[str],
        ]
    ]
    tree_raw: str

    @classmethod
    def from_string(cls, source: str, answer_chopped_cat):
        ID, tree = at._split_ID_from_Tree(
            Tree.fromstring(source)
        )
        parse_nodes(tree)

        return cls(
            str(ID),
            tree,
            answer_chopped_cat,
            tree_raw = source,
        )

    def spanw_new(self):
        return self.from_string(
            self.tree_raw,
            answer_chopped_cat = self.answer_chopped_cat
        )

test_items = (
    TestItem.from_string(
        """
( (NP#deriv=conj (NP 太郎)
                 (P と)
                 (NP 花子)
                 (PU ，)
                 (P そして)
                 (NP 次郎)
                 (P あるいは)
                 (NP 三郎)
                 (P か)
                 (NP 佳子)
                 (P か))
  (ID 1))
        """,
        (
            ("NP", "P"), 
            ("NP", "PU"), 
            (None, "P"), 
            ("NP", "P"), 
            ("NP", "P"), 
            ("NP", "P")
        ),
    ),
    TestItem.from_string(
        """
( (NP#deriv=conj (NP 女) 
                 (P や) 
                 (NP 男))
  (ID 2))
        """,
        (
            ("NP", "P"),
            ("NP", None),
        )
    )
)

class Test_ConjunctSpan:
    @pytest.mark.parametrize(
        "item", test_items
    )
    def test_chop_children(self, item: TestItem):
        tree = item.spanw_new().tree

        chopped = abin._ConjunctSpan.chop_children(
            iter(tree)
        )

        print(tree[0],tree[1])
        for span, (pt, pt2) in zip(chopped, item.answer_chopped_cat):
            if (span_pt := span.conj) is not None:
                assert span_pt.label().cat.equiv_to(pt)
            else:
                assert pt is None
            
            if (span_pt2 := span.p) is not None:
                assert span_pt2.label().cat.equiv_to(pt2)
            else:
                assert pt2 is None

@pytest.mark.parametrize(
    "item", test_items
)
def test_binarize_conj_tree(item: TestItem):
    tree = item.spanw_new().tree
    tree_bin = abin.binarize_conj_tree(tree, item.ID)

    def _test_tree(tree):
        if isinstance(tree, Tree):
            label: Annot[ABCCat] = tree.label()
            if (trace := label.feats.get("trace.binconj", None)):
                assert len(tree) <= 2, "Unsuccessful conjunction binarization"
    
            for child in tree:
                _test_tree(child)
        else:
            # do nothing 
            pass

    _test_tree(tree_bin)

    print(tree_bin)