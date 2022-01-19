import typing 
import logging
logger = logging.getLogger(__name__)

import functools
import pathlib
import os
import re
import sys

import attr
import pykakasi
_kks: pykakasi.kakasi = None

from abctk import ABCTException
import abctk.config as CONF
import abctk.types as at
from . import corpus_readers

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
class UnmatchingDecriptionException(ABCTException):
    amount: int

def decrypt_tree(
    subtree: at.KeyakiTree,
    source: str,
    source_pos: int = 0,
    Id: str = ""
) -> typing.Tuple[at.KeyakiTree, int]:
    try:
        if subtree.is_terminal():
            word: str = subtree.root
            word_new = ""
            for char in word:
                if char == "⛔":
                    word_new += source[source_pos]
                    source_pos += 1
                else:
                    word_new += char
                # === END IF ===
            # === END FOR char ===
            
            return (
                attr.evolve(
                    subtree,
                    root = word_new
                ), source_pos
            )
        else:
            new_children = []
            for child in subtree.children:
                new_child, source_pos = decrypt_tree(
                    child,
                    source,
                    source_pos,
                    Id,
                )
                new_children.append(new_child)
            # === END FOR child ===
            
            return (
                attr.evolve(
                    subtree,
                    children = new_children
                ), source_pos
            )
        # === END IF ===
    except IndexError:
        logger.error(
            msg = (
                f"The Tree {Id} is smaller than expected. "
                "The overflowed part of the tree will remain untouched."
            ),
            stack_info = False,
        )
        return subtree, source_pos
    # == END TRY ===
# === END ===

_re_match_Keyaki_ID_Mai95 = re.compile(
    r".*_news-closed_MAI_.*;(?P<ID>\d{9}-\d{3});JP"
)
def decrypt_stream(
    f_src: typing.TextIO,
    f_dest: typing.TextIO,
    corpora_tsv: typing.TextIO,
    src_name: typing.Any = "<INPUT>",
    dest_name: typing.Any = "<OUTPUT>",
    **kwargs
) -> int:
    corpora_tsv_parsed = corpus_readers.load_corpora_sentences_from_tsv_stream(
        source = corpora_tsv
    )

    def _match_key(src_ID, corpora_keys) -> typing.Optional[corpus_readers.Corpus_Identifier]:
        match = _re_match_Keyaki_ID_Mai95.match(src_ID)
        if match:
            return corpus_readers.Corpus_Identifier(
                corpus = "MAI",
                ID = match.group("ID")
            )
        # === END IF ===

        return None
    # === END ===

    def _trans_tree(ID, tree, corpora_tsv_parsed, corpora_keys):
        match_key = _match_key(ID, corpora_keys)

        if match_key:
            return decrypt_tree(
                tree,
                source = corpora_tsv_parsed[match_key],
                Id = ID,
            )[0]
        else:
            return tree
    # === END ===

    tb = at.TypedTreebank.from_PTB_basic_stream(
        source = f_src,
        name = src_name,
        uniformly_with_ID = True,
    )

    tb_res = attr.evolve(
        tb,
        index = {
            ID:_trans_tree(
                ID, tree, 
                corpora_tsv_parsed,
                corpora_keys = corpora_tsv_parsed.keys()
            )
            for ID, tree in tb.index.items()
        }
    )

    tb_res.to_PTB_single_stream(f_dest)

    return 0
# === END ===

def decrypt_file(
    src: pathlib.Path,
    dest: pathlib.Path,
    corpora_tsv: pathlib.Path,
    **kwargs
) -> int:
    try:
        with open(src, "r") as h_src, open(corpora_tsv, "r") as h_tsv, open(dest, "w") as h_dest:
            res = decrypt_stream(
                h_src, h_dest,
                h_tsv,
                src, dest,
            )
        # === END WITH h_src, h_tsv, h_dest ===
        return res
    except IOError:
        logger.exception(f"IO Error occurred when processing the file: {src}")
        raise
    except Exception as e:
        logger.exception(f"Exception {e} occurred when processing the file: {src}")
        raise
# === END ===

def kakasi_tree(
    subtree: at.KeyakiTree, 
    Id: str = ""
):
    # Initialize the engine
    global _kks
    if _kks is None:
        _kks = pykakasi.kakasi()

    if subtree.is_terminal():
        word: str = subtree.root

        if word.startswith("*") or word.startswith("__"):
            return subtree
        else:
            return attr.evolve(
                subtree,
                root = "".join(res["hepburn"] for res in _kks.convert(word))
            )

    else:
        return attr.evolve(
            subtree,
            children = [kakasi_tree(child, Id) for child in subtree.children]
        )
    # === END IF ===
# === END ===

def kakasi_stream(
    f_src: typing.TextIO,
    f_dest: typing.TextIO,
    src_name: typing.Any = "<INPUT>",
    dest_name: typing.Any = "<OUTPUT>",
    **kwargs
):
    trees_Maybe_wID = at.TypedTreebank.from_PTB_basic_stream(
        source = f_src,
        name = src_name,
        uniformly_with_ID = True,
    )

    tb_res = attr.evolve(
        trees_Maybe_wID,
        index = {
            k:kakasi_tree(Id = k, subtree = v)
            for k, v in trees_Maybe_wID.index.items()
        }
    )

    tb_res.to_PTB_single_stream(f_dest)
    # === END FOR tree_wID ===

    return 0
# === END ===

def kakasi_file(
    src: pathlib.Path, 
    dest: pathlib.Path,
    **kwargs
):
    try:
        with open(src, "r") as h_src, open(dest, "w") as h_dest:
            res = kakasi_stream(
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