from io import StringIO
import os

import pytest

import abctk.transform_Keyaki.core as core

@pytest.fixture(scope = "module")
def sample_ideal():
    script_path = os.path.dirname(os.path.abspath(__file__))
    with open(
        script_path + "/sample_ideal_obfuscated.psd", "r"
    ) as h_obf, open(
        script_path + "/sample_ideal_orig_processed.txt", "r"
    ) as h_orig, open(
        script_path + "/sample_ideal_decrypted.psd", "r"
    ) as h_dec:
        obf = h_obf.read()
        orig = h_orig.read()
        dec = h_dec.read()
    # === END WITH ===

    yield {
        "obfuscated": StringIO(obf), 
        "original": StringIO(orig), 
        "decrypted": StringIO(dec),
    }
# === END ===

def test_decrypt_stream_with_sample_ideal(
    sample_ideal, 
):
    result = StringIO()
    core.decrypt_stream(
        f_src = sample_ideal["obfuscated"],
        f_orig = sample_ideal["original"],
        f_dest = result,
        src_name = "test:sample_ideal",
        orig_name = "test:sample_ideal_orig_processed",
        dest_name = "<result>"
    )

    assert result.getvalue() == sample_ideal["decrypted"].getvalue()
# === END ===

def test_obfuscate_stream_with_sample_ideal(
    sample_ideal,
):
    result = StringIO()
    core.obfuscate_stream(
        f_src = sample_ideal["decrypted"],
        f_dest = result,
        src_name = "test:sample_ideal",
        dest_name = "<result>"
    )
    assert result.getvalue() == sample_ideal["obfuscated"].getvalue()
# === END ===