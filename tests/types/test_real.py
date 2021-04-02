import sys
PY_VER = sys.version_info

if PY_VER >= (3, 7):
    import importlib.resources as imp_res # type: ignore
else:
    import importlib_resources as imp_res # type: ignore

import fs
import pytest
import abctk.types.core as core
import abctk.types.real as real

module_trees = "tests.resources.trees"
module_trees_ABCTreebank_sample = "test.resources.trees.ABCTreebank_sample"

@pytest.fixture(scope = "module")
def sample_KeyakiTreebank():
    # Use the sample of the ABC TB as the Keyaki TB
    with imp_res.path(module_trees, "ABCTreebank_sample") as pth:
        yield pth

@pytest.fixture(scope = "module")
def sample_ABCTreebank():
    with imp_res.path(module_trees, "ABCTreebank_sample") as pth:
        yield pth

def test_load_KeyakiTB_and_dumped_equals_original(sample_KeyakiTreebank):
    with fs.open_fs(str(sample_KeyakiTreebank)) as tb_raw:
        tb_name = str(tb_raw)
        tb = core.TypedTreebank.from_PTB_basic_FS(
            tb_raw,
            name = tb_name,
            # No need of disambiguation of IDs. 
            # The uniqueness of IDs are guaranteed.
            disambiguate_IDs_by_path = False,
            # It can be assumed that every sentence is with an ID.
            uniformly_with_ID = True, 
        )

        assert "7_misc_EXAMPLE;part_115_law;JP" in tb.index
        assert "7_misc_EXAMPLE;part_115_law;JPsss" not in tb.index

        with fs.open_fs("mem://", writeable = True) as mem:
            tb.to_PTB_FS(
                mem,
                path_maker = real.make_path_from_Keyaki_or_ABC_ID,
            )

            tb_again = core.TypedTreebank.from_PTB_basic_FS(
                mem,
                name = tb_name,
                disambiguate_IDs_by_path = False,
                uniformly_with_ID = True, 
            )

            assert tb == tb_again
# === END ===

def test_load_ABCTB_and_dumped_equals_original(sample_ABCTreebank):
    with fs.open_fs(str(sample_ABCTreebank)) as tb_raw:
        tb_name = str(tb_raw)
        tb = core.TypedTreebank.from_PTB_basic_FS(
            tb_raw,
            name = tb_name,
            # No need of disambiguation of IDs. 
            # The uniqueness of IDs are guaranteed.
            disambiguate_IDs_by_path = False,
            # It can be assumed that every sentence is with an ID.
            uniformly_with_ID = True, 
        )
        tb.index = {
            k:v.fmap(
                func_nonterm = lambda src: real.ABCCatPlus.from_str(
                    src,
                    cat_parser = real.parser_ABCCat.parse_partial
                )
            )
            for k, v in tb.index.items()
        }

        assert "7_misc_EXAMPLE;part_115_law;JP" in tb.index
        assert "7_misc_EXAMPLE;part_115_law;JPsss" not in tb.index

        with fs.open_fs("mem://", writeable = True) as mem:
            tb.to_PTB_FS(
                mem,
                path_maker = real.make_path_from_Keyaki_or_ABC_ID,
            )

            tb_again = core.TypedTreebank.from_PTB_basic_FS(
                mem,
                name = tb_name,
                disambiguate_IDs_by_path = False,
                uniformly_with_ID = True, 
            )
            tb_again.index = {
                k:v.fmap(
                    func_nonterm = lambda src: real.ABCCatPlus.from_str(
                        src,
                        cat_parser = real.parser_ABCCat.parse_partial
                    )
                )
                for k, v in tb_again.index.items()
            }
            assert tb.index["1_misc_BUFFALO;TSOGD_1a;JP"] == tb_again.index["1_misc_BUFFALO;TSOGD_1a;JP"]
            #assert tb == tb_again
# === END ===