from nltk import Tree
import pytest

from abctk.types.ABCCat import ABCCat, ABCCatReprMode
from abctk.ml.gen import *

test_trees_raw = (
    (
        "(Sm (Sm#role=h (<Sm/Sm>#role=a LFQ) (Sm#role=h (PPs#role=c (NP#role=c#deriv=unary-NP-type-raising (N 良平)) (<NP\\PPs>#role=h は)) (<PPs\\Sm>#role=h (<<PPs\\Sm>/<PPs\\Sm>>#role=a#deriv=unary-case (NPq#index=1#deriv=unary-NP-type-raising (N 毎日))) (<PPs\\Sm>#role=h (<<PPs\\Sm>/<PPs\\Sm>>#role=a (<<PPs\\Sm>/<PPs\\Sm>>#role=h (NP#role=c#deriv=unary-NP-type-raising (N 村外（はず）れ)) (<NP\\<<PPs\\Sm>/<PPs\\Sm>>>#role=h へ)) (<<<PPs\\Sm>/<PPs\\Sm>>\\<<PPs\\Sm>/<PPs\\Sm>>>#role=a 、)) (<PPs\\Sm>#role=h (<<PPs\\Sm>/<PPs\\Sm>>#role=a (<PPs\\Snml>#role=h (PPo1#role=c (NP#role=c#deriv=unary-NP-type-raising (N (<N/N>#role=a その) (N#role=h 工事))) (<NP\\PPo1>#role=h を)) (<PPo1\\<PPs\\Snml>>#role=h 見物)) (<<PPs\\Snml>\\<<PPs\\Sm>/<PPs\\Sm>>>#role=h に)) (<PPs\\Sm>#role=h (<PPs\\Sm>#role=h 行っ) (<Sm\\Sm>#role=a た))))))) (<Sm\\Sm>#role=a 。))",
        {
            (1, "LFQ", "<Sm/Sm>", 14),
            (2, "良平", "N", 3),
            (3, "は", "<NP\\PPs>", 14),
            (4, "毎日", "N", 14),
            (5, "村外（はず）れ", "N", 6),
            (6, "へ", "<NP\\<<PPs\\Sm>/<PPs\\Sm>>>", 7),
            (7, "、", "<<<PPs\\Sm>/<PPs\\Sm>>\\<<PPs\\Sm>/<PPs\\Sm>>>", 14),
            (8, "その", "<N/N>", 9),
            (9, "工事", "N", 10),
            (10, "を", "<NP\\PPo1>", 11),
            (11, "見物", "<PPo1\\<PPs\\Snml>>", 12),
            (12, "に", "<<PPs\\Snml>\\<<PPs\\Sm>/<PPs\\Sm>>>", 14),
            (13, "行っ", "<PPs\\Sm>", 14),
            (14, "た", "<Sm\\Sm>", 15),
            (15, "。", "<Sm\\Sm>", 0),
        }
    ),
)

class Test_Instance:
    @pytest.mark.parametrize(
        ("tree", "parsed_exp"),
        tuple(
            (Tree.fromstring(tr), parsed_exp)
            for tr, parsed_exp in test_trees_raw
        )
    )
    def test_from_NLTK(self, tree, parsed_exp):
        # Convert categories
        parsed_exp = {
            (
                pos,
                word,
                ABCCat.p(cat).pprint(mode = ABCCatReprMode.DEPCCG),
                head_id
            )
            for pos, word, cat, head_id in parsed_exp
        }
        ist, _, _ = Instance.from_ABC_NLTK_tree(tree)

        assert ist.analysis == parsed_exp