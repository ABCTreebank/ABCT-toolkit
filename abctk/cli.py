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
    "-l", "--log-level", "log_level",
    type = str,
    default = logging.WARNING,
)
@click.option(
    "--logfile", "logfile",
    type = click.Path(
        exists = False, 
        file_okay = True,
        dir_okay = False,
        writable = True
    ),
    default = None,
    help = """
        Path to the log file. No output if not set.
    """
)
@click.pass_context
def cmd_main(
    ctx: click.Context,
    user_config: typing.TextIO,
    log_level: typing.Union[int, str],
    logfile: pathlib.Path
):
    ctx.ensure_object(dict)

    # ====================
    # Configure logging
    # ====================
    # TODO: is this working?
    if isinstance(log_level, int):
        if log_level > 0:
            pass
        else:
            logging.error("Value not in the range for the --log-level option")
            raise ValueError()
        # === END IF ===
    elif isinstance(log_level, str):
        if log_level.isdigit:
            log_level = int(log_level)
        else:
            log_level = str.upper(log_level)
        # === END IF ===
    else:
        logging.error("Wrong type for the --log-level option")
        raise TypeError()
    # === END IF ===

    if logfile:
        logging.basicConfig(
            filename = logfile,
            level = log_level,
        )
        logger.info("Verbose log enabled")
    else:
        logger.setLevel(log_level)
    # === END IF ===

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