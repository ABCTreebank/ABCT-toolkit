import typing
import logging
logger = logging.getLogger(__name__)

import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile

PY_VER = sys.version_info
if PY_VER >= (3, 7):
    import importlib.resources as imp_res # type: ignore
else:
    import importlib_resources as imp_res # type: ignore

import click

import abctk.cli_tool as ct 
import abctk.config as CONF
import abctk.types as at

from . import core
from . import corpus_readers

@click.group(
    short_help = "tweak Keyaki trees",
)
@click.pass_context
def cmd_main(ctx):
    pass

cmd_obfuscate = ct.CmdTemplate_Batch_Process_on_Tree(
    name = "trans_obfuscate",
    logger_orig = logger,
    folder_prefix = "trans_obfuscate",
    with_intermediate = False,
    callback_preprocessing = None,
    callback_process_file = core.obfuscate_file,
    callback_process_rawtrees = core.obfuscate_stream,
    short_help = "obfuscate trees"
)

def _compile_obfus_matcher(
    ctx: click.Context,
    param: str,
    value: str,
) -> typing.Pattern[str]:
    res: typing.Pattern[str]

    try: 
        res = re.compile(value)
    except:
        raise click.BadParameter(f"{value} is not regex-comparable")
    # === END TRY ===

    return res
# === END ===

cmd_obfuscate.params.append(
    click.Option(
        param_decls = [
            "-m",
            "--matcher",
        ],
        type = str,
        callback = _compile_obfus_matcher,
        default = r"closed",
        help = """A regex that specifies 
the IDs of the trees to be obfuscated.
Default to /closed/."""
    )
)

cmd_main.add_command(
    cmd_obfuscate, 
    name = "obfuscate",
)

@cmd_main.command(
    name = "decrypt-legacy"
)
@click.argument(
    "source_dir",
    metavar = "SOURCE",
    type = click.Path(
        exists = True,
        file_okay = False,
        dir_okay = True,
    ),
)
@click.argument(
    "dest_dir",
    metavar = "DEST",
    type = click.Path(
        file_okay = False,
        dir_okay = True,
    ),
)
@click.pass_context
def cmd_decrypt_legacy(
    ctx: click.Context,
    source_dir: str,
    dest_dir: str,
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

    .. seealso::
        `The Keyaki Treebank <https://github.com/ajb129/KeyakiTreebank>`_
            The scripts come from there. 
    """
    CONF: typing.Dict[str, typing.Any] = ctx.obj["CONFIG"]

    dest_dir_path = pathlib.Path(dest_dir)
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
            (pathlib.Path(source_dir).absolute(), f"{ws}/closed", True),
            (pathlib.Path(dest_dir).absolute(), f"{ws}/treebank", True),
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

cmd_decrypt = ct.CmdTemplate_Batch_Process_on_Tree(
    name = "trans_decrypt",
    logger_orig = logger,
    folder_prefix = "trans_deobfuscate",
    with_intermediate = False,
    callback_preprocessing = None,
    callback_process_file = core.decrypt_file,
    callback_process_rawtrees = core.decrypt_stream,
    short_help = "decrypt trees"
)

cmd_decrypt.params.append(
    click.Argument(
        param_decls = ["corpora_tsv"],
        type = click.File(),
        #short_help = "The path to a TSV file made beforehand"
    )
)

cmd_main.add_command(
    cmd_decrypt, 
    name = "decrypt-Mai",
)

@cmd_main.command(
    name = "extract_from_corpora",
    short_help = "extract data from proprietary corpora"
)
@click.pass_context
def cmd_extract_from_corpora(ctx):
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
