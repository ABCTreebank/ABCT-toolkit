import typing
import logging
logger = logging.getLogger(__name__)

import subprocess

import pathlib
import abctk.config as CONF

# ========================
# Runtimer Checking
# ========================

def check_runtimes(
    runtime_dict: typing.Dict[str, typing.Union[str, pathlib.Path]]
) -> int:
    """Check whether the necessary system runtimes exist and are accessible.

        Parameters
        ----------
        runtime_dict : typing.Dict[str, typing.Union[None, str, pathlib.Path]]
            Key-value pairs representing runtimes. 
            The keys are the names of the runtime programs,
            the values are the paths or names, which will be checked against 'shutil.which'.

        Returns
        -------
        int
            0 if the checking succeeds.
            2 (ENOENT) if any of the runtimes is not found.
    """
    import shutil

    # Check required binaries
    bin_sys_not_found = {
        key:pg for key, pg in runtime_dict.items()
        if not (pg and shutil.which(pg))
    }

    if bin_sys_not_found:
        import sys
        for key, pg in bin_sys_not_found.items():
            logger.error(f"Runtime not found: {key}")
            sys.stdout.write(
                "[ERROR] Runtime not found: "
                f"""{key} (designated as {pg})\n"""
            )
        # === END FOR key, pg ===
        sys.stdout.write(
            """To obtain the necessary runtimes:
- m4: install with your system package manager
- sed: install with your system package manager
- java: install with your system package manager
"""
        )
        return 2 # ENOENT
    else:
        return 0 # Successful
    # === END IF ===
# === END ===

# ========================
# Conversion Procedures
# ========================
def convert_keyaki_to_abc(
    f_src: typing.TextIO,
    f_dest: typing.TextIO,
    src_name: typing.Any = "<INPUT>",
    dest_name: typing.Any = "<OUTPUT>",
    conf: typing.Dict[str, typing.Any] = CONF.CONF_DEFAULT,
    log_prefix: typing.Union[None, str, pathlib.Path] = None,
) -> int:
    logger.info(
        f"Commence a Keyaki-to-ABC conversion on the file/stream {src_name}"
    )

    command: str

    if log_prefix:
        logger.info(
            f"Intermediate files will be stored at {log_prefix}-*.psd"
        )
        command = f"""{conf["bin-custom"]["tsurgeon_script"]} {conf["runtimes"]["pretreatments"]} \
| tee {log_prefix}-b2psg-00pre.psd \
| {conf["bin-custom"]["tsurgeon_script"]} {conf["runtimes"]["dependency"]} \
| tee {log_prefix}-b2psg-10dep.psd \
| {conf["bin-custom"]["tsurgeon_script"]} {conf["runtimes"]["dependency-post"]} \
| tee {log_prefix}-b2psg-15deppost.psd \
| {conf["bin-sys"]["sed"]} -f {conf["runtimes"]["simplify-tag"]} \
| tee {log_prefix}-b2psg-30simp.psd \
| {conf["bin-custom"]["abc-relabel"]}"""
    else:
        logger.info(
            f"Intermediate files will not be generated"
        )
        command = f"""{conf["bin-custom"]["tsurgeon_script"]} {conf["runtimes"]["pre-relabel"]} \
| {conf["bin-sys"]["sed"]} -f {conf["runtimes"]["simplify-tag"]} \
| {conf["bin-custom"]["abc-relabel"]}"""
    # === END IF ===

    logger.info(
        f"Command to be executed: {command}"
    )
    
    proc = subprocess.Popen(
        command,
        shell = True,
        stdin = f_src,
        stdout = f_dest,
    )
    proc.wait()

    return_code = proc.returncode

    if return_code: # <> 0
        logger.warning(f"warning: conversion failed: {src_name}")
    else:
        logger.info(
            f"Successfully complete the Keyaki-to-ABC conversion on the file `{src_name}'. "
            f"The outcome is stored at `{dest_name}'."
        )
    # === END IF ===

    return return_code
# === END ===

def convert_keyaki_file_to_abc(
    src: pathlib.Path, 
    dest: pathlib.Path,
    conf: typing.Dict[str, typing.Any] = CONF.CONF_DEFAULT,
    log_prefix: typing.Union[None, str, pathlib.Path] = None,
) -> int:
    dest_name_bare: pathlib.Path = dest.parent / dest.stem
    dest_path_abs: str = str(dest_name_bare) + "-b2psg.psd"

    with open(src, "r") as h_src, open(dest_path_abs, "w") as h_dest:
        res = convert_keyaki_to_abc(
            h_src, h_dest,
            src, dest_path_abs,
            conf = conf,
            log_prefix = log_prefix,
        )
    # === END WITH h_src, h_dest ===

    return res
# === END ===    
