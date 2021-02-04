import typing
import enum
import logging
logger = logging.getLogger(__name__)

import datetime
import pathlib
import os

import click

import abctk.cli_tool as ct
import abctk.config as CONF
from . import core

@click.command()
@click.option(
    "-i", "--input", "--source", "source_type",
    type = click.Choice(
        choices = ("rawtrees", "filelist"),
        case_sensitive = False
    ),
    default = "rawtrees",
    help = """
        \b
        Designating your data source. 
        - `rawtrees' means that input Keyaki trees are provided directry from STDIN.
        - `filelist' indicates that STDIN provides a list of paths to Keyaki tree files.
        Default to `stdin'. Case insensitive.
    """
)
@click.option(
    "-o", "--output", "--to", "--destination", "destination",
    type = click.Path(file_okay = False, dir_okay = True),
    help = """
        Path to a folder that stores the resulting files.
        Since this program yields results in multiple files in different formats, it is always needed to have a storage folder.
        Default to `./result_(timestamp)`.
    """
)
@click.option(
    "-o", "--overwrite/--no-overwrite", "can_overwrite",
    default = False,
)
@click.option(
    "--intermediate/--no-intermediate", "if_gen_intermediate",
    default = False,
    help = """
        When specified, the program will generate 
            intermediate products of the conversion process
            that facilitate development and debugging. 
    """,
)
@click.option(
    "--intermediate-dir", "intermediate_dir",
    type = click.Path(file_okay = False, dir_okay = True),
    default = None,
    help = """
        The path to intermediate logs.
        This option has no effect unless the `--intermediate' flag is set on.
    """,
)
@click.pass_context
def cmd_main(
    ctx: click.Context,
    source_type: str,
    destination: typing.Optional[str],
    can_overwrite: bool,
    if_gen_intermediate: bool,
    intermediate_dir: typing.Optional[str],
) -> None:
    """
        Convert Keyaki tree(s) to ABC trees.
    """
    CONFIG = ctx.obj["CONFIG"]
    
    # ================
    # Check the system runtimes
    # ================
    import sys

    runtime_check_res: int = core.check_runtimes(CONFIG["bin-sys"])
    if runtime_check_res:
        sys.exit(runtime_check_res)
    else:
        pass
    # === END IF ===

    # ================
    # Conversion
    # ================
    if source_type == "filelist":
        # Prepare the destination folder
        res_folders: typing.Dict[str, pathlib.Path]
        
        res_folders = ct.create_folder_time_multiple(
            filter(
                None,
                (
                    "result_conv_" if not destination else None, 
                    "log_conv_" 
                    if if_gen_intermediate and not intermediate_dir
                    else None,
                )
            )
        )
        if destination:
            result_conv_parsed = pathlib.Path(destination)
            if result_conv_parsed.is_dir():
                # Check if the folder is empty or not
                pass
            else: 
                result_conv_parsed.mkdir(parents = True)
            # === END IF ===

            res_folders["result_conv_"] = result_conv_parsed
        else:
            pass
        # === END IF ===

        if if_gen_intermediate and intermediate_dir:
            intermediate_parsed = pathlib.Path(intermediate_dir)

            if intermediate_parsed.is_dir():
                # Check if the folder is empty or not
                pass
            else: 
                intermediate_parsed.mkdir(parents = True)
            # === END IF ===

            res_folders["log_conv_"] = intermediate_parsed
        else:
            pass
        # === END IF ===

        flist: ct.FileList = ct.FileList.from_file_list(sys.stdin)

        import multiprocessing as mp
        import tqdm

        proc_num: int = CONFIG["max_process_num"]
        with mp.Pool(processes = proc_num) as pool:
            logger.info(f"Number of processes: {proc_num}")

            log_prefix = res_folders.get("log_conv_")

            flist_dest_expanded: typing.List[KeyakiFileConversionArgs] = list(
                KeyakiFileConversionArgs(
                    src = src,
                    dest = res_folders["result_conv_"] / fn,
                    size = os.path.getsize(src),
                    conf = CONFIG,
                    log_prefix = (
                        log_prefix / fn
                        if log_prefix
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
    elif source_type == "rawtrees":
        log_pfx: typing.Optional[pathlib.Path]

        if if_gen_intermediate:
            if intermediate_dir:
                intermediate_dir_parsed = pathlib.Path(intermediate_dir)
                if intermediate_dir_parsed.is_dir():
                # Check if the folder is empty or not
                    pass
                else: 
                    intermediate_dir_parsed.mkdir(parents = True)
                # === END IF ===
                log_pfx = intermediate_dir_parsed / "rawtrees"
            else:
                log_pfx = ct.create_folder_time("log_conv") / "rawtrees"
            # === END IF ===
        else:
            log_pfx = None
        # === END IF ===

        _ = core.convert_keyaki_to_abc(
            f_src = sys.stdin,
            f_dest = sys.stdout,
            src_name = "<STDIN>",
            dest_name = "<STDOUT>",
            conf = CONFIG,
            log_prefix = log_pfx,
        )
    else:
        logger.error(
            "Invalid CLI option: `source_type' must be either `stdin` or `filelist', "
            f"but {source_type} is given."
        )
        raise ValueError()
    # === END IF ===
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