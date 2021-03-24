from abc import ABC, abstractmethod
import collections
import functools
import itertools
import random
import string
from packaging.version import Version
import pathlib
import typing

import attr
import fs
import lark

class IPrettyPrintable(ABC):
    """
    An interface of the pretty printer of :class:`TypedTree` s
    along with their components.

    
    """
    @abstractmethod
    def pprint(
        self,
        **kwargs,
    ) -> str:
        if isinstance(self, str):
            return self
        elif self is None:
            return "None"
        elif isinstance(self, IPrettyPrintable):
            # Call their own pprint
            return self.pprint(**kwargs)
        else:
            raise TypeError
    # === END ===
# === END CLASS ===
IPrettyPrintable.register(str)

_X = typing.TypeVar("_X")
_X1 = typing.TypeVar("_X1")
_X2 = typing.TypeVar("_X2")

NT = typing.TypeVar("NT", str, IPrettyPrintable)
_NT_new = typing.TypeVar("_NT_new", str, IPrettyPrintable)
T       = typing.TypeVar("T", str, IPrettyPrintable)
_T_new  = typing.TypeVar("_T_new", str, IPrettyPrintable)
NT_or_T = typing.Union[NT, T]

@attr.s(
    auto_attribs = True
)
class TypedTree(
    typing.Generic[NT, T],
    IPrettyPrintable,
):
    root: NT_or_T
    children: typing.Sequence["TypedTree[NT, T]"] = attr.ib(
        factory = list
    )

    def is_terminal(self):
        return len(self.children) == 0
    # === END ===

    def is_root_type_rigid(self):
        return isinstance(
            self.root,
            T if self.is_terminal() else NT
        )
    # === END ===
    
    def iter_df_bottomup(
        self,
        include_term: bool = True,
    ) -> typing.Iterator[NT_or_T]:
        if include_term or not self.is_terminal():
            yield from itertools.chain.from_iterable(
                c.iter_df_bottomup(include_term)
                for c in self.children
            )
        yield self.root

    def iter_df_topdown(
        self,
        include_term: bool = True,
    ) -> typing.Iterator[NT_or_T]:
        yield self.root
        if include_term or not self.is_terminal():
            yield from itertools.chain.from_iterable(
                c.iter_df_topdown(include_term)
                for c in self.children
            )
    def iter_nonterms(self) -> typing.Iterator[NT_or_T]:
        return self.iter_df_topdown(include_term = False)

    def iter_terms(self) -> typing.Iterator[NT_or_T]:
        if self.is_terminal():
            yield self.root
        else:
            yield from itertools.chain.from_iterable(
                c.iter_terms() for c in self.children
            )
    
    def iter_bf_bottomup(
        self,
        include_term: bool = True,
    ) -> typing.Iterator[NT_or_T]:
        raise NotImplementedError

    def iter_bf_topdown(
        self,
        include_term: bool = True,
    ) -> typing.Iterator[NT_or_T]:
        raise NotImplementedError

    def fmap(
        self,
        func_nonterm: typing.Callable[[NT_or_T], _NT_new],
        func_term: typing.Callable[[NT_or_T], _T_new],
    ) -> "TypedTree[_NT_new, _T_new]":
        root = self.root
        root_new: typing.Union[_NT_new, _T_new]
        if self.is_terminal():
            root_new = func_term(root)
        else:
            root_new = func_nonterm(root)
        
        return TypedTree(
            root = root_new,
            children = tuple(
                c.fmap(func_nonterm, func_term)
                for c in self.children
            )
        )

    def fold(
        self, func: typing.Callable[[NT_or_T, typing.Iterable[_X1]], _X1]
    ) -> _X1:
        children_folded = (
            c.fold(func) for c in self.children
        )
        return func(self.root, children_folded)

    def depth(self) -> int:
        raise NotImplementedError

    def pprint(self, **kwargs) -> str:
        is_oneline = kwargs.get("is_oneline", False)
        indent_current = kwargs.get("indent_current", 0)
        indent_amount = kwargs.get("indent_amount", 2)

        root_str = IPrettyPrintable.pprint(
            self.root,
            is_oneline = is_oneline,
            indent_current = indent_current,
            indent_amount = indent_amount,
        )

        if self.is_terminal():
            return root_str
        else:
            children_str: str
            if is_oneline:
                children_str = " ".join(
                    c.pprint(
                        is_oneline = is_oneline,
                        indent_current = indent_current,
                        indent_amount = indent_amount,
                    )
                    for c in self.children
                )
                return f"({root_str} {children_str})"
            else:
                children_str = "\n".join(
                    c.pprint(
                        is_oneline = is_oneline,
                        indent_current = indent_current + indent_amount,
                        indent_amount = indent_amount,
                    )
                    for c in self.children
                )
                return (
                    ' ' * indent_current 
                    + f"({root_str}\n{children_str}\n)"
                )

    def __str__(self) -> str: 
        return self.pprint(is_oneline = True)

    @staticmethod
    def from_PTB(source: str):
        return typing.cast(
            TypedTree[str, str],
            get_TypedTree_LarkParser().parse(
                source,
                start = "tree",
            )
        )
