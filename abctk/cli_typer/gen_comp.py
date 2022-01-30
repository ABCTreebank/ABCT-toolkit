import functools
import multiprocessing as mp
import logging
import tempfile
logger = logging.getLogger(__name__)

import os
import pathlib
import typing
import sys

import fs
from tqdm import tqdm
import typer

from abctk.config import check_runtimes
import abctk.gen_comp

class FileConversionArgs(typing.NamedTuple):
    src: typing.Union[str, pathlib.Path]
    dest: typing.Union[str, pathlib.Path]
    temp_folder: typing.Union[str, pathlib.Path]
    file_size: int
    log_prefix: typing.Union[str, pathlib.Path, None]

def _conv_file_wrapper(
    args: FileConversionArgs,
    f: typing.Callable,
    conf: dict,
    **kwargs,
) -> typing.Tuple[int, int]:
    return (
        f(
            conf = conf, 
            src = args.src, 
            dest = args.dest,
            temp_folder = args.temp_folder,
            log_prefix = args.log_prefix,
            **kwargs,
        ),
        args.file_size,
    )
# === END ===

def cmd_main(
    ctx: typer.Context,
    source_path: pathlib.Path = typer.Argument(
        ...,
        allow_dash = True,
    ),
    dest_path: pathlib.Path = typer.Argument(
        ...,
        allow_dash = True,
    ),
    force_dir: bool = typer.Option(
        False,
        "--force-dir/--no-force-dir",
    ),
    glob: typing.List[str] = typer.Option(
        ["*.psd"],
        "--glob", "-g",
    ),
    intermediate_dir: typing.Optional[pathlib.Path] = typer.Option(
        None,
        "--intermediate-dir", "-i",
        allow_dash = False,
        file_okay = False,
        dir_okay = True,
    )
):
    """
    Tweak ABC trees wrt comparative.
    """
    CONF = ctx.obj["CONFIG"]

    # 0. Check runtime
    check_error = check_runtimes(
        {
            k:v for k, v in CONF["bin-sys"].items()
            if k in ("m4", "sed", "java", "ruby", "awk", "munge-trees")
        }
    )
    if check_error: 
        raise RuntimeError("Some runtime components are missing")
    else:
        logger.info("Runtimes ensured")

    # 1. Load trees
    filelist: typing.List[pathlib.Path]

    # ensure interemedieate folders:
    if intermediate_dir is not None:
        os.makedirs(intermediate_dir, exist_ok = True)

    if source_path.name == "-":
        raise NotImplementedError

        # The source is STDIN
        if dest_path.name == "-":
            abctk.gen_comp.convert_file(
                f_src = sys.stdin,
                f_dest = sys.stdout,
            )
            cr.convert_keyaki_to_abc(
                f_src = sys.stdin,
                f_dest = sys.stdout,
                conf = CONF,
                log_prefix = (intermediate_dir / "output") if intermediate_dir else None,
            )
        else:
            with open(dest_path, "w") as h_dest:
                cr.convert_keyaki_to_abc(
                    f_src = sys.stdin,
                    f_dest = h_dest,
                    conf = CONF,
                    log_prefix = (intermediate_dir / "output") if intermediate_dir else None,
                )
    elif not force_dir and not source_path.is_dir():
        raise NotImplementedError

        # source_path is a file
        if dest_path.name == "-":

            with open(source_path) as h_src:
                cr.convert_keyaki_to_abc(
                    f_src = h_src,
                    f_dest = sys.stdout,
                    conf = CONF,
                    log_prefix = (intermediate_dir / source_path.stem) if intermediate_dir else None,
                )
        else:
            abctk.gen_comp.convert_treebank(
                src = source_path,
                dest = dest_path,
                conf = CONF,
                log_prefix = (intermediate_dir / source_path.stem) if intermediate_dir else None,
            )
    else:
        # source_path is a folder (multiple files)
        logger.info(f"Source folder: {source_path}")

        # ensure that dest_path is a folder
        if dest_path.exists() and not dest_path.is_dir():
            raise IOError(f"{dest_path} must be a folder")

        with fs.open_fs(str(source_path)) as h_folder:
            filelist = list(
                pathlib.Path(path_str)
                for path_str in h_folder.walk.files(
                    path = "", # get the relative path
                    filter = glob
                )
            )

        # ensure the output folders
        for filepath in filelist:
            parent = filepath.parent
            (dest_path / parent).mkdir(
                parents = True,
                exist_ok = True,
            )
            if intermediate_dir:
                (intermediate_dir / parent).mkdir(
                    parents = True,
                    exist_ok = True,
                )

        # Write files to a folder

        # create temporary folder
        with tempfile.TemporaryDirectory(prefix = "abctk-gen-comp_") as t_folder:

            proc_num = CONF["max_process_num"]
            with mp.Pool(processes = proc_num) as pool:
                logger.info(f"Number of processes: {proc_num}")

                flist_dest_expanded = tuple(
                    FileConversionArgs(
                        src = source_path / filepath,
                        dest = dest_path / filepath,
                        temp_folder = t_folder,
                        file_size = os.path.getsize(source_path / filepath),
                        log_prefix = intermediate_dir,
                    )
                    for filepath in filelist
                )

                files_total_size: int = sum(
                    x.file_size for x in flist_dest_expanded
                )
                
                logger.info(
                    f"# of the files to be processed: {len(flist_dest_expanded)}, "
                    f"The total size of the files to be processed: {files_total_size}"
                )

                # Create jobs
                jobs = pool.imap_unordered(
                    functools.partial(
                        _conv_file_wrapper,
                        f = abctk.gen_comp.convert_file,
                        conf = CONF,
                    ),
                    flist_dest_expanded,
                )

                with tqdm(
                    total = files_total_size, 
                    unit = "B",
                    unit_scale = True,
                    unit_divisor = 1024
                ) as pb:
                    pb.write("Tweaking on comparative nodes:") 
                    for _return_code, src_size in jobs:
                        pb.update(src_size)
                # === END WITH pb ===