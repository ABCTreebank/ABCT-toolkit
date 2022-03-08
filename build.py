import sys
import os
import tempfile
import pathlib
import xdg

import shutil
import subprocess
import requests
import zipfile
import tqdm

import logging

logger = logging.getLogger(__name__)
logger.setLevel(10)

DIR_EXT_SRC = pathlib.Path("./ext_src")
DIR_EXT_SCRIPTS = pathlib.Path("./ext_scripts")
DIR_RUNTIME = pathlib.Path("./abctk/runtime")

#get_requires_for_build_wheel = pt.get_requires_for_build_wheel
#get_requires_for_build_sdist = get_requires_for_build_wheel
#prepare_metadata_for_build_wheel = pt.prepare_metadata_for_build_wheel

def build_ext():
    logger.info("In build_wheel we are using a custom build API backboned by poetry")
    os.makedirs(DIR_RUNTIME, exist_ok = True)

    logger.info("Copy scripts")
    shutil.copy(
        DIR_EXT_SRC / "tsurgeon_script",
        DIR_RUNTIME / "tsurgeon_script"
    )
    shutil.copy(
        DIR_EXT_SCRIPTS / "simplify-tag.sed",
        DIR_RUNTIME / "simplify-tag.sed"
    )
    shutil.copy(
        DIR_EXT_SCRIPTS / "unsimplify-ABC-tags.rb",
        DIR_RUNTIME / "unsimplify-ABC-tags.rb"
    )
    shutil.copy(
        DIR_EXT_SCRIPTS / "move-comparative.tsgn",
        DIR_RUNTIME / "move-comparative.tsgn"
    )

    # Clean the decrypt folder
    DIR_RUNTIME_DECRYPT = pathlib.Path(DIR_RUNTIME / "decrypt")
    if DIR_RUNTIME_DECRYPT.exists():
        if DIR_RUNTIME_DECRYPT.is_dir():
            shutil.rmtree(DIR_RUNTIME_DECRYPT)
        else:
            raise FileExistsError
    # === END IF ===
    shutil.copytree(
        DIR_EXT_SCRIPTS / "decrypt",
        DIR_RUNTIME_DECRYPT,
    )

    shutil.copy(
        DIR_EXT_SCRIPTS / "supertagger_default.jsonnet",
        DIR_RUNTIME / "supertagger_default.jsonnet",
    )

    logger.info("Preprocess the tsurgeon scripts")
    os.makedirs(DIR_RUNTIME / "tsurgeon-debug", exist_ok = True)
    subprocess.run(
        fr"""
            ./lit \
                --input "{DIR_EXT_SCRIPTS}/*.tsgn.md" \
                --output "{DIR_RUNTIME}/tsurgeon-debug/" \
                --pattern "tsurgeon"; \
            cat \
                {DIR_EXT_SCRIPTS}/pretreatments.tsgn.md \
                {DIR_EXT_SCRIPTS}/dependency.tsgn.md \
                {DIR_EXT_SCRIPTS}/dependency-post.tsgn.md \
            | ./lit --stdio --pattern "tsurgeon" \
            > {DIR_RUNTIME}/pre-relabel.tsgn;
        """,
        shell = True
    ).check_returncode()

    logger.info("Build abs-hs (via stack)")
    res_stack = subprocess.Popen(
        (
            "stack", 
            "--local-bin-path", "../../" / DIR_RUNTIME,
            "build", 
            "--copy-bins",
            "--no-haddock",
        ),
        cwd = DIR_EXT_SRC / "abc-hs",
    )

    res_stack.wait()
    if res_stack.returncode: # !== 0
        raise subprocess.CalledProcessError(
            res_stack.returncode, 
            res_stack.args
        )
    # === END IF ===
    logger.info("Successfully built abs-hs (via stack)")


    logger.info("Build move (via SBCL / Roswell)")
    res_ros = subprocess.Popen(
        (
            "ros", "dump", "executable",
            DIR_EXT_SRC / "move.ros",
            "-o", DIR_RUNTIME / "move", "-f",
        )
    )
    res_ros.wait()
    if res_ros.returncode: # !== 0
        raise subprocess.CalledProcessError(
            res_stack.returncode, 
            res_stack.args
        )
    # === END IF ===
    logger.info("Successfully built move")

    # === Get stanford-tregex.jar ===
    logger.info("Obtain Stanford Tregex")
    tregex_zip_cache_path = xdg.xdg_cache_home() / "ABCTreebank-build/stanford-tregex-4.2.0.zip"
    if os.path.isfile(tregex_zip_cache_path) and zipfile.is_zipfile(tregex_zip_cache_path): # TODO: SHA
        logger.info(
            f"An Stanford Tregex zip cache is found at {tregex_zip_cache_path}"
        )    
    else:
        logger.info(
            "No Stanford Tregex zip cache is available. "
            "Try to download one."
        ) 
        tregex_zip_url = "https://nlp.stanford.edu/software/stanford-tregex-4.2.0.zip"
        logger.info(f"Download Stanford Tregex from {tregex_zip_url}")
        tregex_zip_size = int(
            requests.head(tregex_zip_url).headers["content-length"]
        )
        tregex_zip_new = requests.get(tregex_zip_url, stream = True)
        os.makedirs(xdg.xdg_cache_home() / "ABCTreebank-build", exist_ok = True)
        unit_chunk: int = 1024
        with tqdm.tqdm(
            total = tregex_zip_size,
            unit = "B",
            unit_scale = True,
            unit_divisor = unit_chunk
        ) as pb, open(tregex_zip_cache_path, "wb") as temp:
            pb.write("Downloading Stanford Tregex from the Internet ...")
            for chunk in tregex_zip_new.iter_content(chunk_size = 1024):
                temp.write(chunk)
                pb.update(len(chunk))
            # === END FOR chunk ===
        # === END WITH pb, temp ===
    # === END IF ===

    # https://stackoverflow.com/a/17729939
    with zipfile.ZipFile(tregex_zip_cache_path) as zf:
        with zf.open("stanford-tregex-2020-11-17/stanford-tregex.jar") as jar_src, open(DIR_RUNTIME / "stanford-tregex.jar", "wb") as tregex_jar:
            shutil.copyfileobj(jar_src, tregex_jar)
        # === END WITH jar_src, tregex_jar ===
    # === END WITH zf ===

    return 0 # Succeded!
# === END ===

if __name__ == "__main__":
    exit(build_ext())