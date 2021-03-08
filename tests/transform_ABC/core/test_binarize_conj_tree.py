import os
import typing

import pytest

import abctk.transform_ABC.core as core
import abctk.types.trees as trees
from abctk.types.ABCCatPlus import parser_ABCCatPlus
from abctk.types.ABCCat import parser_ABCCat

@pytest.fixture
def sample_ideal():
    script_path = os.path.dirname(os.path.abspath(__file__))

    with open(
        script_path + "/sample_ideal.psd", "r"
    ) as h_data:
        yield trees.parse_ManyTrees_Maybe_with_ID(
            h_data.read(),
            parser_non_terminal = parser_ABCCatPlus(),
        )
# === END ===

def test_binarize_conj_tree(sample_ideal: typing.Iterable[trees.Tree]):
    for tree_with_ID in sample_ideal:
        tree = tree_with_ID.content
        tree_leaves_orig = tree.leaves()

        tree_bined = core.binarize_conj_tree(tree, tree_with_ID.ID)
        tree_leaves_bined = tree_bined.leaves()

        # Property of leaf-order preservation
        assert tree_leaves_orig == tree_leaves_bined
# === END ===
