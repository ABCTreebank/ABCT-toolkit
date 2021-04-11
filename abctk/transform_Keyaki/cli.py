import typing 
import logging
logger = logging.getLogger(__name__)

import re

import click

import abctk.cli_tool as ct 
import abctk.config as CONF
import abctk.types as at

from . import core

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

@click.group(
    short_help = "tweak Keyaki trees",
)
@click.pass_context
def cmd_main(ctx):
    pass

cmd_main.add_command(
    cmd_obfuscate, 
    name = "obfuscate",
)

