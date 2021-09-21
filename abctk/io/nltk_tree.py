"""
Loaders and dumpers of the Keyaki treebank and the ABC Treebank stored in the CorpusSearch format, 
    which make use of the NLTK tree class for internal representation.
"""

import itertools
import operator
import pathlib
import sys
import typing

import fs
import fs.base
from nltk import Tree
from nltk.corpus.reader.bracket_parse import BracketParseCorpusReader

import abctk.types.ABCCat as abcc
from abctk.types.treebank import Keyaki_ID

def _split_ID_from_Tree(tree) -> typing.Tuple[Keyaki_ID, Tree]:
    if len(tree) == 2:
        child_1, child_2 = tree
        if (
            child_2.label() == "ID" 
            and len(child_2) == 1 
            and isinstance(child_2[0], str)
        ):
            ID = Keyaki_ID.from_string(child_2[0])
            tree = child_1
        else:
            ID = Keyaki_ID.new()
    else:
        ID = Keyaki_ID.new()
    
    return ID, tree

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
    def _parse_label(tree: Tree): 
        stack = [tree]

        while stack:
            pointer = stack.pop()
            if isinstance(pointer, Tree):
                pointer.set_label(abcc.Annot.parse(pointer.label()))
            else:
                # do nothing
                pass
        
    for i, tree in enumerate(
        BracketParseCorpusReader(
            root = str(folder),
            fileids = re_filter,
        ).parsed_sents()
    ):
        ID, content = _split_ID_from_Tree(tree)
        _parse_label(content)
        yield ID, content
        if prog_stream:
            prog_stream.write(f"\r# of tree(s) fetched: {i:,}")

    if prog_stream:
        prog_stream.write("\n")

def load_ABC_psd(
    folder: typing.Union[str, pathlib.Path], 
    re_filter: typing.Union[str, typing.Pattern] = r".*\.psd$",
    prog_stream: typing.Optional[typing.IO[str]] = sys.stderr,
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
    """
    def _parse_label(tree: Tree): 
        stack = [tree]

        while stack:
            pointer = stack.pop()
            if isinstance(pointer, Tree):
                pointer.set_label(
                    abcc.Annot.parse(
                        pointer.label(),
                        #parser_cat = abcc.ABCCat.parse, # NOTE: too slow
                        pprinter_cat = abcc.ABCCat.pprint,
                        # TODO: exclude terminals
                    )
                )

                if len(pointer) == 1:
                    if not isinstance(pointer[0], Tree):
                        continue
                    
                for child in tree:
                    _parse_label(child)
            else:
                # do nothing
                pass

    for i, (ID, tree) in enumerate(
        map(
            _split_ID_from_Tree,
            BracketParseCorpusReader(
                root = str(folder),
                fileids = re_filter,
            ).parsed_sents()
        )
    ):
        _parse_label(tree)
        yield ID, tree

        if prog_stream:
            prog_stream.write(f"\r# of tree(s) fetched: {i:,}")
            
    if prog_stream:
        prog_stream.write("\n")

def dump_Keyaki_to_psd(
    tb: typing.Iterable[typing.Tuple[Keyaki_ID, Tree]],
    folder: typing.Union[str, pathlib.Path, fs.base.FS],
    prog_stream: typing.Optional[typing.IO[str]] = sys.stderr,
) -> None:
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

def dump_ABC_to_psd(
    tb: typing.Iterable[typing.Tuple[Keyaki_ID, Tree]],
    folder: typing.Union[str, pathlib.Path, fs.base.FS],
    prog_stream: typing.Optional[typing.IO[str]] = sys.stderr,
) -> None:
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
                        f"(TOP {_flatten_tree(tree)} (ID {ID}))"
                        for ID, tree in trees
                    )
                )
    if prog_stream:
        prog_stream.write("\n")