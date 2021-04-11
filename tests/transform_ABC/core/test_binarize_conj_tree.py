import os
import typing

import pytest

import abctk.transform_ABC.core as core
import abctk.types as at

@pytest.fixture
def sample_ideal():
    script_path = os.path.dirname(os.path.abspath(__file__))

    with open(
        script_path + "/sample_ideal.psd", "r"
    ) as h_data:
        tb = at.TypedTreebank.from_PTB_basic_stream(
            source = h_data,
            name = h_data.name,
        )
        tb.index = {
            ID:tree.fmap(
                func_nonterm = at.ABCCatPlus.from_str,
            )
            for ID, tree in tb.index.items()
        }
        yield tb
# === END ===

def test_binarize_conj_tree(sample_ideal: at.TypedTreebank[str, str, str]):
    for ID, tree in sample_ideal.index.items():
        tree_leaves_orig = tuple(tree.iter_terms())

        tree_bined = core.binarize_conj_tree(tree, ID)
        tree_leaves_bined = tuple(tree_bined.iter_terms())

        # Property of leaf-order preservation
        assert tree_leaves_orig == tree_leaves_bined
# === END ===
