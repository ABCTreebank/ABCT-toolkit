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

    def _obf(tree_wID: at.Tree_with_ID) -> at.Tree_with_ID:
        tree_id = tree_wID.ID
        if matcher.search(tree_id):
            return attr.evolve(
                tree_wID,
                content = obfuscate_tree(tree_wID.content, tree_id),
            )
        else:
            return tree_wID
        # === END IF ===
    # === END ===

    buf = "\n".join(
        at.print_tree_oneline(_obf(tree).to_Tree()) 
        for tree in trees_Maybe_wID
    )
    f_dest.write(buf)
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

@attr.s(
    auto_attribs = True
)
class UnmatchingDecriptionException(Exception):
    amount: int

def decrypt_stream(
    f_src: typing.TextIO,
    f_orig: typing.TextIO,
    f_dest: typing.TextIO,
    src_name: typing.Any = "<INPUT>",
    orig_name: typing.Any = "<SOURCE>",
    dest_name: typing.Any = "<OUTPUT>",
    **kwargs
) -> int:
    def _gen(f_src, f_orig):
        char_src : str
        char_orig : str
        while True:
            char_src = f_src.read(1)

            if char_src == "⛔":
                char_orig = f_orig.read(1)
                if char_orig:
                    yield char_orig
                else:
                    raise UnmatchingDecriptionException(amount = -1)
                    # TODO: get the amount
            elif char_src == '':
                char_orig = f_orig.read(1)
                if char_orig:
                    raise UnmatchingDecriptionException(amount = 1)
                    # TODO: get the amount
                else:
                    # Success
                    break # END
            else:
                yield char_src
            # === END IF ===

    res: str
    try:
        res = "".join(_gen(f_src, f_orig))
    except UnmatchingDecriptionException as e:
        logger.warning(
            f"""The source tree file does not match with the original corpus.
The tree file exceeds by {e.amount} char(s).
Source: {src_name}
Original: {orig_name}
Output: {dest_name}
The result, which is broken, is nevertheless dumped to {dest_name}."""
        )
    finally:
        f_dest.write(res)

    return 0
# === END ===

def decrypt_file(
    src: pathlib.Path,
    orig: pathlib.Path,
    dest: pathlib.Path,
    **kwargs
) -> int:
    try:
        with open(src, "r") as h_src, open(orig, "r") as h_orig, open(dest, "w") as h_dest:
            res = decrypt_stream(
                h_src, h_orig, h_dest,
                src, orig, dest,
            )
        # === END WITH h_src, h_orig, h_dest ===
        return res
    except IOError:
        logger.exception(f"IO Error occurred when processing the file: {src}")
        raise
    except Exception as e:
        logger.exception(f"Exception {e} occurred when processing the file: {src}")
        raise
# === END ===