import enum
import functools
import itertools
from packaging.version import Version
import re
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
import parsy

from . import core

_X = typing.TypeVar("_X")
_X1 = typing.TypeVar("_X1")
_X2 = typing.TypeVar("_X2")

NT = typing.TypeVar(
    "NT",
    bound = typing.Union[str, core.IPrettyPrintable]
)

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

_ABCCatPlus_cat_basic_matcher = re.compile(r"^([^#]*)")
def _ABCCatPlus_split_cat_basic(source: str) -> typing.Tuple[str, str]:
    _, cat, remainder = _ABCCatPlus_cat_basic_matcher.split(source, maxsplit = 1)
    return cat, remainder
    
_ABCCatPlus_feat_matcher = re.compile(r"#(?P<key>[^=]+)=(?P<val>[^#]*)")

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

    @classmethod
    def from_str(
        cls,
        source: str,
        cat_parser: typing.Callable[
            [str],
            typing.Tuple[NT, str]
        ] = _ABCCatPlus_split_cat_basic,
    ):
        cat, residue = cat_parser(source)
        feats = {
            m.group("key"):m.group("val")
            for m in _ABCCatPlus_feat_matcher.finditer(residue)
        }
        role_raw: typing.Optional[str] = feats.get("role", None)
        role: ABCDepMarking
        if role_raw is None:
            role = ABCDepMarking.NONE
        else:
            role = ABCDepMarking(role_raw)
        # === END IF ===
        
        res = cls(
            cat = cat,
            role = role,
            deriv = feats.get("deriv", ""),
        )

        for key, val in itertools.filterfalse(
            lambda pair: pair[0] in ("role", "deriv"),
            feats.items()
        ):
            setattr(res, key, val)
        # === END FOR key val ===

        return res
    # === END ===
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
    eq = False, # Implemented manually
    hash = True, # Implemented automatically
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

    def __eq__(self, other):
        if isinstance(other, ABCCatFunctor):
            return (
                self.mode == other.mode
                and self.ant == other.ant
                and self.conseq == other.conseq
            )
        elif isinstance(other, (str, ABCCatBot)):
            return False
        else:
            return NotImplemented
    
    def __lt__(self, other):
        if isinstance(other, ABCCatFunctor): 
            return (
                self.ant < other.ant
                and self.ant < other.conseq
                and self.conseq < other.ant
                and self.conseq < other.conseq
            )
        elif isinstance(other, (str, ABCCatBot)):
            # Functor < str/⊥
            return False
        else:
            return NotImplemented

    def __le__(self, other):
        if isinstance(other, ABCCatFunctor): 
            return (
                self.ant <= other.ant
                and self.ant <= other.conseq
                and self.conseq <= other.ant
                and self.conseq <= other.conseq
            )
        elif isinstance(other, (str, ABCCatBot)):
            # Functor <= str/⊥
            return False
        else:
            return NotImplemented
    
    def __gt__(self, other):
        if isinstance(other, ABCCatFunctor): 
            return (
                self.ant > other.ant
                or self.ant > other.conseq
                or self.conseq > other.ant
                or self.conseq > other.conseq
            )
        elif isinstance(other, (str, ABCCatBot)):
            # Functor > str/⊥
            return True
        else:
            return NotImplemented
    
    def __ge__(self, other):
        if isinstance(other, ABCCatFunctor): 
            return self == other or (
                self.ant > other.ant
                or self.ant > other.conseq
                or self.conseq > other.ant
                or self.conseq > other.conseq
            )
        elif isinstance(other, (str, ABCCatBot)):
            # Functor >= str/⊥
            return True
        else:
            return NotImplemented
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
parser_ABCCatBot: parsy.Parser = parsy.from_enum(ABCCatBot)
parser_ABCCatBase: parsy.Parser = parsy.regex(r"[^/\\<>#\s]+")

@parsy.generate
def parser_ABCCatFunctor_Left() -> parsy.Parser: 
    que = yield (
        parser_ABCCatBot
        | parser_ABCCatBase
        | parser_ABCCat_group
    ).sep_by(
        parsy.string("\\"),
        min = 2,
    )

    return functools.reduce(
        lambda c, a: ABCCatFunctor(
            mode = ABCCatFunctorMode.LEFT,
            ant = a,
            conseq = c,
        ),
        reversed(que)
    )
# === END ===

@parsy.generate
def parser_ABCCatFunctor_Right() -> parsy.Parser:
    stack = yield (
        parser_ABCCatBot
        | parser_ABCCatBase
        | parser_ABCCatFunctor_Left
        | parser_ABCCat_group
    ).sep_by(
        parsy.string("/"),
        min = 2,
    )

    return functools.reduce(
        lambda a, c: ABCCatFunctor(
            mode = ABCCatFunctorMode.RIGHT,
            ant = a,
            conseq = c,
        ),
        stack
    )
# === END ===

parser_ABCCat_simple: parsy.Parser = (
    parser_ABCCatFunctor_Left
    | parser_ABCCatFunctor_Right
    | parser_ABCCatBot 
    | parser_ABCCatBase
)

parser_ABCCat_group: parsy.Parser = (
    parsy.string("<")
    >> parser_ABCCat_simple
    << parsy.string(">")
)

parser_ABCCat: parsy.Parser = (
    parser_ABCCat_group 
    | parser_ABCCat_simple
)

_path_ID_matcher = re.compile(
    r"^(?P<ID>[0-9]+)"
    r"_(?P<category>[^;_]+)"
    r"_(?P<file_name>[^;]+)"
    r";"
)

def make_path_from_Keyaki_or_ABC_ID(
    ID: str, 
    suffix: str = ".psd"
) -> typing.Tuple[str, str]:
    global _path_ID_matcher
    
    match = _path_ID_matcher.match(ID)
    if match:
        return (
            f"{match.group('category')}"
            f"_{match.group('file_name')}"
            f"{suffix}",
            ID
        )
    else:
        return (f"untitled{suffix}", ID)
    # === END IF ===
# === END ===