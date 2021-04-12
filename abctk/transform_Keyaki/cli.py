import typing 
import logging
logger = logging.getLogger(__name__)

import re
import sys

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
    name = "decrypt",
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
    
    The corpora mentioned above are:
    - Mainichi Shimbun '95
    - BCCWJ
    - CSJ
    - SIDB
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