# === ENE CLASS ===

I = typing.TypeVar("I", str, typing.Hashable)
TypedTreeIndex = typing.Mapping[I, TypedTree[NT, T]]

def gen_random_ID_of_str_against_TypedTreeIndex(
    keys: typing.Iterable[str],
    base: str = string.ascii_letters + string.digits,
    length: int = 12
) -> str:
    id_rand: str
    while True:
        id_rand = ''.join(
            random.choices(base, k = length)
        )
        if id_rand not in keys:
            return id_rand
        # === END IF ===
    # === END ===

def sample_from_TypedTreeIndex(
    index: TypedTreeIndex[I, NT, T],
    k: int,
) -> typing.List[I]:
    return random.sample(
        population = index.keys(),
        k = k,
    )

@attr.s(
    auto_attribs = True,
    # slots = True, -- error in Python 3.6, see https://github.com/python-attrs/attrs/issues/313
)
class TypedTreebank(
    typing.Generic[I, NT, T],
):
    name: str
    version: Version
    container_version: Version
    index: TypedTreeIndex[I, NT, T]

    @classmethod
    def from_PTB(
        cls,
        source: str,
        name: str,
        version: Version = Version("0.0.0"),
        container_version: Version = Version("0.0.0"),
    ):
        return cls(
            name,
            version,
            container_version,
            index = typing.cast(
                TypedTreeIndex[str, str, str],
                get_TypedTree_LarkParser().parse(
                    source,
                    start = "tree_maybe_with_id_list"
                )
            )
        )
    # === END ===

    @classmethod
    def from_PTB_FS(
        cls,
        filesys: "fs.base.FS",
        name: typing.Optional[str] = None,
        glob_str: str = "**/*.psd",
        disambiguate_IDs_by_path: bool = False,
        version: Version = Version("0.0.0"),
        container_version: Version = Version("0.0.0"),
    ):
        def _yielder(match: fs.glob.GlobMatch):
            with filesys.open(match.path) as f:
                return (
                    (
                        f"{match.path}/{k}"
                            if disambiguate_IDs_by_path
                            else k,
                        v,
                    )
                    for k, v in typing.cast(
                        TypedTreeIndex[str, str, str],
                        typing.cast(
                            lark.Lark,
                            get_TypedTree_LarkParser()
                        ).parse(
                            f.read(),
                            start = "tree_maybe_with_id_list"
                        )
                    ).items()
                )
        
        return cls(
            name if name is not None else str(filesys),
            version,
            container_version,
            index = dict(
                itertools.chain.from_iterable(
                    map(_yielder, filesys.glob(glob_str))
                )
            )
        )
    # === END ===

    def to_PTB_FS(
        self,
        filesys: "fs.base.FS",
        path_maker: typing.Callable[
            [I], 
            typing.Tuple[str, I],
        ] = (
            lambda i: ("untitled.psd", i)
        ),
    ) -> None:
        # preparing index
        index_prepared = itertools.groupby(
            sorted(
                (
                    (path_maker(k), v)
                    for k, v in self.index.items()
                ),
                key = lambda p: p[0],
            ),
            key = lambda p: p[0][0],
        )
        
        for file_name, subindex in index_prepared:
            with filesys.open(
                file_name,
                mode = "w",
            ) as f:
                f.write(
                    "\n".join(
                        f"( {tree.pprint(is_oneline = True)} (ID {k[1]}))"
                        for k, tree in subindex
                    )
                )

    def to_PTB_single_stream(
        self,
        stream: typing.TextIO,
    ) -> None:
        stream.write(
            "\n".join(
                f"({tree.pprint(is_oneline = True)} (ID {ID}))"
                for ID, tree in self.index.items()
            )
        )

