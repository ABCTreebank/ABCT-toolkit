import pathlib

import lxml.etree as et
import fs
from tqdm.auto import tqdm

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
        
@app.command("stdin")
def cmd_from_stdin():
    """
    
    """

    raise NotImplementedError