import typing
import pathlib

import sys
import logging
import fs
logger = logging.getLogger(__name__)

import typer

import abctk.config as CONF

app = typer.Typer()

@app.callback()
def cmd_main(
    ctx: typer.Context,
    user_configs: typing.List[typer.FileText] = typer.Option(
        [],
        "-c", "--config",
        help = """
            Path to a configuration file in the YAML format.
            More than one configuration file can be specified.
            Latter ones override former ones.
        """
    ),
    root_stream_log_level: int = typer.Option(
        logging.WARNING,
        "-l", "--root-stream-log-level",
        min = 1,
        help = """
            The log level of the root logger, which is directed to STDERR.

            The level is specified by a positive integer.
            Refer to the following doc to find the correspondent numbers of log levels:
            https://docs.python.org/3/howto/logging.html#logging-levels
        """
    ),
    logfiles: typing.List[typer.FileTextWrite] = typer.Option(
        [],
        "--logfile",
        lazy = True,
        help = """
            Additional log handler set to INTEGER RANGE level which is directed to FILE.
            Multiple handlers are allowed.
        """
    )
):
    """
    A CLI toolkit to generate and manupilate the ABC Treebank.
    \f

    Arguments
    ---------
    ctx
        The context argument that is used by Typer.
    user_configs
        List of streams of configuration files. 
        Each file is opened beforehand 
        and will be closed properly by Typer.
    root_stream_log_level
        The log level for the root logger. Specified in integer.
    logfiles
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


@app.command("version")
def cmd_ver():
    """
    Show the version of this application.
    """
    from abctk.version import pprint_version_info
    typer.echo(pprint_version_info())
# === END ===

def _represent_PurePath(dumper, instance: pathlib.PurePath):
    return dumper.represent_str(str(instance))
# === END ===

@app.command("show-config")
def cmd_show_conf(ctx: typer.Context):
    """
    Dump the configuration recognized by the application.
    For debugging.
    """
    from ruamel.yaml import YAML

    yaml = YAML()
    yaml.representer.add_multi_representer(
        pathlib.PurePath, 
        _represent_PurePath
    )
    
    yaml.dump(ctx.obj["CONFIG"], sys.stdout)
# === END ===

@app.command("dic")
def cmd_dic():
    """
    List special lexical entries in the ABC Treebank.
    """
    import abctk.dic
    abctk.dic.dump_dic_as_csv(sys.stdout)
# === END ===

from . import crypt
app.add_typer(crypt.app, name = "crypt")

from . import gen_comp
app.command("gen-comp")(gen_comp.cmd_main)

from . import conv
app.command("conv")(conv.cmd_main)

from . import tweak
app.add_typer(tweak.app, name = "tweak")

from . import to_jigg
app.add_typer(to_jigg.app, name = "to-jigg")

from . import renumber
app.add_typer(renumber.app, name = "renum")

from . import ccg2lambda
app.add_typer(ccg2lambda.app, name = "c2l")

@app.command("interp-parse-result")
def cmd_interp_parse():
    """
    Convert sentences parsed by AllenNLP/depccg into trees in the Penn Treebank format.

    Data are exchanged through STDIN/STDOUT.
    """

    from abctk.io.depccg_parse_output import load_ABC_parsed_jsonl_psd
    import abctk.io.nltk_tree as nt

    trees_with_ID = load_ABC_parsed_jsonl_psd(sys.stdin)

    sys.stdout.writelines(
        nt.flatten_tree_with_ID(ID, tree) + "\n"
        for ID, tree in trees_with_ID
    )

@app.command("ml-prep")
def cmd_ml_prep(
    source_path: pathlib.Path = typer.Argument(
        ...,
        help = """
        The path to the ABC Treebank.
        """
    ),
    dest_path: pathlib.Path = typer.Argument(
        ...,
        help = """
        The destination.
        """
    ),
):
    """
    Generate necessary ingredients for depccg training.
    """
    import abctk.io.nltk_tree as nt
    import abctk.ml.gen as g
    tb = list(nt.load_ABC_psd(source_path))

    ds = g.DepCCGDataSet.from_ABC_NLTK_trees(
        tb,
    )

    with fs.open_fs(str(dest_path), create = True) as folder:
        ds.dump(
            folder, 
            add_seen_rules = True
        )

@app.command("parse")
def cmd_parse():
    """
    Parse sentences.
    """
    pass

@app.command("norm-cat")
def cmd_normalize_category():
    """
    Normalize ABC categories.
    """
    pass

