import typing
import enum
import logging
logger = logging.getLogger(__name__)

import abctk.cli_tool
from . import core

def _check_sys_runtimes(conf: dict, **kwargs) -> int:
    return core.check_runtimes(conf["bin-sys"])
# === END ===

cmd_main = abctk.cli_tool.CmdTemplate_Batch_Process_on_Tree(
    name = "conv",
    logger_orig = logger,
    folder_prefix = "conv",
    with_intermediate = True,
    callback_preprocessing = _check_sys_runtimes,
    callback_process_file = core.convert_keyaki_file_to_abc,
    callback_process_rawtrees = core.convert_keyaki_to_abc,
)
cmd_main.__doc__ = "Convert Keyaki tree(s) to ABC trees."