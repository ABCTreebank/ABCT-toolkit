import abc as abst_class
from enum import Enum
import functools
import re
import typing

import attr
import parsy

class DepMk(Enum):
    """
    An inventory of dependency markings used in the Keyaki-to-ABC conversion. 
    """

    NONE = "none"
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

    Notes
    -----
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

PlainCat = str
KeyakiCat = str

Annot = typing.Dict[
    str,
    typing.Any,
]
Plain_Annot = typing.Tuple[PlainCat, Annot]

_annot_cat_basic_matcher = re.compile(r"^(?P<cat>[^#]*)(?P<feats>#.*)$")
_annot_feat_matcher = re.compile(r"#(?P<key>[^=]+)=(?P<val>[^#]*)")
def parse_annot(source: str) -> Plain_Annot:
    """
    Parse a tree node label with ABC annotations.

    Arguments
    ---------
    source : str
        A tree node label.

    Returns
    -------
    cat : str
        The category part.
    remainder : dict
        The feature part.
    """
    match = _annot_cat_basic_matcher.match(source)

    if match is None: raise ValueError

    feats: Annot = {
        m.group("key"):m.group("val")
        for m in _annot_feat_matcher.finditer(match.group("feats"))
    }

    if "role" in feats:
        feats["role"] = DepMk(feats["role"])
    else:
        feats["role"] = DepMk.NONE
    # === END IF ==

    return match.group("cat"), feats

def annot_feat_pprint(
    feat_set: Annot
) -> str:
    """
    Prettyprint an ABC Treebank feature bundle.
    """
    if "role" in feat_set:
        role = f"#role={feat_set['role'].value}"
    else:
        role = ""
    # === END IF===

    others = "".join(
        f"#{k}={v}"
        for k, v in feat_set.items()
        if k not in ["role"]
    )
    
    return f"{role}{others}"

# ============
# Classes for ABC categories
# ============

class ABCCatFunctorMode(Enum):
    """
    The enumeration of the types in ABC categories.
    """
    LEFT = "L"
    RIGHT = "R"

    def __invert__(self):
        if self == self.LEFT:
            return self.RIGHT
        elif self == self.RIGHT:
            return self.LEFT
        else:
            return self

# === END CLASS ===

class ABCCatReprMode(Enum):
    TRADITIONAL = 0
    TLCG = 1

@attr.s(
    auto_attribs = True,
    slots = True,
    frozen = True,
)
class ABCReductionRes:
    func_mode: ABCCatFunctorMode
    level: int

    def __str__(self):
        return f"{self.func_mode.value}{self.level}"

