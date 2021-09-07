import importlib.resources as imp_res
from pathlib import Path
import os
import shutil
import subprocess
import sys
import tempfile
import typing

import fs
import fs.base
import typer

import abctk.transform_Keyaki.corpus_readers as corpus_readers

app = typer.Typer()

@app.callback()
def cmd_main():
    """
    Encrypt (obfuscate) or decrypt the proprietary part of the Keyaki and the ABC Treebank.  
    """

@app.command("de-legacy")
def cmd_decrypt(
    ctx: typer.Context,
    source_dir: Path,
    dest_dir: Path,
):
    """ 
    An legacy program to decrypt some of the closed part of the ABC Treebank.

    \b
    This decrypts the part that is originated from the following corpora:
    - BCCWJ
    - CSJ
    - SIDB
    For the Mainichi 95', use `abctk trans-Keyaki decrypt-Mai`.

    The paths to them are to be specified in a config file.
    Either deploy these corpora to the default paths, or alter the default by user configs.

    Runtime requirements: gawk, xslproc, xmllint, Java runtime
    \f

    See Also
    --------
    `The Keyaki Treebank <https://github.com/ajb129/KeyakiTreebank>`_
        The scripts come from there. 
    """
    CONF: typing.Dict[str, typing.Any] = ctx.obj["CONFIG"]

    dest_dir_path = Path(dest_dir)
    if dest_dir_path.exists():
        if dest_dir_path.is_dir():
            pass
        else:
            raise FileExistsError
    else:
        os.mkdir(dest_dir_path)

    with tempfile.TemporaryDirectory(
    ) as ws, imp_res.path(
        "abctk.runtime", "decrypt"
    ) as dec_script_path:
        links = (
            (Path(source_dir).absolute(), f"{ws}/closed", True),
            (Path(dest_dir).absolute(), f"{ws}/treebank", True),
            (CONF["runtimes"]["tregex"], f"{ws}/stanford-tregex.jar", False),
        )
        for src, link, is_dir in links:
            os.symlink(src, link, target_is_directory = is_dir)

        shutil.copytree(
            dec_script_path,
            f"{ws}/scripts",
        )

        procs = tuple(
            subprocess.Popen(
                [
                    f"{ws}/scripts/integrate_{corpus}_characters",
                    "--source",
                    CONF['corpora'][corpus],
                ]   
            )
            for corpus in ("CSJ", "BCCWJ", "SIDB")
        )
        procs_result = tuple(proc.wait() for proc in procs)

        for res in procs_result:
            if res:
                raise RuntimeError(res)

@app.command("en")
def cmd_encrypt(
    ctx: typer.Context,
    input_path: Path = typer.Argument(...),
    output_path: Path = typer.Argument(None),
):
    """ 
    Obfuscate the proprietary part.
    """

@app.command("prep")
def cmd_extract_from_corpora(
    ctx: typer.Context,
):
    """ 
    Extract data from proprietary corpora 
    so that the Keyaki/ABC Treebank gets decrypted.
    
    The corpora that are relevant here are:
    - Mainichi Shimbun '95
    - (BCCWJ) not supported yet
    - (CSJ) not supported yet
    - (SIDB) not supported yet
    Paths to them are to be specified via the CONFIG file.

    Extracted sentences will be printed in the TSV format to STDOUT.
    """
    path_corpora = ctx.obj["CONFIG"]["corpora"]

    sys.stdout.writelines(
        ident.to_tsv_line_with_sentence(sent)
        for ident, sent
        in corpus_readers.extract_from_corpora(
            corpus_Mai95 = path_corpora["Mainichi95"]
        )
    )
