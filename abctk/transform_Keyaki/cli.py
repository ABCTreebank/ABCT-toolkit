import typing 
import logging
logger = logging.getLogger(__name__)

import datetime
import functools
import pathlib
import os
import re
import sys

import attr
import click

import abctk.cli_tool as ct 
import abctk.config as CONF
import abctk.types.trees as at

from . import core

def _process_filelist(
    conf: dict,
    dir_result: pathlib.Path,
    dir_log: typing.Optional[pathlib.Path],
    flist: ct.FileList,
    **kwargs,
):
    import multiprocessing as mp
    import tqdm

    proc_num: int = conf["max_process_num"]
    with mp.Pool(processes = proc_num) as pool:
        logger.info(f"Number of processes: {proc_num}")

        flist_dest_expanded = tuple(
            (src, dir_result / fn, os.path.getsize(src))
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

def __conv_file_wrapper(
    args: typing.Tuple[pathlib.Path, pathlib.Path, int]
    #src: pathlib.Path,
    #dest: pathlib.Path,
    #size: int,
) -> typing.Tuple[int, int]:
    return (core.obfuscate_file(args[0], args[1]), args[2])
# === END ===

cmd_obfuscate = ct.CmdTemplate_Batch_Process_on_Tree(
    name = "trans_obfuscate",
    logger_orig = logger,
    folder_prefix = "trans_obfuscate",
    with_intermediate = False,
    callback_preprocessing = None,
    callback_process_filelist = _process_filelist,
    callback_process_rawtrees = functools.partial(
        core.obfuscate_stream,
        f_src = sys.stdin,
        f_dest = sys.stdout,
        src_name = "<INPUT>",
        dest_name = "<OUTPUT>",
    ),
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
        default = r"closed"
    )
)

@click.group()
@click.pass_context
def cmd_main(ctx):
    pass

cmd_main.add_command(
    cmd_obfuscate, 
    name = "obfuscate",
)

