import logging

from abctk.types.treebank import Keyaki_ID
logger = logging.getLogger(__name__)
import os
import pathlib
import random
import string
import sys
import tempfile
import typing

import lxml.etree as et

import typer

import abctk.transform_ABC.jigg as jg
import abctk.io.nltk_tree as nt

app = typer.Typer()

@app.callback()
def cmd_main():
    """
    Renumber ABC trees.
    """

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
    fmt: str = typer.Option(
        "{id_orig.number}_{name_random}", 
        help = """
        The format of new IDs. Specified in the Python format string format.
        Available variables: id_orig.name, id_orig.number, id_orig.suffix, id_orig.orig, new_num, name_random
        """
    )
):
    """
    Renumber given trees.
    """

    name_random = "".join(random.choice(string.ascii_letters) for _ in range(6))

    with tempfile.TemporaryDirectory(prefix = "abct_jigg_") as temp_folder:
        source_file: typing.Optional[typing.IO[str]] = None
        dest_file: typing.Optional[typing.IO[str]] = None
        try:
            if source_path.name == "-":
                # load from stdin
                source_file = tempfile.NamedTemporaryFile("w", dir = temp_folder)
                source_file.write(sys.stdin.read())
                logger.info(f"STDIN loaded in {source_file.name}")
            else:
                source_path = source_path.resolve()
                source_file_path = f"{temp_folder}/{source_path.name}"
                os.symlink(source_path, dst = source_file_path)
                logger.info(f"File symlinked to {source_file_path}")

            tb = nt.load_ABC_psd(temp_folder, re_filter = ".*")

            if dest_path.name == "-":
                dest_file = sys.stdout
            else:
                dest_file = open(str(dest_path.resolve()), "w")

            tb_mapped = (
                (
                    Keyaki_ID.from_string(
                        fmt.format(
                            id_orig = id_orig, 
                            new_num = num,
                            name_random = name_random
                        )
                    ),
                    tree
                )
                for num, (id_orig, tree) in enumerate(tb, start = 1)
            )

            dest_file.write(
                "\n".join(
                    nt.flatten_tree_with_ID(ID, tree)
                    for ID, tree in tb_mapped
                )
            )
        finally: 
            if source_file: source_file.close()
            if dest_file: dest_file.close()