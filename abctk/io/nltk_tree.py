"""
Loaders and dumpers of the Keyaki treebank and the ABC Treebank stored in the CorpusSearch format, 
    which make use of the NLTK tree class for internal representation.
"""

import itertools
import logging
logger = logging.getLogger(__name__)
import operator
import pathlib
import sys
import typing

import fs
import fs.base
from nltk import Tree
from nltk.corpus.reader.bracket_parse import BracketParseCorpusReader

from abctk import ABCTException
import abctk.obj.ABCCat as abcc
from abctk.obj.Keyaki import Keyaki_ID

def _split_ID_from_Tree(tree) -> typing.Tuple[Keyaki_ID, Tree]:
    if len(tree) >= 2:
        child_body, child_last = tree[:-1], tree[-1]
        if (
            child_last.label() == "ID" 
            and len(child_last) == 1 
            and isinstance(child_last[0], str)
        ):
            ID = Keyaki_ID.from_string(child_last[0])
            if len(child_body) == 1:
                tree = child_body[0]
            else:
                tree = Tree(node = "", children = child_body)
        else:
            ID = Keyaki_ID.new()
    
    else:
        ID = Keyaki_ID.new()
    
    return ID, tree


def parse_all_labels_Keyaki_Annot(
    tree: Tree
):
    '''
    Parses all labels of a tree into `abcc.Annot` objects.
    The tree is modified in situ.
    
    Parameters
    ----------
    tree : Tree
    '''
    stack = [tree]

    while stack:
        pointer = stack.pop()
        if isinstance(pointer, Tree):
            pointer.set_label(abcc.Annot.parse(pointer.label()))
        else:
            # do nothing
            pass

def load_Keyaki_Annot_psd(
    folder: typing.Union[str, pathlib.Path], 
    re_filter: str = r".*\.psd$",
    prog_stream: typing.Optional[typing.IO[str]] = sys.stderr,
) -> typing.Iterator[typing.Tuple[Keyaki_ID, Tree]]:
    """
    Utilizing NLTK, load the Keyaki Treebank with additional annotations for the ABC Treebank.
    
    Parameters
    ----------
    folder

    re_filter

    prog_stream:
        The stream where the progress info is redirected to and show up there.
        Feature disabled when set to `None`. 
    """
    for i, tree in enumerate(
        BracketParseCorpusReader(
            root = str(folder),
            fileids = re_filter,
        ).parsed_sents()
    ):
        ID, content = _split_ID_from_Tree(tree)
        parse_all_labels_Keyaki_Annot(content)
        yield ID, content
        if prog_stream:
            prog_stream.write(f"\r# of tree(s) fetched: {i:,}")

    if prog_stream:
        prog_stream.write("\n")

class InvalidABCTreeException(ABCTException):
    """
    The exception class for ABC tree loading.
    """

    ID: typing.Union[Keyaki_ID, str]
    """ 
    The ID of the problematic tree.
    """

    def __init__(self, ID):
        self.ID = ID
        super().__init__(f"Failed to parse the ABC tree (ID: {ID})")

def parse_all_labels_ABC(
    tree: Tree
):
    '''
    Takes a tree and recursively parses the labels of all the nodes 
        as ABC categories (with annotations).
        The tree is modified in situ.
    
    Parameters
    ----------
    tree : Tree
    '''

    stack = [tree]

    while stack:
        pointer = stack.pop()
        if isinstance(pointer, Tree):
            pointer.set_label(
                abcc.Annot.parse(
                    pointer.label(),
                    parser_cat = abcc.ABCCat.parse, # NOTE: too slow
                    pprinter_cat = abcc.ABCCat.pprint,
                )
            )

            if len(pointer) == 1 and not isinstance(pointer[0], Tree):
                continue
            else:
                stack.extend(pointer)
        else:
            # do nothing
            pass


def load_ABC_psd(
    folder: typing.Union[str, pathlib.Path], 
    re_filter: typing.Union[str, typing.Pattern] = r".*\.psd$",
    prog_stream: typing.Optional[typing.IO[str]] = sys.stderr,
    skip_ill_trees: bool = True,
) -> typing.Iterator[typing.Tuple[Keyaki_ID, Tree]]:
    """
    Utilizing NLTK, load the ABC Treebank.
    
    Parameters
    ----------
    folder

    re_filter

    prog_stream:
        The stream where the progress info is redirected to and show up there.
        Feature disabled when set to `None`. 

    skip_ill_trees:
        If True, try discarding ill-formed trees and continuing the process.

    Yields
    ------
    ID: Keyaki_ID
    tree: Tree

    Raises
    ------
    InvalidABCTreeException
        If parsing of the given tree of categories therein fails.
    """

    corpus_reader = BracketParseCorpusReader(
        root = str(folder),
        fileids = re_filter,
    )

    fileids = corpus_reader.fileids()

    if fileids:
        logger.info(
            f"With the filter {re_filter}, the following file(s) are read: {corpus_reader.fileids()}"
        )

        for i, (ID, tree) in enumerate(
            _split_ID_from_Tree(tree_raw)
            for tree_raw in corpus_reader.parsed_sents()
        ):
            try:
                parse_all_labels_ABC(tree)
                yield ID, tree

                if prog_stream:
                    prog_stream.write(f"\r# of tree(s) fetched: {i + 1:,}")
            except Exception as e:
                if skip_ill_trees:
                    logger.warning(
                        f"An exception has been raised in parsing the nodes of Tree {ID}. The tree will be discarded. Info: {e}"
                    )
                else:
                    logger.error(
                        f"An exception has been raised in parsing the nodes of Tree {ID}. The process will halt and the exception will be tossed up.",
                        exc_info = True,
                        stack_info = True,
                    )
                    raise InvalidABCTreeException(ID) from e

        if prog_stream:
            prog_stream.write("\n")
    else:
        logger.info(
            f"No file is read with the specified filter '{re_filter}'. No trees will be yielded."
        )

