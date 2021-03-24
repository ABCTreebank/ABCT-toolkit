import enum
from functools import lru_cache
import itertools
from packaging.version import Version
#import sys
#PY_VER = sys.version_info
#
import typing
#if PY_VER >= (3, 7):
#    from typing import Literal # type: ignore
#else:
#    from typing_extensions import Literal # type: ignore
# === END IF ===

import attr

from . import core

_X = typing.TypeVar("_X")
_X1 = typing.TypeVar("_X1")
_X2 = typing.TypeVar("_X2")

NT      = typing.TypeVar("NT", typing.Any, core.IPrettyPrintable)

class ABCDepMarking(enum.Enum):
    """
    An inventory of dependency markings used in the Keyaki-to-ABC conversion. 
    """

    NONE = ""
    """
    The default, empty marking.
    """

    HEAD = "h"
    """
    Stands for a phrase head.
    """

    COMPLEMENT = "c"
    """
    Stands for a complement in a phrase.
    """

    ADJUNCT = "a"
    """
    Stands for an adjunct of a phrase.

    .. note::
        The conversion process will
        try to make adjuncts marked by this
        modify the smallest core of the head.
        As a result, the adjuncts are made predicated of the 
        head without affecting its complements.
        This is intended to be an approximation to the raising effect.
    """

    ADJUNCT_CONTROL = "ac"
    """
    The adjunct-control marking.
    Nearly same as `ADJUNCT`, except that 
    the head will eventually get modified along with its subject(s).
    The "ac"-marked adjuncts will end up controlling this subject / these subjects.  
    """
# === END CLASS ===

@attr.s(
    auto_attribs = True,
)
class ABCCatPlus(
    typing.Generic[NT],
    core.IPrettyPrintable,
):
    cat: NT
    role: ABCDepMarking = attr.ib(
        default = ABCDepMarking.NONE
    )
    deriv: str = attr.ib(
        default = ""
    )

    def pprint(self, **kwargs) -> str:
        others = "".join(
            f"#{k}={v}"
            for k, v in self.__dict__.items()
            if k not in ["role", "deriv", "cat"]
        )
        role = (
            f"#role={self.role.value}" 
            if self.role != ABCDepMarking.NONE else ""
        )
        deriv = f"#deriv={self.deriv}" if self.deriv else ""
        
        return f"{self.cat}{role}{deriv}{others}"
    # === END ===

    def __str__(self) -> str:
        return self.pprint()

    @staticmethod
    @lru_cache()
    def gen_larkgrammar(gram_nonterm: str) -> str:
        rf"""
        

        {gram_nonterm.spilt()}

        """
# === END CLASS ===

KeyakiCat = str
KeyakiCat_ABCCatPlus = ABCCatPlus[KeyakiCat] # type: ignore

class ABCCatBot(enum.Enum):
    """
    Represents the bottom type in the ABC Treebank.
    """

    BOT = "⊥"

class ABCCatFunctorMode(enum.Enum):
    LEFT = "L"
    RIGHT = "R"
# === END CLASS ===

@attr.s(
    auto_attribs = True, # Unnecessary in newer version of Python
    frozen = True,
    slots = True,
)
class ABCCatFunctor(
    core.IPrettyPrintable
):
    mode: ABCCatFunctorMode # Effective in Python >= 3.8
    ant: "ABCCat"
    conseq: "ABCCat"

    @classmethod
    def make_adjunct(
        cls, 
        mode: ABCCatFunctorMode, 
        cat: "ABCCat"
    ):
        return cls(
            mode = mode,
            ant = cat,
            conseq = cat
        )
    # === END ===

    def pprint(self, **kwargs) -> str:
        if self.mode == ABCCatFunctorMode.LEFT:
            if kwargs.get("natural_dir", True):
                return f"<{self.ant}\\{self.conseq}>"
            else:
                return f"<{self.conseq}\\{self.ant}>"
        elif self.mode == ABCCatFunctorMode.RIGHT:
            return f"<{self.conseq}/{self.ant}>"
        else:
            raise ValueError
    # === END ===

    def __str__(self) -> str:
        return self.pprint()
    # === END ===
# === END CLASS ===

ABCCat = typing.Union[
    str,
    ABCCatFunctor,
    ABCCatBot,
]
"""
The type representing categories in the ABC Treebank.
"""

ABCCat_ABCCatPlus = ABCCatPlus[ABCCat]

KeyakiTree            = core.TypedTree[KeyakiCat, str]
KeyakiTree_ABCCatPlus = core.TypedTree[KeyakiCat_ABCCatPlus, str]
ABCTree_ABCCatPlus    = core.TypedTree[ABCCat_ABCCatPlus, str]

@lru_cache()
def gen_larkgrammar_PennTreebank(
) -> str:
    return rf"""
%import common.WS
%ignore common.WS

tree_simple: TERM
tree_complex: "(" NONTERM? tree* ")"
tree: tree_simple | tree_complex

tree_with_id: "(" tree_complex "(" "ID" /[^\s]+/ ")" ")"
tree_maybe_with_id: tree_with_id | tree
tree_list: tree_maybe_with_id*

NONTERM: /[^\s]+/
TERM: /[^\s]+/
"""