# ======
# Lark Parsers
# ======

TypedTree_lark_grammar = r"""
%import common.WS
%ignore WS

tree_simple: TERM
label: NONTERM?
tree_complex: "(" label tree* ")"
tree: tree_simple | tree_complex

tree_with_id: "(" tree_complex "(" "ID" /[^\s()]+/ ")" ")"
tree_maybe_with_id: tree_with_id | tree
tree_maybe_with_id_list: tree_maybe_with_id*

NONTERM: /[^\s()]+/
TERM: /[^\s()]+/
"""

class TypedTree_lark_Transformer(lark.Transformer):
    def tree_simple(
        self, 
        args: typing.List[lark.Token]
    ) -> TypedTree[str, str]:
        return TypedTree(
            root = " ".join(i.value for i in args),
        )

    def label(self, args: typing.List[lark.Token]) -> str:
        return " ".join(i.value for i in args)

    def tree_complex(
        self, 
        args: typing.List[TypedTree[str, str]]
    ) -> TypedTree[str, str]:
        res = TypedTree(
            root = args[0],
            children = args[1:],
        )
        return res

    def tree(
        self,
        args: typing.List[TypedTree[str, str]],
    ) -> TypedTree[str, str]:
        return args[0]

    def tree_with_id(
        self,
        args: typing.List[typing.Any],
    ) -> typing.Tuple[str, TypedTree[str, str]]:
        return (args[1], args[0])
    # === END ===

    def tree_maybe_with_id(
        self,
        args: typing.List[typing.Any]
    ) -> typing.Tuple[
        typing.Optional[str],
        TypedTree[str, str],
    ]:
        ret = args[0]
        if isinstance(ret, tuple):
            return typing.cast(
                typing.Tuple[str, TypedTree[str, str]],
                ret,
            )
        elif isinstance(ret, TypedTree):
            return None, typing.cast(TypedTree[str, str], ret)
        else:
            raise TypeError
        # === END IF ===
    # === END ===

    def tree_maybe_with_id_list(
        self,
        args: typing.Iterable[
            typing.Tuple[
                typing.Optional[str],
                TypedTree[str, str],
            ]
        ],
    ) -> TypedTreeIndex[str, str, str]:
        set_keys: typing.Set[str] = set()

        def _decide_key(
            pair: typing.Tuple[
                typing.Optional[str],
                TypedTree[str, str]
            ],
            set_keys: typing.Set[str]
        ) -> typing.Tuple[
            str,
            TypedTree[str, str],
        ]:
            key = pair[0]
            if key is None:
                key = gen_random_ID_of_str_against_TypedTreeIndex(
                    keys = set_keys,
                )
            
            set_keys.add(key)
            return (key, pair[1])
        # === END ==

        return dict(
            map(
                lambda pr: _decide_key(pr, set_keys),
                args
            )
        )
    # === END ===

@functools.lru_cache()
def get_TypedTree_LarkParser() -> lark.Lark:
    return lark.Lark(
        grammar = TypedTree_lark_grammar,
        transformer = TypedTree_lark_Transformer(),
        start = ["tree", "tree_maybe_with_id", "tree_maybe_with_id_list"],
        parser = "lalr",
        cache = True,
    )