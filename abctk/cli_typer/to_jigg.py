import importlib.resources
import logging
logger = logging.getLogger(__name__)

import os
import pathlib
import sys
import tempfile
import typing

import lxml.etree as et
import ruamel.yaml as yaml
import typer

import abctk.transform_ABC.jigg as jg
from abctk.types.ABCCat import ABCCat, ABCCatReprMode
import abctk.io.nltk_tree as nt

app = typer.Typer()

@app.callback()
def cmd_main():
    """
    Convert ABC trees to the JIGG format. Useful for ccg2lambda.
    """

@app.command("treebank")
def cmd_from_treebank(
    ctx: typer.Context,
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
    skip_ill_trees = ctx.obj["CONFIG"]["skip-ill-trees"]

    tb = list(
        nt.load_ABC_psd(
            source_path,
            skip_ill_trees = skip_ill_trees
        )
    )

    xml_root = et.Element("root")
    xml_doc = et.SubElement(xml_root, "document", id = "d0")
    xml_sentences = et.SubElement(xml_doc, "sentences")
    for num, (keyaki_id, tree) in enumerate(tb):
        try:
            xml_sentences.append(
                jg.tree_to_jigg(tree, str(keyaki_id), num)
            )
        except jg.JIGGConvException:
            if skip_ill_trees:
                logger.warning(
                    "An exception was raised by the convertion function. "
                    f"Tree ID: {keyaki_id}. "
                    "The tree will be abandoned."
                )
            else:
                logger.error(
                    "An exception was raised by the convertion function. "
                    f"Tree ID: {keyaki_id}. "
                    "The process has been aborted."
                )
                raise
        except Exception:
            logger.error(
                "An unexpected exception has been raised. The process has been aborted."
            )
            raise

    et.ElementTree(xml_root).write(
        str(dest_path),
        xml_declaration = True,
        encoding = "utf-8",
        pretty_print = True,
    )
        
@app.command("file")
def cmd_from_file(
    ctx: typer.Context,
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
    use_postag: bool = typer.Option(
        True, "--use-postag/--no-use-posttag",
        help = """
        Enable or disable the preparatory POS tagging.
        """
    ),
    postag_path: typing.Optional[pathlib.Path] = typer.Option(
        None, "--postag-path", 
        file_okay = True,
        exists = True,
        help = """
        An additional POS tag dictionary.
        """
    )
):
    """
    Convert ABC Treebank trees coming from STDIN to a JIGG tree file.
    """
    skip_ill_trees = ctx.obj["CONFIG"]["skip-ill-trees"]

    # collect postag rules
    postag = None
    if use_postag:
        if postag_path:
            with open(postag_path) as f_postag:
                postag = yaml.safe_load(f_postag)
        else:
            with importlib.resources.open_text("abctk.ccg2lambda", "semtag.yaml") as f_postag:
                postag = yaml.safe_load(f_postag)
    
        # parse categories beforehand
        for i in range(len(postag)):
            postag[i]["category"] = ABCCat.parse(
                postag[i]["category"],
                ABCCatReprMode.CCG2LAMBDA
            )

    with tempfile.TemporaryDirectory(prefix = "abct_jigg_") as temp_folder:
        temp_file: typing.Optional[typing.IO[str]] = None
        try:
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

            tb = list(
                nt.load_ABC_psd(
                    temp_folder, 
                    re_filter = ".*",
                    skip_ill_trees = skip_ill_trees
                )
            )

            xml_root = et.Element("root")
            xml_doc = et.SubElement(xml_root, "document", id = "d0")
            xml_sentences = et.SubElement(xml_doc, "sentences")
            for num, (keyaki_id, tree) in enumerate(tb):
                try:
                    xml_sentences.append(
                        jg.tree_to_jigg(tree, str(keyaki_id), num, postag)
                    )
                except jg.JIGGConvException:
                    if skip_ill_trees:
                        logger.warning(
                            "An exception was raised by the convertion function. "
                            f"Tree ID: {keyaki_id}. "
                            "The tree will be abandoned."
                        )
                    else:
                        logger.error(
                            "An exception was raised by the convertion function. "
                            f"Tree ID: {keyaki_id}. "
                            "The process has been aborted."
                        )
                        raise
                except Exception:
                    logger.error(
                        "An unexpected exception has been raised. The process has been aborted."
                    )
                    raise
            
            dest_path_str = str(dest_path)
            if dest_path_str == "-":
                sys.stdout.buffer.write(
                    et.tostring(
                        xml_root,
                        xml_declaration = True,
                        encoding = "utf-8",
                        pretty_print = True
                    )
                )
                logger.info("Output XML successfully dumped to STDOUT")
            else:
                et.ElementTree(xml_root).write(
                    dest_path_str,
                    xml_declaration = True,
                    encoding = "utf-8",
                    pretty_print = True,
                )
                logger.info(f"Output XML successfully dumped into {str(dest_path)}")
        finally:
            if temp_file: temp_file.close()