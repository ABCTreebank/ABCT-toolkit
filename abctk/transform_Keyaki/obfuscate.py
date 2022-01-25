import re
import typing
import logging

logger = logging.getLogger(__name__)

from nltk.tree import Tree

from abctk import ABCTException

X = typing.TypeVar("X", Tree, str)

def obfuscate_tree(
    subtree: X, 
    ID: str = "<UNKNOWN>"
) -> X:
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


class UnmatchingDecriptionException(ABCTException):
    amount: int
    def __init__(self, amount: int):
        self.amount = amount

        super().__init__(amount)

def decrypt_tree(
    subtree: typing.Union[Tree, str],
    source: str,
    source_pos: int = 0,
    ID: str = "<UNKNOWN>"
) -> typing.Tuple[typing.Union[Tree, str], int]:
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
                f"The Tree {ID} is smaller than expected. "
                "The overflowed part of the tree will remain untouched."
            ),
            stack_info = False,
        )
        return subtree, source_pos
    except Exception as e:
        raise
    # == END TRY ===
# === END ===

re_match_Keyaki_ID_Mai95 = re.compile(
    r".*_news-closed_MAI_.*;(?P<ID>\d{9}-\d{3});JP"
)