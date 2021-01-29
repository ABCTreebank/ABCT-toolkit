import typing
import attr

@attr.s(
    auto_attribs = True, # Unnecessary in newer version of Python
    frozen = True,
    slots = True,
)
class Results_Jigg:
    counter_incr: int
    attrs_to_be_added: typing.Iterable[typing.Tuple[str, str]]
    elems: typing.Iterable[typing.Tuple[str, "le._Element"]]
# === END CLASS ===

Func_to_Jigg = typing.Callable[
    ...,
    Results_Jigg
]