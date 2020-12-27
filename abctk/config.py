import psutil
import pathlib

import xdg 

DIR_RUNTIME = pathlib.Path(__file__).parent / "runtime"

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
        "m4": "m4", #"m4",
        "sed": "sed",
        "java": "java",
    },
    "bin-custom": {
        "abc-relabel": DIR_RUNTIME / "abc-relabel", 
        "tsurgeon_script": DIR_RUNTIME / "tsurgeon_script",
    },
    "runtimes": {
        "pre-relabel": DIR_RUNTIME / "pre-relabel.tsgn",
        "simplify-tag": DIR_RUNTIME / "simplify-tag.sed",
        "tregex": DIR_RUNTIME / "stanford-tregex.jar",
    },
    "max_process_num": len(psutil.Process().cpu_affinity()),
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