ABCCatReady = typing.Union[str, "ABCCat"]
class ABCCat():
    """
    The abstract base class representing ABC categories.
    """

    @functools.lru_cache()
    def adjunct(self, func_mode: ABCCatFunctorMode) -> "ABCCatFunctor":
        return ABCCatFunctor(
            func_mode = func_mode,
            ant = self,
            conseq = self,
        )

    def adj_l(self):
        return self.adjunct(ABCCatFunctorMode.LEFT)

    def adj_r(self):
        return self.adjunct(ABCCatFunctorMode.RIGHT)

    @functools.lru_cache()
    def r(self, ant: ABCCatReady) -> "ABCCatFunctor":
        return ABCCatFunctor(
            func_mode = ABCCatFunctorMode.RIGHT,
            ant = self.p(ant),
            conseq = self,
        )
    
    def __truediv__(self, others):
        return self.r(others)

    @functools.lru_cache()
    def l(self, conseq: ABCCatReady) -> "ABCCatFunctor":
        return ABCCatFunctor(
            func_mode = ABCCatFunctorMode.LEFT,
            ant = self,
            conseq = self.p(conseq),
        )

    @abst_class.abstractmethod
    def invert_dir(self) -> "ABCCat": ...

    def __invert__(self):
        return self.invert_dir()

    @classmethod
    @functools.lru_cache()
    def apply(
        cls,
        left: ABCCatReady,
        right: ABCCatReady
    ) -> typing.Tuple["ABCCat", typing.Optional[ABCReductionRes]]:
        left_parsed: "ABCCat" = cls.p(left)
        right_parsed: "ABCCat" = cls.p(right)

        if (
            isinstance(left_parsed, (ABCCatBase, ABCCatBot)) 
            and isinstance(right_parsed, ABCCatFunctor) 
            and right_parsed.func_mode == ABCCatFunctorMode.LEFT
        ):
            if left_parsed == right_parsed.ant:
                return (
                    right_parsed.conseq,
                    ABCReductionRes(
                        ABCCatFunctorMode.LEFT,
                        0
                    )
                )
            else:
                return (ABCCatBot.BOT, None)
        elif (
            isinstance(left_parsed, ABCCatFunctor)
            and left_parsed.func_mode == ABCCatFunctorMode.RIGHT
            and isinstance(right_parsed, (ABCCatBase, ABCCatBot))
        ):
            if left_parsed.ant == right_parsed:
                return (
                    left_parsed.conseq,
                    ABCReductionRes(
                        ABCCatFunctorMode.RIGHT,
                        0
                    )
                )
            else:
                return (ABCCatBot.BOT, None)
        elif (
            isinstance(left_parsed, ABCCatFunctor)
            and left_parsed.func_mode == ABCCatFunctorMode.LEFT
            and isinstance(right_parsed, ABCCatFunctor) 
            and right_parsed.func_mode == ABCCatFunctorMode.LEFT
        ):
            if left_parsed.ant == right_parsed:
                return (
                    left_parsed.conseq,
                    ABCReductionRes(
                        ABCCatFunctorMode.LEFT,
                        0
                    )
                )
            else:
                # (A\)B B\C -> (A\)C
                cat, code = cls.apply(
                    left_parsed.conseq,
                    right_parsed
                )

                if (
                    code is not None 
                    and code.func_mode == ABCCatFunctorMode.LEFT
                ):
                    return (
                        left_parsed.ant.l(cat),
                        attr.evolve(code, level = code.level + 1)
                    )
                else:
                    return ABCCatBot.BOT, None
        elif (
            isinstance(left_parsed, ABCCatFunctor)
            and left_parsed.func_mode == ABCCatFunctorMode.RIGHT
            and isinstance(right_parsed, ABCCatFunctor) 
            and right_parsed.func_mode == ABCCatFunctorMode.RIGHT
        ):
            if left_parsed == right_parsed.ant:
                return (
                    right_parsed.conseq,
                    ABCReductionRes(
                        ABCCatFunctorMode.RIGHT,
                        0
                    )
                )
            else:
                # C/B B(/A) -> C(/A)
                cat, code = cls.apply(
                    left_parsed,
                    right_parsed.conseq
                )

                if (
                    code is not None 
                    and code.func_mode == ABCCatFunctorMode.RIGHT
                ):
                    return (
                        cat.r(right_parsed.ant),
                        attr.evolve(code, level = code.level + 1)
                    )
                else:
                    return (ABCCatBot.BOT, None)
        elif (
            isinstance(left_parsed, ABCCatFunctor)
            and left_parsed.func_mode == ABCCatFunctorMode.RIGHT
            and isinstance(right_parsed, ABCCatFunctor) 
            and right_parsed.func_mode == ABCCatFunctorMode.LEFT
        ):
            if left_parsed == right_parsed.ant:
                return (
                    right_parsed.conseq, 
                    ABCReductionRes(
                        ABCCatFunctorMode.LEFT,
                        0
                    )
                )
            elif left_parsed.ant == right_parsed:
                return (
                    left_parsed.conseq,
                    ABCReductionRes(
                        ABCCatFunctorMode.RIGHT,
                        0
                    )
                )
            else:
                return (ABCCatBot.BOT, None)
        elif (
            isinstance(left_parsed, ABCCat)
            and isinstance(right_parsed, ABCCat) 
        ):
            return (ABCCatBot.BOT, None)
        else:
            raise TypeError

    @classmethod
    @functools.lru_cache()
    def apply_str(
        cls, left: str, right: str
    ) -> typing.Tuple["ABCCat", typing.Optional[ABCReductionRes]]:
        """
        Reduce a pair of ABC categories in string forms.
        """
        return cls.apply(
            left = cls.parse(left),
            right = cls.parse(right),
        )

    def __mul__(self, others):
        res, _ = ABCCat.apply(self, others)
        return res

    @abst_class.abstractmethod
    def pprint(
        self, 
        mode: ABCCatReprMode = ABCCatReprMode.TLCG
    ) -> str: ...

    @classmethod
    @functools.lru_cache()
    def parse(
        cls, 
        source: ABCCatReady,
        mode: ABCCatReprMode = ABCCatReprMode.TLCG
    ):
        """ 
        Parse an ABC category.
        """
        if mode == ABCCatReprMode.TLCG:
            return cls.p(source)
        else:
            return cls.p_trad(source)

    @classmethod
    def p(cls, source: ABCCatReady) -> "ABCCat":
        if isinstance(source, str):
            return _parser_ABCCat.parse(source) # typing: ignore
        elif isinstance(source, ABCCat):
            return source
        else:
            raise TypeError

    @classmethod
    def p_trad(cls, source: ABCCatReady):
        raise NotImplementedError

