import re
import typing
import logging

logger = logging.getLogger(__name__)

from nltk.tree import Tree

X = typing.TypeVar("X", Tree, str,)

def obfuscate_tree(
    subtree: X, 
    ID: str = "<UNKNOWN>"
) -> X:
    """
    Replace characters in a given tree with ⛔.
    """
    if isinstance(subtree, Tree):
        return Tree(
            node = subtree.label(),
            children = list(obfuscate_tree(child) for child in subtree)
        )
    elif isinstance(subtree, str) and not (
        subtree.startswith("*")
        or subtree.startswith("__")
    ):
        return "⛔" * len(subtree)
    else:
        # do nothing
        return subtree

def decrypt_tree(
    subtree: X,
    source: str,
    source_pos: int = 0,
    ID: str = "<UNKNOWN>"
) -> typing.Tuple[X, int]:
    """
    Decrypt a given tree with the original text.

    Parameters
    ----------
    subtree
    source
        The original text corresponding to the given tree.
    source_pos
        [Internal] Current position of the source text.
    ID
        The tree ID.

    Exceptions
    ----------
    UnmatchingDecryptionException
    """
    try:
        if isinstance(subtree, Tree):
            new_children = []
            for child in subtree:
                new_child, source_pos = decrypt_tree(
                    child,
                    source,
                    source_pos,
                    ID,
                )
                new_children.append(new_child)
            # === END FOR child ===

            return Tree(
                node = subtree.label(),
                children = new_children
            ), source_pos
        elif isinstance(subtree, str):
            word_new = ""
            for char in subtree:
                if char == "⛔":
                    word_new += source[source_pos]
                    source_pos += 1
                else:
                    word_new += char
                # === END IF ===
            # === END FOR char ===
            
            return word_new, source_pos
        else:
            # do nothing
            return subtree, source_pos
        # === END IF ===
    except IndexError:
        logger.error(
            msg = (
                f"The lexical nodes of Tree {ID} is smaller than the original text. "
                "The overflowed part of the tree will remain untouched."
            ),
            stack_info = False,
        )
        return subtree, source_pos
    except Exception as e:
        raise
    # == END TRY ===
# === END ===