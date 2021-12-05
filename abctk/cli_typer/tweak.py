import logging
logger = logging.getLogger(__name__)
import os
import pathlib
import sys
import tempfile
import typing


import fs
from tqdm.auto import tqdm
import typer
from nltk.tree import Tree

import abctk.io.nltk_tree as nt
import abctk.transform_ABC.norm as norm


from abctk.transform_ABC.elim_empty import elim_empty_terminals
from abctk.transform_ABC.elim_trace import restore_rel_trace

TreeFunc = typing.Callable[
    [Tree, str],
    typing.Any
]
_COMMAND_TABLE: typing.Dict[str, typing.Tuple[TreeFunc, str]] = {
    "bin-conj": (
        lambda tree, ID: NotImplemented,
        "binarize conjunctions",
    ),
    "flatten-conj": (
        lambda tree, ID: NotImplemented,
        "flatten conjunctions"
    ),
    "elim-empty": (
        elim_empty_terminals,
        "eliminate empty nodes"
    ),
    "restore-empty": (
        lambda tree, ID: NotImplemented,
        "restore empty nodes"
    ),
    "elim-trace": (
        lambda tree, ID: NotImplemented,
        "eliminate traces",
    ),
    "restore-trace": (
        restore_rel_trace,
        "restore traces",
    ),
    "janome": (
        lambda tree, ID: NotImplemented,
        "add janome morphological analyses",
    ),
    "del-janome": (
        lambda tree, ID: NotImplemented,
        "delete janome morphological analyses",
    ),
    "min-nodes": (
        lambda tree, ID: NotImplemented,
        "minimize nodes",
    ),
    "elab-nodes": (
        lambda tree, ID: NotImplemented,
        "elaborate nodes",
    ), 
    "obfus": (
        lambda tree, ID: NotImplemented,
        "obfuscate trees",
    )
}
app = typer.Typer()

@app.callback()
def cmd_main():
    """
    Tweak ABC trees.
    """

@app.command("treebank")
def cmd_from_treebank(
    source_path: pathlib.Path = typer.Argument(
        ...,
        help = """
        The path to the ABC Treebank.
        """
    ),
    dest_path: pathlib.Path = typer.Argument(
        ...,
        help = """
        The destination.
        """
    ),
    commands: typing.List[str] = typer.Argument(
        ...,
        help = """
        A list of commands to execute upon each tree.
        """
    )
):
    """
    Tweak the ABC Treebank as a whole.
    """

    # parse commands
    logger.info("Start parsing commands")

    # load trees
    tb = list(nt.load_ABC_psd(source_path))

    for ID, tree in tqdm(tb, desc = "Tweaking ABC trees"):
        for com in commands:
            func, desc = _COMMAND_TABLE[com]
            
            logger.info(f"Command: {desc}")
            # apply tweaks
            func(tree, ID)

    with fs.open_fs(str(dest_path), create = True) as folder:
        nt.dump_ABC_to_psd(tb, folder)
        
@app.command("file")
def cmd_from_file(
    source_path: pathlib.Path = typer.Argument(
        ...,
        file_okay = True,
        dir_okay = False,
        allow_dash = True,
        help = """
        The path to the input file. `-` indicates STDIN.
        """
    ),
    dest_path: pathlib.Path = typer.Argument(
        ...,
        file_okay = True,
        dir_okay = False,
        allow_dash = True,
        help = """
        The destination. `-` indicates STDOUT.
        """
    ),
    commands: typing.List[str] = typer.Argument(
        ...,
        help = """
        A list of commands to execute upon each tree.
        """
    )
):
    with tempfile.TemporaryDirectory(
        prefix = "abct_tweak_"
    ) as temp_folder:
        source_file: typing.Optional[typing.IO[str]] = None
        dest_file: typing.Optional[typing.IO[str]] = None
        try:
            if source_path.name == "-":
                source_file = tempfile.NamedTemporaryFile("w", dir = temp_folder)
                source_file.write(sys.stdin.read())
                logger.info(f"STDIN loaded in {source_file.name}")
            else:
                source_path = source_path.resolve()
                source_file_path = f"{temp_folder}/{source_path.name}"
                os.symlink(source_path, dst = source_file_path)
                logger.info(f"File symlinked to {source_file_path}")

            tb = list(nt.load_ABC_psd(temp_folder, re_filter = ".*"))

            if dest_path.name == "-":
                dest_file = sys.stdout
            else:
                dest_file = open(str(dest_path.resolve()), "w")

            for ID, tree in tqdm(tb, desc = "Tweaking ABC trees"):
                for com in commands:
                    func, desc = _COMMAND_TABLE[com]
                    
                    logger.info(f"Command: {desc}")
                    # apply tweaks
                    func(tree, ID)

                # dump the tree
                dest_file.writelines(
                    (
                        nt.flatten_tree_with_ID(
                            ID, tree
                        ),
                        "\n",
                    )
                )
        finally:
            if source_file: source_file.close()
            if dest_file: dest_file.close()