class ABCCatBot(ABCCat, Enum):
    """
    Represents the bottom type in the ABC Treebank.
    """
    BOT = "⊥"

    def pprint(
        self, 
        mode: ABCCatReprMode = ABCCatReprMode.TLCG
    ) -> str:
        return self.value

    def invert_dir(self):
        return self

    def __eq__(self, other):
        if isinstance(other, ABCCatBot):
            return (self.value == other.value)
        elif isinstance(other, ABCCat):
            return False
        else:
            return NotImplemented

@attr.s(
    auto_attribs = True,
    frozen = True,
    slots = True,
    hash = True,
)
class ABCCatBase(ABCCat):
    name: str

    def pprint(
        self, 
        mode: ABCCatReprMode = ABCCatReprMode.TLCG
    ) -> str:
        return self.name

    def invert_dir(self):
        return self

    def __eq__(self, other):
        if isinstance(other, ABCCatBase):
            return (self.name == other.name)
        elif isinstance(other, ABCCat):
            return False
        else:
            return NotImplemented

@attr.s(
    auto_attribs = True, # Unnecessary in newer version of Python
    frozen = True,
    slots = True,
    eq = False, # Implemented manually
    hash = True, # Implemented automatically
)
class ABCCatFunctor(ABCCat):
    func_mode: ABCCatFunctorMode
    ant: "ABCCat"
    conseq: "ABCCat"

    def pprint(
        self, 
        mode: ABCCatReprMode = ABCCatReprMode.TLCG
    ) -> str:
        if self.func_mode == ABCCatFunctorMode.LEFT:
            if mode == ABCCatReprMode.TLCG:
                return f"<{self.ant.pprint(mode)}\\{self.conseq.pprint(mode)}>"
            else:
                return f"<{self.conseq.pprint(mode)}\\{self.ant.pprint(mode)}>"
        elif self.func_mode == ABCCatFunctorMode.RIGHT:
            return f"<{self.conseq.pprint(mode)}/{self.ant.pprint(mode)}>"
        else:
            raise ValueError
    # === END ===

    def invert_dir(self):
        fm_new = ~self.func_mode
        return attr.evolve(
            self,
            func_mode = fm_new,
        )

    def __eq__(self, other):
        if isinstance(other, ABCCatFunctor):
            return (
                self.func_mode == other.func_mode
                and self.ant == other.ant
                and self.conseq == other.conseq
            )
        elif isinstance(other, ABCCat):
            return False
        else:
            return NotImplemented
# === END CLASS ===

ABCCat_Annot = typing.Tuple[ABCCat, Annot]

_parser_ABCCatBot: parsy.Parser = parsy.from_enum(ABCCatBot)
_parser_ABCCatBase: parsy.Parser = parsy.regex(r"[^/\\<>#\s]+").map(ABCCatBase)

@parsy.generate
def _parser_ABCCatFunctor_Left() -> parsy.Parser: 
    que = yield (
        _parser_ABCCatBot
        | _parser_ABCCatBase
        | _parser_ABCCat_group
    ).sep_by(
        parsy.string("\\"),
        min = 2,
    )

    return functools.reduce(
        lambda c, a: ABCCatFunctor(
            func_mode = ABCCatFunctorMode.LEFT,
            ant = a,
            conseq = c,
        ),
        reversed(que)
    )
# === END ===

@parsy.generate
def _parser_ABCCatFunctor_Right() -> parsy.Parser:
    stack = yield (
        _parser_ABCCatBot
        | _parser_ABCCatBase
        | _parser_ABCCatFunctor_Left
        | _parser_ABCCat_group
    ).sep_by(
        parsy.string("/"),
        min = 2,
    )

    return functools.reduce(
        lambda c, a: ABCCatFunctor(
            func_mode = ABCCatFunctorMode.RIGHT,
            ant = a,
            conseq = c,
        ),
        stack
    )
# === END ===

_parser_ABCCat_simple: parsy.Parser = (
    _parser_ABCCatFunctor_Left
    | _parser_ABCCatFunctor_Right
    | _parser_ABCCatBot 
    | _parser_ABCCatBase
)

_parser_ABCCat_group: parsy.Parser = (
    parsy.string("<")
    >> _parser_ABCCat_simple
    << parsy.string(">")
)

_parser_ABCCat: parsy.Parser = (
    _parser_ABCCat_simple
    | _parser_ABCCat_group
)