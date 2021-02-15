import typing 
import logging
logger = logging.getLogger(__name__)

import functools
import pathlib
import os
import re
import sys

import attr

import abctk.config as CONF
import abctk.types.trees as at

def obfuscate_tree(
    subtree: at.Tree, 
    Id: str = ""
) -> at.Tree:
    if isinstance(subtree, at.Tree):
        return at.Tree(
            subtree.label(),
            map(
                functools.partial(obfuscate_tree, Id = Id),
                subtree
            )
        )
    elif isinstance(subtree, str):
        if subtree.startswith("*") or subtree.startswith("__"):
            return subtree
        else:
            return "⛔" * len(subtree)
    else:
        raise ValueError(f"Ill-formed Tree, ID: {Id}")
    # === END IF ===
# === END ===

def obfuscate_stream(
    f_src: typing.TextIO,
    f_dest: typing.TextIO,
    src_name: typing.Any = "<INPUT>",
    dest_name: typing.Any = "<OUTPUT>",
    matcher: typing.Pattern[str] = re.compile(r"closed"),
    **kwargs
) -> int:
    trees_Maybe_wID: typing.Iterable[at.Tree_with_ID] = at.parse_ManyTrees_Maybe_with_ID(f_src.read())

    for tree_wID in trees_Maybe_wID:
        tree_id = tree_wID.ID
        if matcher.search(tree_id):
            res = attr.evolve(
                tree_wID, 
                content = obfuscate_tree(tree_wID.content, tree_id),
            )
            res.pprint(stream = f_dest)
        else:
            tree_wID.pprint(stream = f_dest)
    # === END FOR tree_wID ===
    return 0
# === END ===

def obfuscate_file(
    src: pathlib.Path, 
    dest: pathlib.Path,
    **kwargs
) -> int:
    try:
        with open(src, "r") as h_src, open(dest, "w") as h_dest:
            res = obfuscate_stream(
                h_src, h_dest,
                src, dest,
            )
        # === END WITH h_src, h_dest ===
        return res
    except IOError:
        logger.exception(f"IO Error occurred when processing the file: {src}")
        raise
    except Exception as e:
        logger.exception(f"Exception {e} occurred when processing the file: {src}")
        raise
# === END ===