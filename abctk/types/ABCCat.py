import abc as abst_class
from collections import deque
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

_annot_cat_basic_matcher = re.compile(r"^(?P<cat>[^#]*)(?P<feats>#.*)?$")
_annot_feat_matcher = re.compile(r"#(?P<key>[^=]+)=(?P<val>[^#]*)")
@attr.s(auto_attribs = True, slots = True, frozen = True)
class Annot:
    cat: typing.Any # TODO: generic
    feats: typing.Dict[str, typing.Any] = attr.ib(factory = dict)
    pprinter_cat: typing.Callable[[typing.Any], str] = str
    
    def pprint(
        self, 
        pprinter_cat: typing.Optional[
            typing.Callable[[typing.Any], str]
        ] = None
    ):
        """
        Prettyprint an ABC Treebank feature bundle.

        Examples
        --------
        >>> label = Annot.parse("<NP/NP>#role=h#deriv=leave")
        >>> label.annot_feat_pprint()
        '<NP/NP>#role=h#deriv=leave'

        """
        if "role" in self.feats:
            role = f"#role={self.feats['role'].value}"
        else:
            role = ""
        # === END IF===

        others = "".join(
            f"#{k}={v}"
            for k, v in self.feats.items()
            if k not in ["role"]
        )
        
        if pprinter_cat:
            cat = pprinter_cat(self.cat)
        else:
            cat = self.pprinter_cat(self.cat)

        return f"{cat}{role}{others}"

    @classmethod
    def parse(
        cls,
        source: str,
        parser_cat: typing.Callable[[str], typing.Any] = (lambda x: x),
        pprinter_cat: typing.Callable[[typing.Any], str] = str,
    ):
        """
        Parse a tree node label with ABC annotations.

        Arguments
        ---------
        source : str
            A tree node label.
        parser_cat
        pprinter_cat

        Examples
        --------
        >>> c = parse_annot("<NP/NP>#role=h#deriv=leave")
        >>> c.cat
        '<NP/NP>'
        >>> isinstance(c.cat, str)
        True
        >>> c.feats
        {'role': <DepMk.HEAD: 'h'>, 'deriv': 'leave'})
        """
        match = _annot_cat_basic_matcher.match(source)

        if match is None: raise ValueError

        feats = {
            m.group("key"):m.group("val")
            for m in _annot_feat_matcher.finditer(match.group("feats") or "")
        }

        if "role" in feats:
            feats["role"] = DepMk(feats["role"])
        else:
            feats["role"] = DepMk.NONE
        # === END IF ==

        return cls(
            parser_cat(match.group("cat")), 
            feats,
            pprinter_cat,
        )

    def __str__(self):
        return self.pprint()

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

    VERT = "V"
    """
    The vertical functor '|' of TLCG.
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
    """
    Styles of representation of categories.
    """

    TRADITIONAL = 0
    """
    The traditional way of representing categories.
    Adopted by Combinatorial Categorial Grammar.

    Examples
    --------
    - `<S/NP>` stands for an `S` wanting an `NP` to its right.
    - `<S\\NP>` is an `S` whose `NP` argument to its left is missing.
    """
    
    TLCG = 1
    """
    An iconic way of representing categories.
    Adopted by Type-logical Categorial Grammar and the ABC Treebank.
    This is the default representation of this package.
    
    Examples
    --------
    - `<S/NP>` stands for an `S` wanting an `NP` to its right.
    - `<NP\\S>` is an `S` whose `NP` argument to its left is missing.
    - `<Sm\\NP>` is a predicate which bears an `m` feature. The categorial features are not marked in a special way.
    """
    
    DEPCCG = 2
    """
    The style that can be read by depccg.
    Parentheses are used instead of angle brackets.

    Examples
    --------
    - `(S/NP)` stands for an `S` wanting an `NP` to its right.
    - `(S\\NP)` is an `S` whose `NP` argument to its left is missing.
    - `(S[m]\\NP)` is a predicate which bears an `m` feature.
    """

    CCG2LAMBDA = 3
    """
    The style compatible with ccg2lambda.

    Examples
    --------
    - `<S/NP>` stands for an `S` wanting an `NP` to its right.
    - `<S\\NP>` is an `S` whose `NP` argument to its left is missing.
    - `<S[m=true]\\NP>` is a predicate which bears an `m` feature.
    """

_re_elimtype = re.compile(
    r"^(?P<dir>[<>|])(B(?P<level>[0-9]+))?$"
)

@attr.s(
    auto_attribs = True,
    slots = True,
    frozen = True,
)
class ElimType:
    """
    Representing details of simplification of ABC categories.

    The string representation `__str__` is compatible with the Jigg-ccg2lambda format. 
    """

    func_mode: ABCCatFunctorMode
    """
    The used rule in the simplification.
    """

    level: int
    """
    The depth of functional compoisition.
    """

    @classmethod
    def is_compatible_repr(cls, input: str) -> bool:
        return (
            input in ("", "none")
            or bool(_re_elimtype.match(input))
        )

    @classmethod
    def is_repr(cls, input: str) -> bool:
        return bool(_re_elimtype.match(input))

    @classmethod
    def maybe_parse(cls, input: str):
        match = _re_elimtype.match(input)

        if match:
            d = match.groupdict()

            level = d.get("level", 0)
            dir_raw = d["dir"]
            
            if dir_raw == "<":
                direct = ABCCatFunctorMode.LEFT
            elif dir_raw == ">":
                direct = ABCCatFunctorMode.RIGHT
            elif dir_raw == "|":
                direct = ABCCatFunctorMode.VERT
            else:
                raise ValueError
            
            return cls(func_mode = direct, level = level)
        else:
            return input

    def __str__(self):
        level_str = f"B{self.level}" if self.level > 0 else ""

        direct = self.func_mode

        if direct == ABCCatFunctorMode.LEFT:
            return f"<{level_str}"
        elif direct == ABCCatFunctorMode.RIGHT:
            return f">{level_str}"
        elif direct == ABCCatFunctorMode.VERT:
            return f"|{level_str}"
        else:
            raise ValueError

ABCSimplifyRes = typing.Tuple["ABCCat", ElimType]

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
        
        >>> ABCCat.p("NP").adjunct(ABCCatFunctorMode.LEFT).pprint()
        '<NP\\\\NP>'

        >>> ABCCat.p("NP").adjunct(ABCCatFunctorMode.VERT).pprint()
        '<NP|NP>'
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

    def adj_v(self):
        """
        Make a self vertical adjunction from a category.
        This is no more than an alias of `ABCCat.adjunct(cat, ABCCatFunctorMode.VERT)`.
        """
        return self.adjunct(ABCCatFunctorMode.VERT)

    @functools.lru_cache()
    def v(self, ant: ABCCatReady) -> "ABCCatFunctor":
        """
        An iconic method to create a vertical functor cateogry.
        To the argument comes the antecedent (viz. the `B` in `A|B`).

        Notes
        -----
        The (antecedent) argument can be of any types in `ABCCatReady`.
        It is not necessary to convert an `str` antecedent into an `ABCCat` beforehand.

        The `|` (bitwise OR) operator is also available as an alias of this function.

        See also
        --------
        ABCCat.l:
            The same method for left functors.

        Examples
        --------
        >>> ABCCat.p("NP").v("Scomp").pprint()
        '<NP|Scomp>'

        >>> (ABCCat.p("NP") | "Scomp").pprint()
        '<NP|Scomp>'
        """
        return ABCCatFunctor(
            func_mode = ABCCatFunctorMode.VERT,
            ant = self.p(ant),
            conseq = self,
        )

    def __or__(self, other: ABCCatReady):
        return self.v(other)

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

        >>> (~(ABCCat.p("S") / "NP")).pprint()
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
    def simplify(
        cls,
        left: ABCCatReady,
        right: ABCCatReady,
    ) -> typing.Iterator[ABCSimplifyRes]:
        """
        Simplify a pair of ABC cateogires, using functor elimination rules
            and functor composition rules.
        All possible results are iterated, duplication not being eliminated.

        Arguments
        ---------
        left: ABCCatReady
        right: ABCCatReady

        Notes
        -----
        It yields nothing if no viable simplification is found.

        Yields
        -------
        cat: ABCCat
            The resulting category.
        res: ElimType
            The details of the simplification process.
        """
        
        left_parsed = ABCCat.p(left)
        right_parsed = ABCCat.p(right)

        queue: typing.Deque[
            typing.Tuple[
                "ABCCatFunctor",
                ABCCat,
                bool, # ant_left
                typing.Callable[[ABCCat, ElimType], ABCSimplifyRes]
                ]
        ] = deque()
        if (
            isinstance(left_parsed, ABCCatFunctor)
            and left_parsed.func_mode in (
                ABCCatFunctorMode.RIGHT,
                ABCCatFunctorMode.VERT,
            )
        ):
            queue.append(
                (left_parsed, right_parsed, False, lambda x, res: (x, res))
            )
        # === END IF ===

        if (
            isinstance(right_parsed, ABCCatFunctor)
            and right_parsed.func_mode in (
                ABCCatFunctorMode.LEFT,
                ABCCatFunctorMode.VERT,
            )
        ):
            queue.append(
                (right_parsed, left_parsed, True, lambda x, res: (x, res))
                # swapped
            )
        # === END IF ===

        while queue:
            f, v, ant_left, decor = queue.popleft()

            cat_maybe = f.reduce_with(v, ant_left)
            if cat_maybe is None:
                # failed
                # try func comp
                if (
                    isinstance(v, ABCCatFunctor)
                    and v.func_mode == f.func_mode 
                    # NOTE: for crossed-composition this condition will be relaxed.
                ):
                    queue.append(
                        (
                            f,
                            v.conseq,
                            ant_left,
                            lambda x, res, _decor = decor, _f = f, _v = v: _decor(
                                ABCCatFunctor(
                                    func_mode = _v.func_mode,
                                    ant = _v.ant,
                                    conseq = x,
                                ),
                                attr.evolve(
                                    res,
                                    level = res.level + 1
                                )
                            )
                        )
                    )
                else:
                    # no remedy
                    pass
            else:
                etype = ElimType(
                    func_mode = f.func_mode,
                    level = 0,
                )
                yield decor(cat_maybe, etype)
            # === END IF ===
        # === END WHILE queue ===
    # === END ===

    @classmethod
    @functools.lru_cache()
    def simplify_exh(
        cls,
        left: ABCCatReady,
        right: ABCCatReady,
    ) -> typing.Set[ABCSimplifyRes]:
        """
        Return all possible ways of functor elimination 
            of a pair of ABC cateogires, using functor elimination rules
            and functor composition rules.
        Duplicating results are eliminted in the same way as a set does.


        Arguments
        ---------
        left: ABCCatReady
        right: ABCCatReady

        Notes
        -----
        `*` is an alias operator that returns
            the result that is first found
            with simplification details omitted.
        Exceptions arise when it fails. 
        
        Yields
        -------
        cat: ABCCat
            The resulting category.
        res: ElimType
            The details of the simplification process.

        Examples
        --------
        >>> results = list(ABCCat.simplify_exh("A/B", "B/C"))
        >>> cat, details = results[0]
        >>> cat.pprint()
        '<A/C>'
        >>> str(details)
        '>'
        """
        
        return set(cls.simplify(left, right))

    def __mul__(self, others):
        # NOTE: This operator must hinge on `simplify_exh` rather than `simplify` for the proper exploitation of cache, which is not available for the latter.
        try:
            cat, _ = next(iter(ABCCat.simplify_exh(self, others)))
        except StopIteration as e:
            raise ValueError("No application can be applied to the two categories.")
        return cat

    @abst_class.abstractmethod
    def pprint(
        self, 
        mode: ABCCatReprMode = ABCCatReprMode.TLCG
    ) -> str:
        if isinstance(self, ABCCat):
            return self.pprint(mode)
        else:
            return str(self)

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

        # TODO: find alternative of parsy. Still not efficient.

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

class ABCCatTop(ABCCat, Enum):
    """
    Represents the bottom type in the ABC Treebank.
    """
    TOP = "⊤"

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

    def __hash__(self):
        return hash(self.BOT.value)

_re_ABCCat_feature = re.compile(r"(?P<cat>.*?)(?<=[A-Z])(?P<feat>[a-z][a-z0-9]*)")

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

    @functools.lru_cache()
    def pprint(
        self, 
        mode: ABCCatReprMode = ABCCatReprMode.TLCG
    ) -> str:
        if mode == ABCCatReprMode.DEPCCG or mode == ABCCatReprMode.CCG2LAMBDA:
            dict_maybe = self.tell_feature()
            if dict_maybe:
                if mode == ABCCatReprMode.DEPCCG:
                    return f"{dict_maybe['cat']}[{dict_maybe['feat']}]"
                else:
                    return f"{dict_maybe['cat']}[{dict_maybe['feat']}=true]"
            else:
                return self.name
        else:
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

    @functools.lru_cache()
    def tell_feature(self) -> typing.Optional[typing.Dict[str, str]]:
        match = _re_ABCCat_feature.search(self.name)
        if match:
            return match.groupdict()
        else:
            return None
            
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

    @functools.lru_cache()
    def pprint(
        self, 
        mode: ABCCatReprMode = ABCCatReprMode.TLCG
    ) -> str:
        if mode == ABCCatReprMode.DEPCCG:
            if self.func_mode == ABCCatFunctorMode.LEFT:
                return f"({self.conseq.pprint(mode)}\\{self.ant.pprint(mode)})"
            elif self.func_mode == ABCCatFunctorMode.RIGHT:
                return f"({self.conseq.pprint(mode)}/{self.ant.pprint(mode)})"
            elif self.func_mode == ABCCatFunctorMode.VERT:
                return f"({self.conseq.pprint(mode)}|{self.ant.pprint(mode)})"
            else:
                raise ValueError
        elif mode == ABCCatReprMode.CCG2LAMBDA:
            if self.func_mode == ABCCatFunctorMode.LEFT:
                return f"({self.ant.pprint(mode)}\\{self.conseq.pprint(mode)})"
            elif self.func_mode == ABCCatFunctorMode.RIGHT:
                return f"({self.conseq.pprint(mode)}/{self.ant.pprint(mode)})"
            elif self.func_mode == ABCCatFunctorMode.VERT:
                return f"({self.conseq.pprint(mode)}|{self.ant.pprint(mode)})"
            else:
                raise ValueError
        else:
            if self.func_mode == ABCCatFunctorMode.LEFT:
                if mode == ABCCatReprMode.TLCG:
                    return f"<{self.ant.pprint(mode)}\\{self.conseq.pprint(mode)}>"
                else:
                    return f"<{self.conseq.pprint(mode)}\\{self.ant.pprint(mode)}>"
            elif self.func_mode == ABCCatFunctorMode.RIGHT:
                return f"<{self.conseq.pprint(mode)}/{self.ant.pprint(mode)}>"
            elif self.func_mode == ABCCatFunctorMode.VERT:
                return f"<{self.conseq.pprint(mode)}|{self.ant.pprint(mode)}>"
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

    def reduce_with(self, ant: ABCCatReady, ant_left: bool = False) -> typing.Optional[ABCCat]:
        """
        Eliminate the functor with a given antecedent.
        
        Notes
        -----
        Function composition rules are not invoked here.

        Arguments
        ---------
        ant: ABCCatReady
            An antecedent.
        ant_left: bool, default: False
            The position of the ancedecent.
            `True` when it is on the left to the functor. 
        
        Returns
        -------
        conseq: ABCCat or None
            The resulting category. `None` on failure.
        """

        ant_parsed = ABCCat.p(ant)

        if self.ant == ant_parsed:
            if (
                (
                    self.func_mode == ABCCatFunctorMode.LEFT
                    and not ant_left
                ) or (
                    self.func_mode == ABCCatFunctorMode.RIGHT
                    and ant_left
                )
            ):
                # wrong functor-argument arrangement
                return None
            else:
                # reduction successful
                return self.conseq
        else:
            return None

# === END CLASS ===

_parser_ABCCatTop: parsy.Parser = parsy.from_enum(ABCCatTop)
_parser_ABCCatBot: parsy.Parser = parsy.from_enum(ABCCatBot)
_parser_ABCCatBase: parsy.Parser = parsy.regex(r"[^/\\|<>#\s]+").map(ABCCatBase)

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
def _parser_ABCCatFunctor_Vert() -> parsy.Parser:
    stack = yield (
        _parser_ABCCatBot
        | _parser_ABCCatBase
        | _parser_ABCCatFunctor_Left
        | _parser_ABCCatFunctor_Right
        | _parser_ABCCat_group
    ).sep_by(
        parsy.string("|"),
        min = 2,
    )

    return functools.reduce(
        lambda c, a: ABCCatFunctor(
            func_mode = ABCCatFunctorMode.VERT,
            ant = a,
            conseq = c,
        ),
        stack
    )

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
    | _parser_ABCCatFunctor_Vert
    | _parser_ABCCatBot
    | _parser_ABCCatTop
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