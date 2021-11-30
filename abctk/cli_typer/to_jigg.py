import logging
logger = logging.getLogger(__name__)
import os
import pathlib
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
    Normalize ABC trees.
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
):
    """
    Convert the ABC Treebank to the JIGG tree file(s).
    """
    tb = list(nt.load_ABC_psd(source_path))

    xml_root = et.Element("root")
    xml_doc = et.SubElement(xml_root, "document", id = "d0")
    xml_sentences = et.SubElement(xml_doc, "sentences")
    for num, (keyaki_id, tree) in enumerate(tb):
        xml_sentences.append(jg.tree_to_jigg(tree, str(keyaki_id), num))
    et.ElementTree(xml_root).write(
        str(dest_path),
        xml_declaration = True,
        encoding = "utf-8",
        pretty_print = True,
    )
        
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
        help = """
        The destination. `-` is not supported.
        """
    ),
):
    """
    Convert ABC Treebank trees coming from STDIN to a JIGG tree file.
    """

    with tempfile.TemporaryDirectory(prefix = "abct_jigg_") as temp_folder:
        temp_file: typing.Optional[typing.IO[str]] = None
        try:
            print(source_path)
            if source_path.name == "-":
                # load from stdin
                temp_file = tempfile.NamedTemporaryFile("w", dir = temp_folder)
                temp_file.write(sys.stdin.read())
                logger.info(f"STDIN loaded in {temp_file.name}")
            else:
                source_path = source_path.resolve()
                temp_file_path = f"{temp_folder}/{source_path.name}"
                os.symlink(source_path, dst = temp_file_path)
                logger.info(f"File symlinked to {temp_file_path}")

            tb = list(nt.load_ABC_psd(temp_folder, re_filter = ".*"))

            xml_root = et.Element("root")
            xml_doc = et.SubElement(xml_root, "document", id = "d0")
            xml_sentences = et.SubElement(xml_doc, "sentences")
            for num, (keyaki_id, tree) in enumerate(tb):
                xml_sentences.append(jg.tree_to_jigg(tree, str(keyaki_id), num))
            et.ElementTree(xml_root).write(
                str(dest_path),
                xml_declaration = True,
                encoding = "utf-8",
                pretty_print = True,
            )

            logger.info(f"Output XML successfully dumped into {str(dest_path)}")
        finally:
            if temp_file: temp_file.close()