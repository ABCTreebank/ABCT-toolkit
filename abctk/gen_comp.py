from importlib.resources import path
import logging
import shutil
logger = logging.getLogger(__name__)
import pathlib
import typing

import subprocess

import abctk.config
import abctk.cli_typer.renumber

# ========================
# Conversion Procedures
# ========================
def convert_io(
    f_src: typing.TextIO,
    f_dest: typing.TextIO,
    temp_folder: typing.Union[str, pathlib.Path],
    src_name: typing.Any = "<INPUT>",
    dest_name: typing.Any = "<OUTPUT>",
    conf: typing.Dict[str, typing.Any] = abctk.config.CONF_DEFAULT,
    log_prefix: typing.Union[None, str, pathlib.Path] = None,
    **kwargs
) -> int:
    basename = pathlib.Path(src_name).stem

    logger.info(
        f"Commence a comparative conversion on the file/stream {src_name}"
    )

    if isinstance(temp_folder, pathlib.Path):
        temp_folder = str(temp_folder.resolve())

    command_select = f"""
    {conf["bin-sys"]["ruby"]} {conf["runtimes"]["unsimplify-ABC-tags"]} - 
| {conf["bin-sys"]["munge-trees"]} -w
| {conf["bin-sys"]["awk"]} -e '/typical|関係節|連用節/'
| {conf["bin-sys"]["sed"]} -e 's/(COMMENT {{.*}})//g'
"""
    if log_prefix:
        command_select += f" | tee {log_prefix}-00-selected.psd"
        logger.info(
            f"The trace file of Step 1 will be saved at {log_prefix}-00-selected.psd"
        )

    command_select = command_select.strip().replace("\n", "")

    logger.info(
        f"Step 1: Command to be executed: {command_select}"
    )
    
    temp_file_name_selected = pathlib.Path(
        f"{temp_folder}/{basename}-00-selected.psd"
    )

    with open(temp_file_name_selected, "w") as f_temp:
        proc = subprocess.Popen(
            command_select,
            shell = True,
            stdin = f_src,
            stdout = f_temp,
        )
        proc.wait()

        return_code = proc.returncode

        if return_code: # <> 0
            logger.warning(f"warning: conversion failed: {src_name}")
        else:
            logger.info(
                f"Successfully complete Step 1. "
                f"The outcome is stored at `{temp_file_name_selected}'."
            )
        # === END IF ===

    # 2. renumber trees
    logger.info(
        f"Step 2: renumber trees"
    )

    temp_file_name_renumbered = pathlib.Path(
        f"{temp_folder}/{basename}-10-renum.psd"
    )
    abctk.cli_typer.renumber.cmd_from_file(
        source_path = temp_file_name_selected,
        dest_path = temp_file_name_renumbered,
        fmt = "{id_orig.number}_{name_random}"
    )
    if log_prefix:
        shutil.copy(
            temp_file_name_renumbered,
            f"{log_prefix}-10-renum.psd"
        )
        logger.info(
            f"The trace file of Step 2 is saved at {log_prefix}-10-selected.psd"
        )

    logger.info(
        f"Successfully complete Step 2. "
        f"The outcome is stored at `{temp_file_name_renumbered}'."
    )

    # 3. remove #role=none & move
    if log_prefix:
        command = f"""
{conf["bin-sys"]["sed"]} -e 's/#role=none//g'
| tee {log_prefix}-20-remrole.psd
| {conf["bin-custom"]["tsurgeon_script"]} {conf["runtimes"]["move-comparative"]}
| tee {log_prefix}-30-move.psd
    """
    else:
        command = f"""
{conf["bin-sys"]["sed"]} -e 's/#role=none//g'
| {conf["bin-custom"]["tsurgeon_script"]} {conf["runtimes"]["move-comparative"]}
    """

    command = command.strip().replace("\n", "")

    logger.info(
        f"Steps 3 - 4: remove #role=none and move comp-related nodes: {command}"
    )

    with (
        open(temp_file_name_renumbered) as f_renum,
    ):
        proc = subprocess.Popen(
            command,
            shell = True,
            stdin = f_renum,
            stdout = f_dest,
        )
        proc.wait()

        return_code = proc.returncode

        if return_code: # <> 0
            logger.warning(f"warning: conversion failed: {src_name}")
        else:
            logger.info(
                f"Successfully complete Steps 3 - 4. "
                f"The outcome is stored at `{dest_name}'."
            )
        # === END IF ===
    return return_code
# === END ===

def convert_file(
    src: pathlib.Path, 
    dest: pathlib.Path,
    temp_folder: typing.Union[str, pathlib.Path],
    conf: typing.Dict[str, typing.Any] = abctk.config.CONF_DEFAULT,
    log_prefix: typing.Union[None, str, pathlib.Path] = None,
    **kwargs
) -> int:
    dest_file_name_bare = dest.stem
    dest_name_bare: pathlib.Path = dest.parent / dest_file_name_bare
    dest_path_abs: str = str(dest_name_bare) + "-comp_moved.psd"

    # temp_folder = None
    # try:
    #     temp_folder = tempfile.TemporaryDirectory(prefix = "ABCT-gen-comp_")
    #     logger.info(
    #         f"Temporary folder created at: {temp_folder}"
    #     )

    with open(src, "r") as h_src, open(dest_path_abs, "w") as h_dest:
        res = convert_io(
            h_src, h_dest,
            temp_folder = temp_folder,
            src_name = src, 
            dest_name = dest_path_abs,
            conf = conf,
            log_prefix = (
                f"{log_prefix}/{dest_file_name_bare}"
                if log_prefix else None
            ),
            # TODO: more flexible log_prefix
            **kwargs
        )
    # === END WITH h_src, h_dest ===
    # finally:
    #     if temp_folder:
    #         temp_folder.cleanup()
    #         logger.info(
    #             f"The temporary folder has been cleaned up"
    #         )

    return res
# === END ===    
