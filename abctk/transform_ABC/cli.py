import typing 
import logging
logger = logging.getLogger(__name__)

import re

import click

import abctk.cli_tool as ct 
import abctk.config as CONF

from . import core

cmd_binarize_conj = ct.CmdTemplate_Batch_Process_on_Tree(
    name = "trans_binarize_CONJ",
    logger_orig = logger,
    folder_prefix = "trans_bin_conj",
    with_intermediate = False,
    callback_preprocessing = None,
    callback_process_file = core.binarize_conj_file,
    callback_process_rawtrees = core.binarize_conj_stream,
    short_help = "binarize CONJ subtrees"
)

@click.group(
    short_help = "tweak ABC Treebank trees",
)
@click.pass_context
def cmd_main(ctx):
    pass

cmd_main.add_command(
    cmd_binarize_conj, 
    name = "binarize-conj",
)

