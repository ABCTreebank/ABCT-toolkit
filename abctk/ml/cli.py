import typing
import pathlib

import sys
import click

from . import misc
import abctk.cli_tool as ct

def _get_rand() -> float:
    """
        Generate a random float number ranging from 0 to 100.
        Returns
        -------
        num : float
            A random float number.
    """
    import random

    return random.uniform(0, 100)
# === END ===

@click.command()
@click.option(
    "-o", "--output", "--to", "--destination", "destination",
    type = click.Path(file_okay = False, dir_okay = True),
    help = """
        Path to a folder that stores the resulting files.
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
    destination: typing.Optional[pathlib.Path],
    can_overwrite: bool,
):
    r"""
        Generate a parser model (and auxiliariy files) from a treebank.

        The source ABCTreebank must be formatted beforehand as one-line trees
        and given to STDIN.
    """
    CONFIG_ML: typing.Dict[str, typing.Any] = ctx.obj["CONFIG"]["ml"]

    # =========================
    # 0. Prepare the output folder
    # =========================
    dest_folder_root: pathlib.Path 
    if destination:
        dest_folder_root = destination
        # TODO: check if it's empty
    else:
        dest_folder_root = ct.create_folder_time("result_", to_make = True) 
    # === END IF ===

    dest_folders: typing.Dict[str, pathlib.Path] = {
        "root": dest_folder_root,
        "source": dest_folder_root / "source",
        "treebank_mod/all": dest_folder_root / "treebank_mod/all",
        "treebank_mod/train": dest_folder_root / "treebank_mod/train",
        "treebank_mod/test": dest_folder_root / "treebank_mod/test",
        "wvect": dest_folder_root / "wvect",
        "model": dest_folder_root / "model",
    }

    for v in dest_folders.values():
        v.mkdir(parents = True, exist_ok = True)
    # === END FOR v ===

    # =========================
    # 1. Divide trees to the training / test sets
    # =========================
    
    with open(
        dest_folders["source"] / "all.psd",
        mode = "w"
    ) as h_treebank_all, open(
        dest_folders["source"] / "training.psd",
        mode = "w"
    ) as h_treebank_train, open(
        dest_folders["source"] / "testing.psd",
        mode = "w"
    ) as h_treebank_test:
        # read each tree from STDIN
        for line in sys.stdin:
            if _get_rand() < CONFIG_ML["train_test_ratio"]:
                h_treebank_train.write(line)
            else:
                h_treebank_test.write(line)
            # === END IF ===

            h_treebank_all.write(line)
        # === END FOR line ===

    # === END WITH h_treebank_all, h_treebank_train, h_treebank_test ===
    
    # =========================
    # 2. Digest the separated treebanks and collect info
    # =========================
    digested_treebank: typing.Dict[str, misc.ModderSettings] = {
        "all": misc.create_mod_treebank(
            dest_folders["source"] / "all.psd",
            dest_folders["treebank_mod/all"],
            mode = "train",
        ),
        "train": misc.create_mod_treebank(
            dest_folders["source"] / "training.psd",
            dest_folders["treebank_mod/train"],
            mode = "train",
        ),
        "test": misc.create_mod_treebank(
            dest_folders["source"] / "testing.psd",
            dest_folders["treebank_mod/test"],
            mode = "test",
        )
    }

    # =========================
    # 3. Configure the word-vector directory
    # =========================
    # Copy the directory to the new folder 
    import shutil

    shutil.copytree(
        CONFIG_ML["runtimes"]["wvect"],
        dest_folders["wvect"],
        dirs_exist_ok = True,
    )

    # Overwrite the vocabulary list
    with open(
        dest_folders["wvect"] / "head_tags.txt", 
        mode = "w"
    ) as h_headtags:
        h_headtags.write("@@UNKNOWN@@\n")
        for entry in digested_treebank["all"].targets:
            h_headtags.write(entry)
            h_headtags.write("\n")
        # === END FOR entry ===
    # === END with h_headtags ===

    # =========================
    # 4. Configure the trainer
    # =========================
    import allennlp.common.params as allp
    import allennlp.common.util as allu
    import allennlp.commands.train as allct
    allu.import_submodules("depccg.models.my_allennlp")

    trainer_settings: allp.Params = allp.Params.from_file(
        CONFIG_ML["runtimes"]["trainer_settings"],
        ext_vars = {
            "vocab": str(dest_folders["wvect"]),
            "train_data": str(
                dest_folders["treebank_mod/train"] / "traindata.json"
            ),
            "test_data": str(
                dest_folders["treebank_mod/test"] / "testdata.json"
            ),
            "gpu": CONFIG_ML["gpu_id"],
        }
    )

    # =========================
    # 5. Dump parser settings
    # =========================
    with open(
        dest_folders["root"] / "config_parser_abc.json",
        "w"
    ) as h_parserconf:
        json.dump(
            vars(digested_treebank["train"]),
            h_parserconf,
            default = str
        )
    # === END WITH ===

    # =========================
    # 6. Execute the trainer
    # =========================
    allct.train_model(
        params = trainer_settings,
        serialization_dir = dest_folders["model"],
    )
# === END ===