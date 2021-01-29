import typing
import enum

import attr
import parsy

import lxml.etree as le
from . import jigg

class ABCDepMarking(enum.Enum):
    NONE = ""
    HEAD = "h"
    COMPLEMENT = "c"
    ADJUNCT = "a"
    ADJUNCT_CONTROL = "ac"
# === END CLASS ===

T = typing.TypeVar("T")
@attr.s(
    auto_attribs = True, # Unnecessary in newer version of Python
)
class ABCCatPlus(typing.Generic[T]):
    cat: T
    role: ABCDepMarking = attr.ib(
        default = ABCDepMarking.NONE
    )
    deriv: str = attr.ib(
        default = ""
    )

    def to_jigg(
        self,
        counter: int = 0,
        label_prefix: str = "",
        **args,
    ) -> jigg.Results_Jigg:
        label_id: str = f"{label_prefix}ABCLabel{counter}"

        res: "le._Element" = le.Element(
            "ABCLabel",
            id = label_id,
            cat = str(self.cat),
            role = self.role.value,
            deriv = self.deriv,
        )

        return jigg.Results_Jigg(
            counter_incr = counter,
            attrs_to_be_added = (
                ("ABCLabelInfo", label_id), 
            ),
            elems = (
                ("ABCLabels", res),
            )
        )
    # === END ===

    def __str__(self) -> str:
        others = "".join(
            f"#{k}={v}"
            for k, v in self.__dict__.items()
            if k not in ["role", "deriv"]
        )

        return f"{self.cat}#role={self.role.value}#deriv={self.deriv}{others}"
    # === END ===
# === END CLASS ===

@parsy.generate
def parser_ABCCatPlus_AttrVal() -> parsy.Parser:
    yield parsy.string("#")
    attr = yield parsy.regex(r"[^=\s]+")
    yield parsy.string("=")
    if attr == "role":
        val = yield parsy.from_enum(ABCDepMarking)
    else:
        val = yield parsy.regex(r"[^#\s]*")
    # === END IF ===
    
    return (attr, val)
# === END ===

def parser_ABCCatPlus(
    parser_cat: parsy.Parser = parsy.regex(r"[^#\s]*")
) -> parsy.Parser:
    @parsy.generate
    def _parser():
        cat = yield parser_cat
        attrvals = yield parser_ABCCatPlus_AttrVal.many().map(dict)

        role: ABCDepMarking = attrvals.pop("role", ABCDepMarking.NONE)
        deriv: str = attrvals.pop("deriv", "")

        res: ABCCatPlus = ABCCatPlus(
            cat = cat,
            role = role,
            deriv = deriv,
        )
        
        for key, val in attrvals.items():
            setattr(res, key, val)
        # === END FOR key, val ===
    
        return res
    # === END ===

    return _parser
# === END ===