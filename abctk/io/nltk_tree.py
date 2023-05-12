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
from typing import Tuple, Union

import fs
import fs.base
from nltk import Tree
from nltk.corpus.reader.bracket_parse import BracketParseCorpusReader

from abctk import ABCTException
from abctk.obj.ABCCat import ABCCat, Annot
from abctk.obj.ID import RecordID, SimpleRecordID
from abctk.obj.Keyaki import Keyaki_ID
from abctk.obj.comparative import ABCTComp_BCCWJ_ID

X = typing.TypeVar("X", Tree, str)
def split_ID_from_Tree(tree: X) -> Tuple[RecordID, X]:
    '''
    Takes a tree as input, extracts the Keyaki ID from it if it exists, and returns a
    tuple of the ID and the remainder part of the tree.
    
    Returns
    -------
    ID : :class:`RecordID`
    tree: :class:`nltk.Tree`
    '''

    # Check whether there is an ID node available at the root
    if isinstance(tree, Tree) and len(tree) >= 2:
        child_body: list[Tree]= tree[:-1]
        child_last: Tree = tree[-1]
        if (
            child_last.label() == "ID" 
            and len(child_last) == 1 
            and isinstance(child_last[0], str)
        ):
            # If found
            ID_raw: str = child_last[0] # type: ignore
            ID = (
                ABCTComp_BCCWJ_ID.from_string(ID_raw)
                or Keyaki_ID.from_string(ID_raw)
                or SimpleRecordID.from_string(ID_raw)
            )
            
            # Reform the tree
            if len(child_body) == 1:
                tree = child_body[0]
            else:
                tree = Tree(node = "", children = child_body)
        else:
            # If no ID node found
            # Create a default ID
            ID = Keyaki_ID.new()
    else:
        # If no ID node found
        # Create a default ID
        ID = Keyaki_ID.new()
    
    return ID, tree

def parse_all_labels_Keyaki_Annot(
    tree: Tree
):
    '''
    Parses all labels of a tree into :class:`Annot` objects.
    The tree is modified in situ.
    
    Parameters
    ----------
    tree : Tree
    '''
    stack = [tree]

    while stack:
        pointer = stack.pop()
        if isinstance(pointer, Tree):
            pointer.set_label(Annot.parse(pointer.label()))
        else:
            # do nothing
            pass

def load_Keyaki_Annot_psd(
    folder: typing.Union[str, pathlib.Path], 
    re_filter: str = r".*\.psd$",
    prog_stream: typing.Optional[typing.IO[str]] = sys.stderr,
) -> typing.Iterator[typing.Tuple[RecordID, Tree]]:
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
        ID, content = split_ID_from_Tree(tree)
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
    tree: Tree,
    ID: Union[RecordID, str] = "<UNKNOWN>",
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
            label: Union[str, Annot[str]] = pointer.label()

            try:
                if isinstance(label, str):
                    label_parsed: Annot[ABCCat] = Annot.parse(
                        label,
                        parser_cat = ABCCat.parse, # NOTE: too slow
                        pprinter_cat = ABCCat.pprint,
                    )
                else:
                    label_parsed: Annot[ABCCat] = Annot(
                        cat = ABCCat.parse(label.cat),
                        feats = {**label.feats},
                        pprinter_cat = ABCCat.pprint
                    )
                pointer.set_label(label_parsed)
            except Exception as e:
                logging.error(f"Parsing ABC category \"{label}\" failed in function parse_all_labels_ABC. Tree ID: {ID}. Error: {e}")
                raise

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
) -> typing.Iterator[typing.Tuple[RecordID, Tree]]:
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
            split_ID_from_Tree(tree_raw)
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
            if isinstance(label, Annot):
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

def flatten_tree(
    tree: typing.Union[Tree, str],
    hide_all_feats: bool = False,
    feats_to_print: typing.Sequence[str] = tuple(),
    verbose_role: bool = False,
):
    '''
    Flatten a tree and return its Penn Treebank representation.
    
    Parameters
    ----------
    tree
        The tree to flatten.
    verbose_role
        Verbosely print `#role=none` if `True`.
    
    Returns
    -------
        A Penn Treebank representation of the tree.
    '''

    if isinstance(tree, Tree):
        label = tree.label()
        if isinstance(label, Annot):
            label_pprint = label.pprint(
                hide_all_feats = hide_all_feats,
                feats_to_print = feats_to_print,
                verbose_role = verbose_role,
            )
        else:
            label_pprint = str(label)

        children_pprint = " ".join(
            flatten_tree(
                child,
                hide_all_feats = hide_all_feats,
                feats_to_print = feats_to_print,
                verbose_role = verbose_role,
            )
            for child in tree
        )
        return f"({label_pprint} {children_pprint})"
    else:
        return str(tree)

def flatten_tree_with_ID(
    ID: RecordID, 
    tree: typing.Union[Tree, str],
    hide_all_feats: bool = False,
    feats_to_print: typing.Sequence[str] = tuple(),
    verbose_role: bool = False,
):
    '''
    Flatten a tree in the Penn Treebank format with the ID attached to the top node
    
    Parameters
    ----------
    ID
        A tree ID
    tree
        A tree to flatten.

    Returns
    -------
        An Penn Treebank representation of `tree`.
    
    '''
    return f"""(TOP {
        flatten_tree(
            tree, 
            hide_all_feats = hide_all_feats,
            feats_to_print = feats_to_print, 
            verbose_role = verbose_role
        )
    } (ID {ID}))"""

def dump_ABC_to_psd(
    tb: typing.Iterable[typing.Tuple[Keyaki_ID, Tree]],
    folder: typing.Union[str, pathlib.Path, fs.base.FS],
    prog_stream: typing.Optional[typing.IO[str]] = sys.stderr,
    hide_all_feats: bool = False,
    feats_to_print: typing.Sequence[str] = tuple(),
    verbose_role: bool = False,
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
                        flatten_tree_with_ID(
                            ID, 
                            tree, 
                            hide_all_feats = hide_all_feats,
                            feats_to_print = feats_to_print,
                            verbose_role = verbose_role,
                        )
                        for ID, tree in trees
                    )
                )
    if prog_stream:
        prog_stream.write("\n")