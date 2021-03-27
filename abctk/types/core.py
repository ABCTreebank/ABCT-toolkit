from abc import ABC, abstractmethod
import collections
import concurrent.futures as cf
import functools
import itertools
import logging
logger = logging.getLogger(__name__)
import multiprocessing as mp
import os
import random
import re
import string
from packaging.version import Version
import pathlib
import typing

import attr
import fs
import humanize
import lark
import tqdm

import abctk.config

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

def _load_file(
    args: typing.Tuple[str, int, str],
    disambiguate_IDs_by_path: bool,
    uniformly_with_ID: bool,
) -> typing.Tuple[
    str, # path
    int, # size
    int, # status
    typing.Tuple[typing.Tuple[str, TypedTree[str, str]]],
]:
    path, size, content = args
    res = tuple(
        (
            f"{path}/{k}"
                if disambiguate_IDs_by_path
                else k,
            v,
        )
        for k, v in typing.cast(
            typing.Iterable[
                typing.Tuple[
                    str, TypedTree[str, str],
                ]
            ],
            typing.cast(
                lark.Lark,
                get_TypedTree_LarkParser() # type: ignore
            ).parse(
                content,
                start = (
                    "tree_with_id_list" if uniformly_with_ID
                    else "tree_maybe_with_id_list"
                )
            )
        )
    )

    return path, size, 0, res
# === END ===

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
        uniformly_with_ID: bool = True,
    ):
        return cls(
            name,
            version,
            container_version,
            index = typing.cast(  # type: ignore
                TypedTreeIndex[str, str, str],
                get_TypedTree_LarkParser().parse(
                    source,
                    start = (
                        "tree_with_id_list" if uniformly_with_ID
                        else "tree_maybe_with_id_list"
                    )
                )
            ) 
        )
    # === END ===

    @classmethod
    def from_PTB_FS(
        cls,
        filesys: "fs.base.FS",
        name: typing.Optional[str]      = None,
        glob_str: str                   = "**/*.psd",
        disambiguate_IDs_by_path: bool  = False,
        version: Version                = Version("0.0.0"),
        container_version: Version      = Version("0.0.0"),
        process_num: int                = typing.cast(int, abctk.config.CONF_DEFAULT["max_process_num"]),
        tqdm_buffer: typing.Optional[typing.TextIO] = None,
        uniformly_with_ID: bool = True,
    ):
        # ------------
        # 1. Collect files and their info
        # ------------
        glob_matches = filesys.glob(glob_str)
        file_paths = tuple(
            match.path for match in glob_matches
        )
        file_sizes = tuple(
            filesys.getinfo(path, ("details", )).size
            for path in file_paths  
        )
        file_num = len(file_paths)
        file_size_sum = sum(file_sizes)
        logger.info(
            f"# of files to be loaded: {file_num}, "
            f"the total size: {humanize.naturalsize(file_size_sum)}"
        )

        # ------------
        # 2. Making a file reading iterator
        # ------------
        def _read_file(filesys: "fs.base.FS", path: str):
            with filesys.open(path, "r") as f:
                return f.read()
        # === END ===

        file_contents = (
            _read_file(filesys, path) 
            for path in file_paths
        ) # As iterator, actual IO made delayed

        # ------------
        # 3. Launch a multiprocessing context
        # -----------
        result_tree_iters = list()
        with cf.ProcessPoolExecutor(
            max_workers = process_num
        ) as executor:
            logger.info(f"Multiprocessing pool created, number of processes: {process_num}")

            with tqdm.tqdm(
                total = file_size_sum,
                desc = "Reading & parsing treebank files",
                unit = "B",
                unit_scale = True,
                file = tqdm_buffer,
                disable = tqdm_buffer is None,
            ) as bar:
                for _, size, _, trees in executor.map(
                    functools.partial(
                        _load_file,
                        disambiguate_IDs_by_path = disambiguate_IDs_by_path,
                        uniformly_with_ID = uniformly_with_ID,
                    ),
                    zip(
                        file_paths,
                        file_sizes,
                        file_contents,
                    )
                ):
                    bar.update(size)
                    result_tree_iters.append(trees)

        return cls(
            name if name is not None else str(filesys),
            version,
            container_version,
            index = dict(itertools.chain.from_iterable(result_tree_iters))
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

_treeID_path_matcher = re.compile(r"^(.*)?/(.*)$")

def treeIDstr_to_path_default(ID: str) -> typing.Tuple[str, str]:
    ID_str = str(ID)
    res = _treeID_path_matcher.match(ID_str)
    if res is None:
        return ("", ID_str)
    else:
        return typing.cast(
            typing.Tuple[str, str],
            res.group(1, 2),
        )
    # === END ===
# === END ===

# ======
# Lark Parsers
# ======

larkgramamr_TypedTree = r"""
%import common.WS
%ignore WS

tree_simple: TERM
label: NONTERM?
tree_complex: "(" label tree* ")"
tree: tree_simple | tree_complex

tree_list: tree*
tree_with_id_list: tree*
tree_maybe_with_id_list: tree*

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

    def tree_list(
        self,
        args: typing.List[TypedTree[str, str]],
    ) -> typing.List[TypedTree[str, str]]:
        return args

    def tree_with_id_list(
        self,
        args: typing.List[TypedTree[str, str]]
    ) -> typing.Iterator[typing.Tuple[str, TypedTree[str, str]]]:
        def _extract_ID(tree: TypedTree[str, str]):
            content, ID_node = tree.children
            assert ID_node.root == "ID"
            return ID_node.children[0].root, content
        # === END ===
        return map(_extract_ID, args)
    # === END ===
    
    def tree_maybe_with_id_list(
        self,
        args: typing.List[TypedTree[str, str]]
    ) -> typing.Iterator[
        typing.Tuple[
            typing.Optional[str],
            TypedTree[str, str]
        ]
    ]:
        def _extract_ID(tree: TypedTree[str, str]):
            if len(tree.children) == 2:
                content, ID_node = tree.children
                if ID_node.root == "ID" and len(tree.children) == 1:
                    ID = ID_node.children[0].root
                    return ID, content
                else:
                    return None, content
            else:
                return None, content
            # === END IF ===
        # === END ===
        return map(_extract_ID, args)
    # === END ===

@functools.lru_cache()
def get_TypedTree_LarkParser() -> lark.Lark:
    return lark.Lark(
        grammar = larkgramamr_TypedTree,
        transformer = TypedTree_lark_Transformer(),
        start = [
            "tree", 
            "tree_list",
            "tree_with_id_list", 
            "tree_maybe_with_id_list"
        ],
        parser = "lalr",
        cache = True,
    )