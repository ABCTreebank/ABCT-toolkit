import typing
import pathlib

import logging
logger = logging.getLogger(__name__)

import click

import abctk.config as CONF

@click.group(name = "ABC Treebank Toolkit")
@click.option(
    "-c", "--config", "user_configs",
    type = click.File(mode = "r"),
    multiple = True,
    help = """
        Path to a configuration file in the YAML format.
        More than one configuration file can be specified.
        Latter ones override former ones.
    """
)
@click.option(
    "-l", "--root-stream-log-level", "root_stream_log_level",
    type = click.IntRange(min = 1),
    default = logging.WARNING,
    help = """
        The log level of the root logger, which is directed to STDERR.

        The level is specified by a positive integer.
        Refer to the following doc to find the correspondent numbers of log levels:
        https://docs.python.org/3/howto/logging.html#logging-levels
    """
)
@click.option(
    "--logfile", "logfiles",
    type = (
        click.IntRange(min = 1),
        click.Path(
            exists = False, 
            file_okay = True,
            dir_okay = False,
            writable = True
        ),
    ),
    multiple = True,
    help = """
        Additional log handler set to INTEGER RANGE level which is directed to FILE.
        Multiple handlers are allowed.
    """
)
@click.pass_context
def cmd_main(
    ctx: click.Context,
    user_configs: typing.Iterator[typing.TextIO],
    root_stream_log_level: int,
    logfiles: typing.Iterable[typing.Tuple[int, pathlib.Path]],
):
    """A CLI toolkit to generate and manupilate the ABC Treebank.
    \f

    :param ctx: The context argument that is used by Click.
    :param user_configs:
        List of streams of configuration files. 
        Each file is opened beforehand 
        and will be closed properly by Click.
    :param root_stream_log_level:
        The log level for the root logger. Specified in integer.
    :param logfiles:
        List of additional log handlers.
        Each item consists of a tuple of a log level and an output path.
    """
    ctx.ensure_object(dict)

    # ====================
    # Configure logging
    # ====================
    # Adjust the root stream handler
    logger_root = logging.getLogger()
    logger_root.setLevel(root_stream_log_level)
    logging.info(
        f"The log level of the root logger is set to {logger_root.level}"
    )

    # Add file handlers to the root
    for level, hpath in logfiles:
        hd = logging.FileHandler(hpath)
        hd.setLevel(level)
        logger_root.addHandler(hd)
    # === END FOR level, hpath ===

    logger_root.info(
        f"The handler(s) of the root logger is/are: {logging.root.handlers}"
    )

    # ====================
    # Build config
    # ====================
    from dictknife import deepmerge
    import ruamel.yaml
    yaml = ruamel.yaml.YAML()
    import xdg
    import os

    CONFIG: typing.Dict[str, typing.Any] = CONF.CONF_DEFAULT
    path_config_user: pathlib.Path = xdg.xdg_config_home() / "ABCTreebank.yaml"
    if os.path.exists(path_config_user):
        with open(path_config_user, "r") as cu:
            CONFIG = deepmerge(CONFIG, cu, method = "merge")
        # === END WITH cu ===
    # === END IF ===

    for h_cf in user_configs:
        CONFIG = deepmerge(CONFIG, yaml.load(h_cf), method = "merge")
    # === END IF ===

    ctx.obj["CONFIG"] = CONFIG
# === END ===

import abctk.conversion.cli as cli_conv
cmd_main.add_command(cli_conv.cmd_main, name = "conv")

import abctk.parsing.cli as cli_parse
cmd_main.add_command(cli_parse.cmd_main, name = "parse")

import abctk.transform_Keyaki.cli as cli_trans_Keyaki
cmd_main.add_command(
    cli_trans_Keyaki.cmd_main, 
    name = "trans-Keyaki",
)

import abctk.transform_ABC.cli as cli_trans_ABC
cmd_main.add_command(
    cli_trans_ABC.cmd_main,
    name = "trans-ABC"
)