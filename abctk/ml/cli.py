import typing
import logging
logger = logging.getLogger(__name__)

import pathlib

import sys
import click

from . import core
import abctk.cli_tool as ct

@click.group()
@click.pass_context
def cmd_main(ctx): pass

@cmd_main.command("prepare")
@click.option(
    "-o", "--output", "--to", "--destination", "destination",
    type = click.Path(file_okay = False, dir_okay = True),
    help = """
        Path to a folder that stores the resulting files.
        Default to `./ml_prepared_(timestamp)`.
    """
)
@click.option(
    "--overwrite/--no-overwrite", "can_overwrite",
    default = False,
)
@click.option(
    "--leave-temp", "if_leave_temp",
    default = False,
)
@click.pass_context
def cmd_prepare(
    ctx: click.Context,
    destination: typing.Optional[pathlib.Path],
    can_overwrite: bool,
    if_leave_temp: bool,
):
    r"""
        Generate a parser model (and auxiliariy files) from a treebank.

        The source ABCTreebank must be formatted beforehand as one-line trees
        and given to STDIN.
    """
    try: 
        # =========================
        # 1. Prepare the intermediate temp folder
        # =========================
        import tempfile 
        temp_folder: pathlib.Path = pathlib.Path(
            tempfile.mkdtemp(prefix = "abctk.ml.cli.prepare-")
        )
        logger.info(f"Create a temporary folder at {temp_folder}")

        # =========================
        # 2. Prepare the output folder
        # =========================
        dest_folder_root: pathlib.Path 
        if destination:
            dest_folder_root = destination
            # TODO: check if it's empty
        else:
            dest_folder_root = ct.create_folder_time(
                "ml_prepared_", to_make = True
            ) 
        # === END IF ===

        core.prepare_ml_data(
            source_trees = sys.stdin,
            config = ctx.obj["CONFIG"]["ml"],
            dir_temp = temp_folder,
            dir_output = dest_folder_root
        )
    finally:
        if temp_folder and temp_folder.is_dir():
            if if_leave_temp:
                msg: str = f"Temporary file kept at {temp_folder}"
                sys.stderr.write(msg)
                logger.info(msg)
            else:
                pass # delete tempfolder
            # === END IF ===
        else:
            pass
        # === END IF ===
    # === END TRY ===
# === END ===

@cmd_main.command("train")
@click.argument(
    "source",
    type = click.Path(file_okay = False, dir_okay = True, exists = True)
)
@click.option(
    "-o", "--output", "--to", "--destination", "destination",
    type = click.Path(
        file_okay = False, 
        dir_okay = True, 
        resolve_path = True
    ),
    help = """
        Path to a folder that stores the resulting model.
        Default to `./ml_(timestamp)`.
    """
)
@click.option(
    "--overwrite/--no-overwrite", "can_overwrite",
    default = False,
)
def cmd_train(
    source: pathlib.Path, 
    destination: pathlib.Path,
    can_overwrite: bool,
):
    # =========================
    # Prepare the output folder
    # =========================
    source_path_name = pathlib.Path(source).name
    dest_folder_root: pathlib.Path 
    if destination:
        dest_folder_root = destination
        # TODO: check if it's empty
    else:
        dest_folder_root = ct.create_folder_time(
            f"ml_{source_path_name}_", to_make = True
        ) 
    # === END IF ===

    import os 
    os.chdir(source)

    import allennlp.common.params as allp
    import allennlp.common.util as allu
    import allennlp.commands.train as allct
    allu.import_submodules("depccg.models.my_allennlp")

    allct.train_model(
        params = allp.Params.from_file(core.FILES["trainer_settings"]),
        serialization_dir = dest_folder_root
    )
# === END ===