def dump_Keyaki_to_psd(
    tb: typing.Iterable[typing.Tuple[Keyaki_ID, Tree]],
    folder: typing.Union[str, pathlib.Path, fs.base.FS],
    prog_stream: typing.Optional[typing.IO[str]] = sys.stderr,
) -> None:
    '''
    Takes a bunch of Keyaki trees, and dumps them into a folder.
    
    Parameters
    ----------
    tb
        A stream of tuples of a tree ID and a tree,
    folder
        The folder to dump the trees to.
    prog_stream
        A stream to write progress to (using tqdm).
    '''
    def _flatten_tree(tree: typing.Union[Tree, str]):
        if isinstance(tree, Tree):
            label = tree.label()
            if isinstance(label, abcc.Annot):
                label_pprint = label.pprint()
            else:
                label_pprint = str(label)

            children_pprint = " ".join(
                _flatten_tree(child) for child in tree
            )
            return f"({label_pprint} {children_pprint})"
        else:
            return str(tree)

    bucket = list(tb)

    bucket.sort(key = operator.itemgetter(0))
    bucket_grouped = itertools.groupby(
        bucket,
        key = lambda x: x[0].name,
    )

    if isinstance(folder, pathlib.Path):
        folder = str(folder)
    
    with fs.open_fs(folder, create = True) as h_folder:
        for file_name, trees in bucket_grouped:
            file_path = Keyaki_ID.from_string("0_" + file_name).tell_path()

            h_folder.makedir(fs.path.dirname(file_path), recreate = True)
            with h_folder.open(file_path, "w") as h_file:
                h_file.write(
                    "\n".join(
                        f"(TOP {_flatten_tree(tree)} (ID {ID}))"
                        for ID, tree in trees
                    )
                )
    if prog_stream:
        prog_stream.write("\n")

def flatten_tree(tree: typing.Union[Tree, str]):
    '''
    Flatten a tree and return its Penn Treebank representation.
    
    Parameters
    ----------
    tree
        The tree to flatten.
    
    Returns
    -------
        A Penn Treebank representation of the tree.
    '''

    if isinstance(tree, Tree):
        label = tree.label()
        if isinstance(label, abcc.Annot):
            label_pprint = label.pprint()
        else:
            label_pprint = str(label)

        children_pprint = " ".join(
            flatten_tree(child) for child in tree
        )
        return f"({label_pprint} {children_pprint})"
    else:
        return str(tree)

def flatten_tree_with_ID(ID: Keyaki_ID, tree: typing.Union[Tree, str]):
    '''
    Flatten a tree in the Penn Treebank format with the ID attached to the top node
    
    Parameters
    ----------
    ID

    tree
    
    Returns
    -------
        An Penn Treebank representation of the tree.
    
    '''
    return f"(TOP {flatten_tree(tree)} (ID {ID}))"

def dump_ABC_to_psd(
    tb: typing.Iterable[typing.Tuple[Keyaki_ID, Tree]],
    folder: typing.Union[str, pathlib.Path, fs.base.FS],
    prog_stream: typing.Optional[typing.IO[str]] = sys.stderr,
) -> None:
    
    '''
    Takes a bunch of ABC trees, and dumps them into a folder.
    
    Parameters
    ----------
    tb
        A stream of tuples of a tree ID and a tree,
    folder
        The folder to dump the trees to.
    prog_stream
        A stream to write progress to (using tqdm).
    '''

    bucket = list(tb)
    bucket.sort(key = operator.itemgetter(0, 1))
    bucket_grouped = itertools.groupby(
        bucket,
        key = lambda x: x[0].name,
    )

    if isinstance(folder, pathlib.Path):
        folder = str(folder)
    
    with fs.open_fs(folder, create = True) as h_folder:
        for file_name, trees in bucket_grouped:
            file_path = Keyaki_ID.from_string("0_" + file_name).tell_path()

            h_folder.makedir(fs.path.dirname(file_path), recreate = True)
            with h_folder.open(file_path, "w") as h_file:
                h_file.write(
                    "\n".join(
                        flatten_tree_with_ID(ID, tree)
                        for ID, tree in trees
                    )
                )
    if prog_stream:
        prog_stream.write("\n")