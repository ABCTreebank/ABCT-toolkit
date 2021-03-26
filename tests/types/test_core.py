import sys
PY_VER = sys.version_info

if PY_VER >= (3, 7):
    import importlib.resources as imp_res # type: ignore
else:
    import importlib_resources as imp_res # type: ignore

import fs
import pytest
import abctk.types.core as core

module_trees = "tests.resources.trees"
module_trees_devised = "tests.resources.trees.devised"

@pytest.fixture(scope = "module")
def sample_trees_folder():
    with imp_res.path(module_trees, "devised") as folder:
        return folder

@pytest.fixture(scope = "module")
def sample_single_tree_raw():
    return imp_res.read_text(module_trees_devised, "test_single.psd")

@pytest.fixture(scope = "module")
def sample_multiple_trees_raw():
    return imp_res.read_text(module_trees_devised, "test_multiple.psd")

def test_parse_single_tree(sample_single_tree_raw):
    assert isinstance(
        core.TypedTree.from_PTB(sample_single_tree_raw),
        core.TypedTree,
    )

def test_parse_multiple_trees_with_ID(sample_multiple_trees_raw):
    res = core.TypedTreebank.from_PTB(
        sample_multiple_trees_raw,
        name = "test",
        version = None,
        container_version = None,
    )
    assert isinstance(res, core.TypedTreebank)

def test_load_trees(sample_trees_folder):
    with fs.open_fs(str(sample_trees_folder)) as tb:
        res = core.TypedTreebank.from_PTB_FS(
            tb,
        )
        assert isinstance(res.index["1_misc_TOPTEN;1a;JP"], core.TypedTree)

def test_dump_trees(sample_trees_folder):
    with fs.open_fs(str(sample_trees_folder)) as tb:
        res = core.TypedTreebank.from_PTB_FS(
            tb,
        )

        with fs.open_fs("mem://", writeable = True) as mem:
            res.to_PTB_FS(mem)

            mem.isfile("/untitled.psd")

def test_load_disamb_trees_and_dumped_equals_original(sample_trees_folder):
    with fs.open_fs(str(sample_trees_folder)) as tb_raw:
        tb = core.TypedTreebank.from_PTB_FS(
            tb_raw,
            name = "test",
            disambiguate_IDs_by_path = True,
        )

        with fs.open_fs("mem://", writeable = True) as mem:
            tb.to_PTB_FS(
                mem,
                path_maker = core.treeIDstr_to_path_default,
            )

            tb_again = core.TypedTreebank.from_PTB_FS(
                mem,
                name = "test",
                disambiguate_IDs_by_path = True,
            )

            assert tb == tb_again