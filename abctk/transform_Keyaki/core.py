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
import abctk.types as at

def obfuscate_tree(
    subtree: at.KeyakiTree, 
    Id: str = ""
) -> at.KeyakiTree:
    if subtree.is_terminal():
        word: str = subtree.root
        if word.startswith("*") or word.startswith("__"):
            return subtree
        else:
            return attr.evolve(
                subtree,
                root = "⛔" * len(word)
            )
    else:
        return attr.evolve(
            subtree,
            children = [obfuscate_tree(child, Id) for child in subtree.children]
        )
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
    trees_Maybe_wID = at.TypedTreebank.from_PTB_basic_stream(
        source = f_src,
        name = src_name,
        uniformly_with_ID = True,
    )

    def _obf(Id: str, tree) -> at.TypedTree[str, str]:
        if matcher.search(Id):
            return obfuscate_tree(tree, Id)
        else:
            return tree
        # === END IF ===
    # === END ===

    tb_res = attr.evolve(
        trees_Maybe_wID,
        index = {
            k:_obf(Id = k, tree = v)
            for k, v in trees_Maybe_wID.index.items()
        }
    )

    tb_res.to_PTB_single_stream(f_dest)
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