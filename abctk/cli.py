import typing
import pathlib

import sys
import logging
logger = logging.getLogger(__name__)

import click

import abctk.config as CONF

@click.group(name = "ABC Treebank Toolkit")
@click.option(
    "-c", "--config", "user_config",
    type = click.File(mode = "r"),
    help = "Path to the user custom option file (in the YAML format)."
)
@click.option(
    "-l", "--root-stream-log-level", "root_stream_log_level",
    type = click.IntRange(min = 1),
    default = logging.WARNING,
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
        Path to the log file. No output if not set.
    """
)
@click.pass_context
def cmd_main(
    ctx: click.Context,
    user_config: typing.TextIO,
    root_stream_log_level: int,
    logfiles: typing.Iterable[typing.Tuple[int, pathlib.Path]],
):
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
            CONFIG = deepmerge(CONFIG, cu, mode = "merge")
        # === END WITH cu ===
    # === END IF ===

    if user_config:
        CONFIG = deepmerge(CONFIG, user_config, mode = "merge")
    # === END IF ===

    ctx.obj["CONFIG"] = CONFIG
# === END ===

import abctk.conversion.cli as cli_conv
cmd_main.add_command(cli_conv.cmd_main, name = "conv")

import abctk.ml.cli as cli_ml
cmd_main.add_command(cli_ml.cmd_main, name = "ml")

import abctk.parsing.cli as cli_parse
cmd_main.add_command(cli_parse.cmd_main, name = "parse")

@cmd_main.command(
    name = "dic",
    short_help = "list special lexical entries in ABC Treebank"
)
def cmd_dic():
    import abctk.dic
    abctk.dic.dump_dic_as_csv(sys.stdout)
# === END ===

@cmd_main.command(name = "version")
def cmd_ver():
    import abctk
    sys.stdout.writelines(
        (
            abctk.__version__,
            "\n\n"
        )
    )

    import git
    try:
        repo = git.Repo(
            pathlib.Path(__file__).parent / ".."
        )
    except git.InvalidGitRepositoryError:
        pass
    else:
        is_modified: str = "Yes" if repo.is_dirty() else "No"
        r_head = repo.head
        sys.stdout.write(
            rf"""Git Dev Info:
- Location: {r_head.abspath}
- Head: {r_head.ref}@{r_head.commit.hexsha}
- Modified: {is_modified}
"""
        )
    # === END TRY ===
# === END ===

def _represent_PurePath(dumper, instance: pathlib.PurePath):
    return dumper.represent_str(str(instance))
# === END ===

@cmd_main.command(
    name = "show-config",
    short_help = "dump the configurations recognized by the program (for debugging)"
)
@click.pass_context
def cmd_show_conf(ctx: click.Context):
    from ruamel.yaml import YAML

    yaml = YAML()
    yaml.representer.add_multi_representer(
        pathlib.PurePath, 
        _represent_PurePath
    )
    
    yaml.dump(ctx.obj["CONFIG"], sys.stdout)
# === END ===
