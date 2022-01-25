import typing 
import logging
logger = logging.getLogger(__name__)

import pathlib
import re

import attr

from abctk import ABCTException
import abctk.config as CONF
import abctk.types as at
from . import corpus_readers

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