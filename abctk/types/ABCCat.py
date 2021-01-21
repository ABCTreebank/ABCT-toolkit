import typing
import functools
import enum

import attr
import parsy

class ABCCatFunctorMode(enum.Enum):
    LEFT = "L"
    RIGHT = "R"
# === END CLASS ===

@attr.s(
    auto_attribs = True, # Unnecessary in newer version of Python
    frozen = True,
    slots = True,
)
class ABCCatFunctor:
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

    def to_string(self, natural_dir: bool = True) -> str:
        if self.mode == ABCCatFunctorMode.LEFT:
            if natural_dir:
                return f"<{self.ant}\\{self.conseq}>"
            else:
                return f"<{self.conseq}\\{self.ant}"
        elif self.mode == ABCCatFunctorMode.RIGHT:
            return f"<{self.conseq}/{self.ant}>"
        else:
            raise ValueError
    # === END ===

    def __str__(self) -> str:
        return self.to_string(natural_dir = True)
    # === END ===
# === END CLASS ===

class ABCCatBot(enum.Enum):
    BOT = "⊥"
# === END CLASS ===

ABCCat = typing.Union[
    str,
    ABCCatFunctor,
    ABCCatBot
]

parser_ABCCatBot: parsy.Parser = parsy.from_enum(ABCCatBot)
parser_ABCCatBase: parsy.Parser = parsy.regex(r"[^/\\<>\s]+")

@parsy.generate
def parser_ABCCatFunctor_Left() -> ABCCatFunctor: 
    que = yield (
        parser_ABCCatBot
        | parser_ABCCatBase
        | parser_ABCCat_group
    ).sep_by(
        parsy.string("\\"),
        min = 2,
    )

    return functools.reduce(
        lambda a, c: ABCCatFunctor(
            mode = ABCCatFunctorMode.LEFT,
            ant = a,
            conseq = c,
        ),
        reversed(que)
    )
# === END ===

@parsy.generate
def parser_ABCCatFunctor_Right() -> ABCCatFunctor:
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

def parse_ABCCat(text: str) -> ABCCat:
    return parser_ABCCat.parse(text)
# === END ===


