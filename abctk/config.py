import logging
logger = logging.getLogger(__name__)
import importlib.util
import pathlib
import psutil
import typing

import xdg

MODULE = importlib.util.find_spec("abctk")

if MODULE is None: raise RuntimeError
MODULE_PATH = MODULE.submodule_search_locations
if MODULE_PATH is None: raise RuntimeError
DIR_RUNTIME = pathlib.Path(MODULE_PATH[0] + "/runtime")

DIR_SHARE = xdg.xdg_data_home() / "ABCT-toolkit"
DIR_CACHE = xdg.xdg_cache_home() / "ABCT-toolkit"

_TOKEN_EMBEDDING_DIM = 200
_CHAR_EMBEDDING_DIM = 50
_CHAR_EMBEDDED_DIM = 100

_TOKEN_INDEXERS = {
    "tokens": {
        "type": "single_id",
        "lowercase_tokens": False,
    },
    "token_characters": {
        "type": "characters",
        "min_padding_length": 5,
        "character_tokenizer": {
            "end_tokens": [
                "@@PADDING@@",
                "@@PADDING@@",
                "@@PADDING@@",
                "@@PADDING@@",
            ]
        }
    }
}

CONF_DEFAULT = {
    "bin-sys": {
        "m4": "m4",
        "sed": "sed",
        "java": "java",
        "ruby": "ruby",
        "awk": "gawk",
        "munge-trees": "munge-trees",
    },
    "bin-custom": {
        "abc-relabel": f"{DIR_RUNTIME / 'abc-relabel'} --oneline", 
        "tsurgeon_script": DIR_RUNTIME / "tsurgeon_script",
        "move": DIR_RUNTIME / "move",
    },
    "runtimes": {
        "pre-relabel": DIR_RUNTIME / "pre-relabel.tsgn",
        "pretreatments": DIR_RUNTIME / "tsurgeon-debug/pretreatments.tsgn",
        "dependency": DIR_RUNTIME / "tsurgeon-debug/dependency.tsgn",
        "dependency-post": DIR_RUNTIME / "tsurgeon-debug/dependency-post.tsgn",
        "simplify-tag": DIR_RUNTIME / "simplify-tag.sed",
        "tregex": DIR_RUNTIME / "stanford-tregex.jar",
        "unsimplify-ABC-tags": DIR_RUNTIME / "unsimplify-ABC-tags.rb",
        "move-comparative": DIR_RUNTIME / "move-comparative.tsgn",
        "move0": DIR_RUNTIME / "move0.tsgn",
    },
    "corpora": {
        "Mainichi95": DIR_SHARE / "corpora/MAI95.TXT",
        "CSJ": DIR_SHARE / "corpora/csj",
        "BCCWJ": DIR_SHARE / "corpora/bccwj",
        "SIDB": DIR_SHARE / "corpora/sidb",
    },
    "skip-ill-trees": True,
    "gen-comp": {
        "tree-filter": "typical|関係節|連用節"
    },
    "max_process_num": (
        len(num)
        if (num := psutil.Process().cpu_affinity())
        else 0
    ),
    "ml": {
        "train_test_ratio": 80,
        "trainer_settings": {
            "dataset_reader": {
                "type": "ja_supertagging_dataset",
                "lazy": True,
                "token_indexers": _TOKEN_INDEXERS
            },
            "validation_dataset_reader": {
                "type": "ja_supertagging_dataset",
                "lazy": True,
                "token_indexers": _TOKEN_INDEXERS
            },
            # "train_data_path": given dynamically
            # "validation_data_path": given dynamically
            "model": {
                "type": "supertagger",
                "text_field_embedder": {
                    "token_embedders": {
                        "tokens": {
                            "type": "embedding",
                            "pretrained_file": (
                                xdg.xdg_data_home() / "ABCT-toolkit/jawiki.entity_vectors.200d.txt"
                            ),
                            "embedding_dim": _TOKEN_EMBEDDING_DIM,
                            "sparse": True
                        },
                        "token_characters": {
                            "type": "character_encoding",
                            "embedding": {
                                "embedding_dim": _CHAR_EMBEDDING_DIM,
                                "sparse": True,
                                "trainable": True
                            },
                            "encoder": {
                                "type": "cnn",
                                "embedding_dim": _CHAR_EMBEDDING_DIM,
                                "num_filters": _CHAR_EMBEDDED_DIM,
                                "ngram_filter_sizes": [5]
                            }
                        }
                    }
                },
                "encoder": {
                    "type": "lstm",
                    "input_size": _TOKEN_EMBEDDING_DIM + _CHAR_EMBEDDED_DIM,
                    "hidden_size": 200,
                    "num_layers": 2,
                    "dropout": 0.32,
                    "bidirectional": True,
                },
                "tag_representation_dim": 100,
                "arc_representation_dim": 100,
                "dropout": 0.32,
                "input_dropout": 0.5,
            },
            "iterator": {
                "type": "bucket",
                "cache_instances": False,
                "batch_size": 128,
                "sorting_keys": [
                    ["words", "num_tokens"]
                ],
            },
            "trainer": {
                "optimizer": {
                    "type": "dense_sparse_adam",
                    "betas": [0.9, 0.9]
                },
                "learning_rate_scheduler":{
                    "type": "reduce_on_plateau",
                    "mode": "max",
                    "factor": 0.5,
                    "patience": 5,
                },
                "validation_metric": "+harmonic_mean",
                "grad_norm": 5,
                "num_epochs": 100,
                "patience": 20,
                "cuda_device": 0,
            },
        }
    }
}

# ========================
# Runtime Checking
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
        return 2 # ENOENT
    else:
        return 0 # Successful
    # === END IF ===
# === END ===
