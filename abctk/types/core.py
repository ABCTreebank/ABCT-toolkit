from abc import ABC, abstractmethod
import collections
import concurrent.futures as cf
import enum
import functools
import itertools
import io
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
import more_itertools
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

    _PTB_tokenizer: typing.ClassVar[typing.Pattern] = re.compile(r"([()]|\s+)")
    _PTB_token_WS: typing.ClassVar[typing.Pattern]  = re.compile(r"^\s*$")

    class _PTB_Parser_State(enum.Enum):
        SENTENCE = 0
        SENTENCE_SIMP = 10
        SENTENCE_COMP = 11
        CHILDREN = 20
        YIELD_SENTENCE = 30
        YIELD_MANY_SENTENCES = 31
    # === END CLASS ===
    
    @classmethod
    def take_one_PTB_basic_from_stream(
        cls,
        source: typing.TextIO
    ) -> "TypedTree[str, str]":
        """
        Take one tree from a given stream.
        The rest of the stream is left unconsumed.
        """
        return next(
            cls._parse_PTB_stream(
                source,
                many = False,
                need_EOF = False,
            )
        )
    # === END ===

    @classmethod
    def _parse_PTB_stream(
        cls,
        source: typing.TextIO,
        many: bool = False,
        need_EOF: bool = False,
    ) -> typing.Iterator[
        "TypedTree[str, str]"
    ]:
        """
        An LL(1) parser of penn treebank trees.
        """
        # 1. Tokenization
        tokens = more_itertools.peekable(
            itertools.filterfalse(
                cls._PTB_token_WS.match,
                itertools.chain.from_iterable(
                    map(cls._PTB_tokenizer.split, source)
                )
            )
        )

        # 2. Parsing
        state_stack: typing.List[
            typing.Tuple["TypedTree._PTB_Parser_State", int]
        ] = [
            (
                (
                    cls._PTB_Parser_State.YIELD_MANY_SENTENCES
                    if many else cls._PTB_Parser_State.YIELD_SENTENCE
                ),
                0
            ),
        ]
        return_stack: typing.List[
            typing.Union[
                str,
                TypedTree[str, str],
                typing.Sequence[TypedTree[str, str]],
            ]
        ] = []
        current_token: str

        try:
            while True:
                # print(f"state_stack: {state_stack}\nreturn_stack: {return_stack}")
                #print(f"latest state_stack: {state_stack[-3:]}\nlatest return_stack: {return_stack[-3:]}")
                #next_token = tokens.peek(None)
                #print(f"next_token: {next_token}")
                #print(f"--------")

                # read a token
                # if it reaches EOF, it will raise an IndexErrorException
                current_state, current_resume_pos = state_stack.pop()
                
                if current_state == cls._PTB_Parser_State.YIELD_MANY_SENTENCES:
                    # YIELD_MANY_SENTENCES -> SENTENCE YIELD_MANY_SENTENCES 
                    #                       | EOF
                    if current_resume_pos == 0:
                        # MANY_SENTENCE -> ★0 SENTENCE [1] MANY_SENTENCE [-]
                        #                | ★0 EOF [-]
                        
                        # no token consumption
                        next_token = tokens.peek(None)
                        if next_token:
                            # greedily construct a next tree
                            # if it meets an unexpected EOF, an exception will be raised. The consumed inputs is lost, so the producer should take responsibility for keeping them.
                            # if the stream is not yet complete, it hangs up and waits for next.
                            state_stack.extend(
                                (
                                    (cls._PTB_Parser_State.YIELD_MANY_SENTENCES, 1),
                                    (cls._PTB_Parser_State.SENTENCE, 0),
                                )
                            )
                        else:
                            # EOF
                            # do nothing 
                            pass
                        # === END IF ===
                    elif current_resume_pos == 1:
                        # MANY_SENTENCE -> [0] SENTENCE ★1 MANY_SENTENCE [-]
                        #                | [0] EOF [-]
                        yield typing.cast(
                            TypedTree[str, str],
                            return_stack.pop()
                        )
                        
                        state_stack.append(
                            (cls._PTB_Parser_State.YIELD_MANY_SENTENCES, 0)
                        )
                    else:
                        raise RuntimeError("Illegal state")
                    # === END IF current_resume_pos ===
                elif current_state == cls._PTB_Parser_State.YIELD_SENTENCE:
                    # YIELD_SENTENCE -> SENTENCE 
                    if current_resume_pos == 0:
                        # YIELD_SENTENCE -> ★0 SENTENCE [1]
                        state_stack.extend(
                            (
                                (cls._PTB_Parser_State.YIELD_SENTENCE, 1),
                                (cls._PTB_Parser_State.SENTENCE, 0),
                            )
                        )
                    elif current_resume_pos == 1:
                        # YIELD_SENTENCE -> [0] SENTENCE ★1
                        yield typing.cast(
                            TypedTree[str, str],
                            return_stack.pop()
                        )
                    else:
                        raise RuntimeError("Illegal state")
                elif current_state == cls._PTB_Parser_State.SENTENCE:
                    # SENTENCE -> SENTENCE_COMP
                    #           | SENTENCE_SIMP
                    if current_resume_pos == 0:
                        # SENTENCE -> ★0 SENTENCE_COMP [-]
                        #           | ★0 SENTENCE_SIMP [-]
                        # no token consumption
                        next_token = tokens.peek()
                        if next_token == "(":
                            state_stack.append(
                                (cls._PTB_Parser_State.SENTENCE_COMP, 0)
                            )
                        elif next_token == ")":
                            raise ValueError("Extra ')'!")
                        else:
                            state_stack.append(
                                (cls._PTB_Parser_State.SENTENCE_SIMP, 0)
                            )
                        # === END IF next_token ===
                    else:
                        raise RuntimeError("Illegal state")
                    # === END IF current_resume_pos ===
                elif current_state == cls._PTB_Parser_State.SENTENCE_SIMP:
                    # SENTENCE_SIMP -> word
                    current_token = next(tokens) # consumption
                    return_stack.append(
                        TypedTree(
                            root = current_token,
                            children = []
                        )
                    )
                elif current_state == cls._PTB_Parser_State.SENTENCE_COMP:
                    # SENTENCE_COMP -> "(" root? CHILDREN ")"
                    if current_resume_pos == 0:
                        # SENTENCE_COMP -> ★0 "(" root? CHILDREN [1] ")" [-]

                        # "("
                        current_token = next(tokens) # consumption
                        if current_token == "(": # validate and skip
                            pass
                        else:
                            raise ValueError(
                                f"Wrong token: found: {current_token}, "
                                "expected: )"
                            )
                        # === END IF ===

                        # root?
                        next_token = tokens.peek()

                        if next_token == "(" or next_token == ")":
                            # no label
                            subtree_label = ""
                        else:
                            # consume that token 
                            current_token = next(tokens)
                            # and take it as the label
                            # return a subtree
                            subtree_label = current_token
                        # === END IF ===

                        # Keep the intermediate product
                        return_stack.append(subtree_label)
                        
                        # Go to the next
                        state_stack.extend(
                            (
                                (cls._PTB_Parser_State.SENTENCE_COMP, 1),
                                (cls._PTB_Parser_State.CHILDREN, 0),
                            )
                        )
                    elif current_resume_pos == 1: 
                        # SENTENCE_COMP -> [0] "(" root? CHILDREN ★1 ")" [-]

                        children = typing.cast(
                            typing.Sequence[TypedTree[str, str]],
                            return_stack.pop()
                        )

                        label = typing.cast(
                            str,
                            return_stack.pop()
                        )

                        # ")"
                        current_token = next(tokens) # consumption
                        if current_token == ")": # validate and skip
                            pass
                        else:
                            raise ValueError(
                                f"Wrong token: found: {current_token}, "
                                "expected: )"
                            )
                        # === END IF ===

                        return_stack.append(
                            TypedTree(
                                root = label,
                                children = list(children),
                            )
                        )
                    else:
                        raise RuntimeError("Illegal state")
                    # === END IF current_resume_pos ===
                elif current_state == cls._PTB_Parser_State.CHILDREN:
                    # CHILDREN -> ")" | SENTENCE CHILDREN
                    if current_resume_pos == 0:
                        # CHILDREN -> ★0 ")" 
                        #           | ★0 SENTENCE [1] CHILDREN [2]

                        # peak next token to tell if it's the end
                        next_token = tokens.peek()
                        
                        if next_token == ")":
                            # no more children
                            # give a deque
                            return_stack.append(collections.deque())
                            # convert the queue to a list
                            #return_stack[-1] = list(
                            #    typing.cast(
                            #        typing.Sequence[TypedTree[str, str]],
                            #        return_stack[-1]
                            #    )
                            #)
                        else: 
                            # require one or more child:
                            state_stack.extend(
                                (
                                    (cls._PTB_Parser_State.CHILDREN, 1),
                                    (cls._PTB_Parser_State.SENTENCE, 0),
                                )
                            )
                        # === END IF ===
                    elif current_resume_pos == 1:
                        # CHILDREN -> [0] ")" 
                        #           | [0] SENTENCE ★1 CHILDREN [2]

                        # keep the created child
                        state_stack.extend(
                            (
                                (cls._PTB_Parser_State.CHILDREN, 2),
                                (cls._PTB_Parser_State.CHILDREN, 0),
                            )
                        )
                    elif current_resume_pos == 2:
                        # CHILDREN -> [0] ")" 
                        #           | [0] SENTENCE ★1 CHILDREN [2]
                        
                        # merge children
                        latest_child = typing.cast(
                            TypedTree[str, str],
                            return_stack.pop(-2)
                        )
                        typing.cast(
                            typing.Deque[TypedTree[str, str]],
                            return_stack[-1]
                        ).appendleft(latest_child)
                else:
                    raise RuntimeError(f"Unexpected state: {current_state}")
                # === END IF ===
                
        except StopIteration:
            # End of stream
            raise EOFError
        except IndexError as e:
            if not state_stack:
                # End of parsing

                # Check if it reaches EOF
                if need_EOF:
                    next_token = tokens.peek(None)
                    if next_token is None:
                        pass
                    else:
                        raise ValueError("trailing tokens")
                    # === END IF ===
                # === END IF ==

                # Check if there is no more state remaining
                if state_stack:
                    raise ValueError("trailing tree")
                else:
                    pass
                # === END IF ===
            else:
                raise e
        # === END TRY ===
