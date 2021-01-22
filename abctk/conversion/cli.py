import typing
import enum
import logging
logger = logging.getLogger(__name__)

import datetime
import pathlib
import os

import click

import abctk.cli_tool as ct
from . import core


@click.command()
@click.option(
    "-i", "--input", "--source", "source_type",
    type = click.Choice(
        choices = ("stdin", "filelist"),
        case_sensitive = False
    ),
    default = "stdin",
    help = """
        \b
        Designating your data source. 
        - `stdin' means that input Keyaki trees are provided directry from STDIN.
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
@click.pass_context
def cmd_main(
    ctx: click.Context,
    source_type: str,
    destination: typing.Optional[pathlib.Path],
    can_overwrite: bool, 
) -> typing.NoReturn:
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
    # Prepare the destination folder
    # ================
    dest_folder: pathlib.Path
    if destination:
        if destination.is_dir():
            # Check if the folder is empty or not
            pass
        else:
            destination.mkdir(parents = True)
        # === END IF ===
        dest_folder = destination
    else:
        dest_folder = ct.create_folder_time("result_") 
    # === END IF ===

    # ================
    # Conversion
    # ================
    if source_type == "filelist":
        flist: ct.FileList = ct.FileList.from_file_list(sys.stdin)

        import multiprocessing as mp
        import tqdm

        proc_num: int = CONFIG["max_process_num"]
        with mp.Pool(processes = proc_num) as pool:
            logger.info(f"Number of processes: {proc_num}")

            flist_dest_expanded: typing.List[
                typing.Tuple[pathlib.Path, pathlib.Path, int]
            ] = list(
                (src, dest_folder / fn, os.path.getsize(src)) 
                for src, fn 
                in flist.iterate_truncating_commonprefix()
            )
            files_total_size: int = sum(
                map(lambda x: x[2], flist_dest_expanded)
            )
            
            jobs = pool.imap_unordered(
                __conv_file_wrapper,
                flist_dest_expanded
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
    elif source_type == "stdin":
        _ = core.convert_keyaki_to_abc(
            f_src = sys.stdin,
            f_dest = sys.stdout,
            src_name = "<STDIN>",
            dest_name = "<STDOUT>",
        )
    else:
        logger.error(
            "Invalid CLI option: `source_type' must be either `stdin` or `filelist', "
            f"but {source_type} is given."
        )
        raise ValueError()
    # === END IF ===
# === END ===

def __conv_file_wrapper(
    arg_tuple: typing.Tuple[pathlib.Path, pathlib.Path, int],
) -> typing.Tuple[int, int]:
    return (
        core.convert_keyaki_file_to_abc(arg_tuple[0], arg_tuple[1]),
        arg_tuple[2]
    )
# === END ===