import typing
import pathlib
import logging
logger = logging.getLogger(__name__)

from . import misc

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

SUBDIRS: typing.Dict[str, pathlib.Path] = {
    "source":                pathlib.Path("source"),
    "treebank_mod/all":      pathlib.Path("treebank_mod/all"),
    "treebank_mod/train":    pathlib.Path("treebank_mod/train"),
    "treebank_mod/test":     pathlib.Path("treebank_mod/test"),
    "vocab":                 pathlib.Path("vocabulary"),
}

FILES: typing.Dict[str, pathlib.Path] = {
    "all.psd":          SUBDIRS["source"] / "all.psd",
    "train.psd":        SUBDIRS["source"] / "train.psd",
    "test.psd":         SUBDIRS["source"] / "test.psd",
    "head_tags.txt":    SUBDIRS["vocab"] / "head_tags.txt",
    "tokens.txt":       SUBDIRS["vocab"] / "tokens.txt",
    "non_padded_ns":    SUBDIRS["vocab"] / "non_padded_namespaces.txt",

    "traindata":        SUBDIRS["treebank_mod/train"] / "traindata.json",
    "testdata":         SUBDIRS["treebank_mod/test"] / "testdata.json",
    "trainer_settings":     pathlib.Path("trainer_settings.jsonnet"),
    "config_parser_abc":    pathlib.Path("config_parser_abc.json"),
}

def prepare_ml_data(
    source_trees: typing.TextIO,
    config: typing.Dict[str, typing.Any],
    dir_temp: pathlib.Path,
    dir_output: pathlib.Path,
) -> None:
    logger.info("The core preparation procedure `prepare_ml_data' is called")

    # =========================
    # 0. Prepare Subdirectories
    # =========================

    for fd in SUBDIRS.values():
        fd_temp = dir_temp / fd
        fd_temp.mkdir(parents = True, exist_ok = True)
        logger.debug(
            f"The subfolder {fd} of the temporary workspace is created at {fd_temp.absolute()}"
        )

        fd_output = dir_output / fd
        fd_output.mkdir(parents = True, exist_ok = True)
        logger.debug(
            f"The subfolder {fd} of the output directory is created at {fd_output.absolute()}"
        )
    # === END FOR fd ===

    # =========================
    # 1. Divide trees to the training / test sets
    # =========================
    with open(dir_temp / FILES["all.psd"],
        mode = "w"
    ) as h_treebank_all, open(dir_temp / FILES["train.psd"],
        mode = "w"
    ) as h_treebank_train, open(dir_temp / FILES["test.psd"],
        mode = "w"
    ) as h_treebank_test:
        logger.debug(
            f"The streams all.psd, train.psd and test.psd are opened at {dir_temp}"
        )

        # read each tree from STDIN
        for line in source_trees:
            if _get_rand() < config["train_test_ratio"]: # TODO: rewrite
                h_treebank_train.write(line)
            else:
                h_treebank_test.write(line)
            # === END IF ===

            h_treebank_all.write(line)
        # === END FOR line ===
    # === END WITH h_treebank_all, h_treebank_train, h_treebank_test ===
    logger.info(
        "Trees have been divided into training and testing ones"
    )

    # =========================
    # 2. Digest the separated treebanks and collect info
    # =========================
    treebank_mod_list: typing.Dict[str, misc.ModderSettings] = {
        "all": misc.create_mod_treebank(
            dir_temp / FILES["all.psd"],
            dir_temp / SUBDIRS["treebank_mod/all"],
            mode = "train",
        ),
        "train": misc.create_mod_treebank(
            dir_temp / FILES["train.psd"],
            dir_temp / SUBDIRS["treebank_mod/train"],
            mode = "train",
        ),
        "test": misc.create_mod_treebank(
            dir_temp / FILES["test.psd"],
            dir_temp / SUBDIRS["treebank_mod/test"],
            mode = "test",
        )
    }

    # =========================
    # 3. Configure the vocabulary folder
    # =========================
    with open(
        dir_temp / FILES["head_tags.txt"],
        mode = "w"
    ) as h_headtags:
        h_headtags.write("@@UNKNOWN@@\n")
        for entry in treebank_mod_list["all"].targets:
            h_headtags.write(entry)
            h_headtags.write("\n")
        # === END FOR entry ===
    # === END with h_headtags ===

    with open(
        dir_temp / FILES["non_padded_ns"],
        mode = "w"
    ) as _:
        pass
    # === END WITH _ ===

    with open(
        dir_temp / SUBDIRS["treebank_mod/all"] / "words.txt",
        mode = "r"
    ) as h_all_tokens, open(
        config["trainer_settings"]["model"]["text_field_embedder"]["token_embedders"]["tokens"]["pretrained_file"],
        mode = "r"
    ) as h_wvect, open(
        dir_temp / FILES["tokens.txt"],
        mode = "w"
    ) as h_voc_tokens:
        wbag = set(
            map(
                lambda x: x.split()[0],
                h_all_tokens
            )
        )
        wbag.update(
            map(
                lambda x: x.split()[0],
                h_wvect,
            )
        )
        
        h_voc_tokens.write("@@UNKNOWN@@\n")
        for w in wbag:
            h_voc_tokens.write(w)
            h_voc_tokens.write("\n")
    # === END with h_tokens ===



    # =========================
    # 4. Make the trainer config
    # =========================
    import json 

    with open(
        dir_temp / FILES["trainer_settings"],
        "w"
    ) as h_jsonnet:
        # TODO: check if the entity vector exists
        json.dump(
            dict(
                **config["trainer_settings"],
                vocabulary = {
                    "directory_path": SUBDIRS["vocab"],
                },
                train_data_path = SUBDIRS["treebank_mod/train"] / "traindata.json",
                validation_data_path = SUBDIRS["treebank_mod/test"] / "testdata.json",
            ),
            h_jsonnet,
            default = str,
        )
    # === END WITH h_jsonnet ===

    # =========================
    # 5. Dump parser settings
    # =========================
    with open(
        dir_temp / FILES["config_parser_abc"],
        "w"
    ) as h_parserconf:
        json.dump(
            vars(treebank_mod_list["train"]),
            h_parserconf,
            default = str
        )
    # === END WITH h_parserconf ===

    # ===========================
    # 6. Export necessary files to the output folder
    # ===========================
    import shutil
    for f in (
        "head_tags.txt", "tokens.txt", "non_padded_ns",
        "traindata", "testdata",
        "trainer_settings",
        "config_parser_abc",
    ):
        file_path = FILES[f]
        shutil.copy(dir_temp / file_path, dir_output / file_path)

    logger.info("The core preparation procedure `prepare_ml_data' has ended in success")
# === END ===