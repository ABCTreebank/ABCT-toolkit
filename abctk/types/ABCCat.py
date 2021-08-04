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

    Examples
    --------
    >>> parse_annot("<NP/NP>#role=h#deriv=leave")
    ('<NP/NP>', {'role': <DepMk.HEAD: 'h'>, 'deriv': 'leave'})
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

    Examples
    --------
    >>> _, feat_set = parse_annot("<NP/NP>#role=h#deriv=leave")
    >>> annot_feat_pprint(feat_set)
    '#role=h#deriv=leave'

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
    """
    The left functor `\\`.
    """

    RIGHT = "R"
    """
    The right functor '/'.
    """

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
    """
    Representing details of simplification of ABC categories.
    """

    func_mode: ABCCatFunctorMode
    """
    The used rule in the simplification.
    """

    level: int
    """
    The depth of functional compoisition.
    """

    def __str__(self):
        return f"{self.func_mode.value}{self.level}"

ABCCatReady = typing.Union[str, "ABCCat"]
"""
The union of the types that is interpretable as ABC categories.
"""

class ABCCat():
    """
    The abstract base class representing ABC categories.

    Notes
    -----
    All instances of all subclasses of this are expected to be identifiable by `==`, hashable, and frozen (unchangeable; all operations create new instances).

    All category-related arguments of the methods are expected to accept both `ABCCat` and any other types that can be interpretable as `ABCCat`, instances of the latter types begin implicitly parsed.
    This feature will enable a readable and succint coding and manupilation of `ABCCat` objects.
    """

    @functools.lru_cache()
    def adjunct(self, func_mode: ABCCatFunctorMode) -> "ABCCatFunctor":
        """
        Make a self adjunction from a category.

        Examples
        --------
        >>> ABCCat.p("NP").adjunct(ABCCatFunctorMode.RIGHT).pprint()
        '<NP/NP>'
        """
        return ABCCatFunctor(
            func_mode = func_mode,
            ant = self,
            conseq = self,
        )

    def adj_l(self):
        """
        Make a self left adjunction from a category.
        This is no more than an alias of `ABCCat.adjunct(cat, ABCCatFunctorMode.LEFT)`.
        """

        return self.adjunct(ABCCatFunctorMode.LEFT)

    def adj_r(self):
        """
        Make a self right adjunction from a category.
        This is no more than an alias of `ABCCat.adjunct(cat, ABCCatFunctorMode.RIGHT)`.
        """
        return self.adjunct(ABCCatFunctorMode.RIGHT)

    @functools.lru_cache()
    def r(self, ant: ABCCatReady) -> "ABCCatFunctor":
        """
        An iconic method to create a right functor cateogry.
        To the argument comes the antecedent (viz. the `B` in `A/B`).

        Notes
        -----
        The (antecedent) argument can be of any types in `ABCCatReady`.
        It is not necessary to convert an `str` antecedent into an `ABCCat` beforehand.

        The `/` (true division) operator is also available as an alias of this function.

        See also
        --------
        ABCCat.l:
            The same method for left functors.

        Examples
        --------
        >>> ABCCat.p("NP").r("Scomp").pprint()
        '<NP/Scomp>'

        >>> (ABCCat.p("NP") / "Scomp").pprint()
        '<NP/Scomp>'
        """
        return ABCCatFunctor(
            func_mode = ABCCatFunctorMode.RIGHT,
            ant = self.p(ant),
            conseq = self,
        )
    
    def __truediv__(self, others):
        return self.r(others)

    @functools.lru_cache()
    def l(self, conseq: ABCCatReady) -> "ABCCatFunctor":
        """
        An iconic method to create a left functor cateogry.
        To the argument comes the consequence (viz. the `B` in `B\\A`).

        Notes
        -----
        The (antecedent) argument can be of any types in `ABCCatReady`.
        It is not necessary to convert an `str` antecedent into an `ABCCat` beforehand.

        For left functors, which has no baskslash counterpart that is eligible for an Python binary operator (like the `/` for right functors),
            a workaround would be combining `/` with the direction inversion `~`.

        Examples
        --------
        >>> ABCCat.p("NP").l("S").pprint()
        '<NP\\\\S>'
        """
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
        """
        Simplify two ABC categories.

        Arguments
        ---------
        left: ABCCatReady
        right: ABCCatReady

        Returns
        -------
        cat: ABCCat
            The resulting category.
            If simplification fails, it yields `ABCCatBot.BOT` (the bottom ⊥).
        res: ABCReductionRes or None
            The details of the simplification process.
            If it fails, it is a `None`.

        Notes
        -----
        `*` is an alias operator with simplification details omitted.

        Examples
        --------
        >>> cat, res = ABCCat.apply("NP", "NP\\\\S")
        >>> cat.pprint()
        'S'
        >>> str(res)
        'L0'
        >>> cat == ABCCat.p("NP") * "NP\\\\S"
        True

        >>> cat, res = ABCCat.apply("C/S", "S/NP")
        >>> cat.pprint()
        '<C/NP>'
        >>> str(res)
        'R1'

        >>> cat, res = ABCCat.apply("S", "NP")
        >>> cat.pprint()
        '⊥'
        >>> res is None
        True
        """

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

        Arguments
        ---------
        source: ABCCatReady
            The thing to be parsed. If it is already an `ABCCat`, nothing happens and the method just returns this thing.
        mode: ABCCatReprMode, default: ABCCatReprMode.TLCG
            The linear order of functor categories.

        Returns
        -------
        parsed: ABCCat

        Examples
        --------
        >>> np: ABCCatBase = ABCCat.parse("NP")
        >>> np.name
        'NP'

        >>> pred: ABCCatFunctor = ABCCat.parse("NP\\\\S")
        >>> pred.pprint()
        '<NP\\\\S>'

        >>> ABCCat.parse(pred) == pred
        True
        """
        if isinstance(source, str):
            return _parser_ABCCat.parse(source) # typing: ignore
        elif isinstance(source, ABCCat):
            return source
        else:
            raise TypeError

    @classmethod
    def p(
        cls,
        source: ABCCatReady,
        mode: ABCCatReprMode = ABCCatReprMode.TLCG,
    ) -> "ABCCat":
        """
        An alias of `ABCCat.parse`.
        """
        return cls.parse(source, mode)

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
    """
    Representing atomic ABC categories.
    """

    name: str
    """
    The letter of the atom.
    """

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
    """
    Representing functor categories.
    """

    func_mode: ABCCatFunctorMode
    """
    The mode, or direction, of the functor.
    """

    ant: "ABCCat"
    """
    The antecedent.
    """

    conseq: "ABCCat"
    """
    The consequence.
    """

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
        """
        Invert the direction of the functor.

        Notes
        -----
        This method always returns a new instance.

        Examples
        --------
        >>> cat = ABCCat.p("NP\\\\S")
        >>> cat.invert_dir().pprint()
        '<S/NP>'

        >>> cat.invert_dir() == ~cat
        True
        """

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