# === ENE CLASS ===

I = typing.TypeVar("I", str, typing.Hashable)
TypedTreeIndex = typing.Mapping[I, TypedTree[NT, T]]

def get_ID_from_TypedTree(
    tree: TypedTree[str, T]
) -> typing.Tuple[T, TypedTree[str, T]]:
    content, ID_node = tree.children
    ID_node = typing.cast(TypedTree[str, T], ID_node)
    assert ID_node.root == "ID"
    ID_ID_node, = ID_node.children
    return (ID_ID_node.root, content)
# === END ===

def get_ID_maybe_from_TypedTree(
    tree: TypedTree[str, T]
) -> typing.Tuple[typing.Optional[T], TypedTree[str, T]]:
    children = tree.children
    if len(children) == 2:
        content, ID_node = children
        ID_node = typing.cast(TypedTree[str, T], ID_node)
        if ID_node.root == "ID" and len(ID_node.children) == 1:
            return (ID_node.children[0].root, content)
        else:
            return (None, tree)
    else:
        return (None, tree)
# === END ===

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
        for k, v in map(
            (
                get_ID_from_TypedTree 
                if uniformly_with_ID else get_ID_maybe_from_TypedTree
            ),
            TypedTree._parse_PTB_stream(
                io.StringIO(content),
                many = True,
                need_EOF = True,
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
    def from_PTB_basic_stream(
        cls,
        source: typing.TextIO,
        name: str,
        version: Version = Version("0.0.0"),
        container_version: Version = Version("0.0.0"),
        uniformly_with_ID: bool = True,
    ):
        return cls(
            name,
            version,
            container_version,
            index = dict(
                map(
                    (
                        get_ID_from_TypedTree 
                        if uniformly_with_ID 
                        else get_ID_maybe_from_TypedTree
                    ),
                    TypedTree._parse_PTB_stream(
                        source,
                        many = True,
                        need_EOF = True,
                    )
                ),
            ),
        )
    # === END ===

    @classmethod
    def from_PTB_basic_FS(
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
