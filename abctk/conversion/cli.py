import typing
import enum
import logging
logger = logging.getLogger(__name__)

import datetime
import functools
import os
import pathlib
import sys

import click

import abctk.cli_tool as ct
import abctk.config as CONF
from . import core

def _check_sys_runtimes(conf: dict, **kwargs) -> int:
    return core.check_runtimes(conf["bin-sys"])
# === END ===

def _process_filelist(
    conf: dict,
    dir_result: pathlib.Path,
    dir_log: typing.Optional[pathlib.Path],
    flist: ct.FileList,
    **kwargs,
) -> int:
    import multiprocessing as mp
    import tqdm

    proc_num: int = conf["max_process_num"]
    with mp.Pool(processes = proc_num) as pool:
        logger.info(f"Number of processes: {proc_num}")

        flist_dest_expanded: typing.List[KeyakiFileConversionArgs] = list(
            KeyakiFileConversionArgs(
                src = src,
                dest = dir_result / fn,
                size = os.path.getsize(src),
                conf = conf,
                log_prefix = (
                    dir_log / fn
                    if dir_log
                    else None
                ),
            )
            for src, fn 
            in flist.iterate_truncating_commonprefix()
        )
        files_total_size: int = sum(
            map(lambda x: x[2], flist_dest_expanded)
        )
        
        jobs = pool.imap_unordered(
            __conv_file_wrapper,
            flist_dest_expanded,
        )
        with tqdm.tqdm(
            total = files_total_size, 
            unit = "B",
            unit_scale = True,
            unit_divisor = 1024
        ) as pb:
            pb.write("Converting Keyaki trees into ABC trees:")
            for _return_code, src_size in jobs:
                pb.update(src_size)
        # === END WITH pb ===
    # === END FOR path_src, filename_res ===

    return 0
# === END ===

def _process_rawtrees(
    conf: dict,
    dir_log: typing.Optional[pathlib.Path],
    **kwargs,
) -> int:
    return core.convert_keyaki_to_abc(
        f_src = sys.stdin,
        f_dest = sys.stdout,
        src_name = "<STDIN>",
        dest_name = "<STDOUT>",
        conf = conf,
        log_prefix = dir_log,
    )
# === END ===

class KeyakiFileConversionArgs(typing.NamedTuple):
    src: pathlib.Path
    dest: pathlib.Path
    size: int
    conf: typing.Dict[str, typing.Any] = CONF.CONF_DEFAULT
    log_prefix: typing.Union[None, str, pathlib.Path] = None
# === END CLASS ===

def __conv_file_wrapper(
    args: KeyakiFileConversionArgs
) -> typing.Tuple[int, int]:
    """A wrapper function that calls the routine of Keyaki file conversion.

    Parameters
    ----------
    args: KeyakiFileConversionArgs

    Returns
    -------
    return_code: int
        0 if the checking succeeds.
        2 (ENOENT) if any of the runtimes is not found.
    size: int
        The size of the converted file. Equals to `args.size`.
    """
    return (
        core.convert_keyaki_file_to_abc(
            args.src, args.dest,
            conf = args.conf,
            log_prefix = args.log_prefix
        ),
        args.size
    )
# === END ===

cmd_main = ct.CmdTemplate_Batch_Process_on_Tree(
    name = "conv",
    logger_orig = logger,
    folder_prefix = "conv",
    with_intermediate = True,
    callback_preprocessing = _check_sys_runtimes,
    callback_process_filelist = _process_filelist,
    callback_process_rawtrees = _process_rawtrees,
)
cmd_main.__doc__ = "Convert Keyaki tree(s) to ABC trees."