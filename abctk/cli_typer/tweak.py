import logging
logger = logging.getLogger(__name__)
import os
import pathlib
import re
import sys
import tempfile
import typing

import fs
from tqdm.auto import tqdm
import typer
from nltk.tree import Tree

from abctk.obj.ID import RecordID
from abctk.obj.Keyaki import Keyaki_ID

import abctk.io.nltk_tree as nt
import abctk.transform_ABC.norm
import abctk.transform_ABC.binconj
import abctk.transform_ABC.elim_empty 
import abctk.transform_ABC.elim_trace 
import abctk.transform_ABC.morph_janome
import abctk.check_comp_feat
import abctk.obfuscate
import abctk.gen_comp

# ================
# Command for treebank
# ================
app_treebank = typer.Typer(chain = True)

@app_treebank.callback()
def cmd_from_treebank(
    ctx: typer.Context,
    source_path: pathlib.Path = typer.Argument(
        ...,
        help = """
        The path to the ABC Treebank.
        """
    ),
):
    """
    Tweak the whole ABC Treebank files.

    For more info on each subcommand, 
    run `abctk tweak file /dev/null <COMMAND> --help`.
    """
    # load trees
    tb = list(nt.load_Keyaki_Annot_psd(source_path))

    # store trees in ctx
    ctx.ensure_object(dict)
    ctx.obj["treebank"] = tb

# ================
# Command for single files
# ================
app_file = typer.Typer(chain = True)

@app_file.callback()
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
    )
):
    """
    Tweak a single Treebank file or trees in STDIN.

    For more info on each subcommand, 
    run `abctk tweak file /dev/null <COMMAND> --help`.
    """
    temp_folder = tempfile.TemporaryDirectory(
        prefix = "abct_tweak_"
    )
    source_file: typing.Optional[typing.IO[str]] = None
    try:
        if source_path.name == "-":
            source_file = tempfile.NamedTemporaryFile(
                "w",
                dir = temp_folder.name
            )
            source_file.write(sys.stdin.read())
            source_file.flush()
            logger.info(f"STDIN loaded in {source_file.name}")
        else:
            source_path = source_path.resolve()
            source_file_path = f"{temp_folder.name}/{source_path.name}"
            os.symlink(source_path, dst = source_file_path)
            logger.info(f"File symlinked to {source_file_path}")

        tb = list(nt.load_ABC_psd(str(temp_folder.name), re_filter = ".*"))
        
    finally:
        if source_file: source_file.close()

    # pass to ctx
    ctx.ensure_object(dict)
    ctx.obj["temp_folder"] = temp_folder
    ctx.obj["treebank"] = tb

# ================
# Subcommands
# ================

# ----------------
# General decorators
# ----------------
def lift_func(name: str, bar_desc: str = ""): 
    '''
    A decorator that takes in a tree-modifying function 
    and returns a new function that
    iterates through a treebank 
    and applies the input function to each tree, 
    handling exceptions and logging progress.
    
    Parameters
    ----------
    name : str
        The name of the lift function subcommand.
    bar_desc : str
        A string that describes the progress bar for the `tqdm` library.
    '''

    def decorate(f: typing.Callable[[Tree, str], typing.Any]):
        def cmd(ctx: typer.Context):
            skip_ill_trees = ctx.obj["CONFIG"]["skip-ill-trees"]

            logger.info(f"Subcommand invoked: {name}")
            for ID, tree in tqdm(ctx.obj["treebank"], desc = bar_desc):
                try:
                    f(tree, ID)
                except Exception as e:
                    if skip_ill_trees:
                        logger.warning(
                            "An exception was raised by the convertion function. "
                            "The tree will be abandoned."
                            f"Tree ID: {ID}. "
                            f"Exception: {e}"
                        )
                    else:
                        logger.error(
                            "An exception was raised by the convertion function. "
                            "The process has been aborted."
                            f"Tree ID: {ID}. "
                            f"Exception: {e}"
                        )
                        raise
        return cmd
    return decorate

def lift_func_newobj(name: str, bar_desc: str = ""):
    '''
    A decorator that takes in a tree-generating function 
    and returns a new function that
    iterates through a treebank 
    and applies the input function to each tree, 
    handling exceptions and logging progress.
    
    Parameters
    ----------
    name : str
        The name of the lift function subcommand.
    bar_desc : str
        A string that describes the progress bar for the `tqdm` library.
    '''

    def decorate(f: typing.Callable[[Tree, str], typing.Any]):
        def cmd(ctx: typer.Context):
            skip_ill_trees = ctx.obj["CONFIG"]["skip-ill-trees"]

            logger.info(f"Subcommand invoked: {name}")
        
            def _yield(tb):
                for ID, tree in tqdm(tb, desc = bar_desc):
                    try:
                        yield ID, f(tree, ID)
                    except Exception as e:
                        if skip_ill_trees:
                            logger.warning(
                                "An exception was raised by the convertion function. "
                                "The tree will be abandoned."
                                f"Tree ID: {ID}. "
                                f"Exception: {e}"
                            )
                        else:
                            logger.error(
                                "An exception was raised by the convertion function. "
                                "The process has been aborted."
                                f"Tree ID: {ID}. "
                                f"Exception: {e}"
                            )
                            raise

            ctx.obj["treebank"] = list(_yield(ctx.obj["treebank"]))
        return cmd 
    return decorate

# ----------------
# Particular functions
# ----------------
def cmd_minimize_tree(
    ctx: typer.Context,
    discard_trace: bool = typer.Option(
        True,
    ),
    reduction_check: bool = typer.Option(
        True
    ),
):
    tb: typing.Dict[str, Tree] = ctx.obj["treebank"]
    for ID, tree in tqdm(tb, desc = "Minimizing annotations"):
        abctk.transform_ABC.norm.minimize_tree(
            tree, ID,
            discard_trace,
            reduction_check
        )

def cmd_restore_trace(
    ctx: typer.Context,
    generous: bool = typer.Option(
        False,
        "--generous/--strict",
        help = ""
    )
):
    logger.info(f"Subcommand invoked: restore-trace")
    skip_ill_trees = ctx.obj["CONFIG"]["skip-ill-trees"]

    tb: typing.List[typing.Tuple[RecordID, Tree]] = ctx.obj["treebank"]

    for ID, tree in tqdm(tb, desc = "Restoring *T*"):
        try:
            abctk.transform_ABC.elim_trace.restore_rel_trace(
                tree, ID,
                generous
            )
        except abctk.transform_ABC.elim_trace.ElimTraceException as e:
            if skip_ill_trees:
                logger.warning(
                    "An exception was raised by the convertion function. "
                    f"Tree ID: {ID}. "
                    "The tree will be abandoned."
                )
            else:
                logger.error(
                    "An exception was raised by the convertion function. "
                    f"Tree ID: {ID}. "
                    "The process has been aborted."
                )
                raise

def cmd_elaborate_cat_annotations(
    ctx: typer.Context,
):
    tb: typing.Dict[str, Tree] = ctx.obj["treebank"]
    for ID, tree in tqdm(tb, desc = "Elaborating category-related annotations"):
        abctk.transform_ABC.norm.elaborate_cat_annotations(
            tree, ID,
        )

def cmd_elaborate_char_spans(
    ctx: typer.Context,
):
    tb: typing.Dict[str, Tree] = ctx.obj["treebank"]
    for ID, tree in tqdm(tb, desc = "Elaborating char span annotations"):
        abctk.transform_ABC.norm.elaborate_char_spans(
            tree, ID,
        )

def cmd_obfuscate_tree(
    ctx: typer.Context,
    filter: str = typer.Option(
        "closed",
        help = """A regex that specifies
the IDs of the trees to be obfuscated.
Default to /closed/."""
    )
):
    """
    Obfuscate trees by masking characters for license / copyright reasons.
    """

    skip_ill_trees = ctx.obj["CONFIG"]["skip-ill-trees"]
    tb: typing.List[typing.Tuple[RecordID, Tree]] = ctx.obj["treebank"]
    matcher = re.compile(filter)
    
    def _yield(tb):
        for ID, tree in tqdm(tb, desc = "Obfuscate trees"):
            try:
                if matcher.search(ID.name):
                    yield ID, abctk.obfuscate.obfuscate_tree(tree, ID)
                else:
                    yield ID, tree
            except Exception as e:
                if skip_ill_trees:
                    logger.warning(
                        "An exception was raised by the convertion function. "
                        f"Tree ID: {ID}. "
                        "The tree will be abandoned."
                    )
                else:
                    logger.error(
                        "An exception was raised by the convertion function. "
                        f"Tree ID: {ID}. "
                        "The process has been aborted."
                    )
                    raise
    
    ctx.obj["treebank"] = list(_yield(tb))

def cmd_decrypt_tree(
    ctx: typer.Context,
    filter: str = typer.Option(
        "closed",
        help = """
            A regex that specifies
            the IDs of the trees to be obfuscated.
            Default to /closed/.
        """
    ),
    source: pathlib.Path = typer.Argument(
        ...,
        file_okay = True,
        dir_okay = True,
        exists = True,
        help = """
            A TSV file which contains decrypting texts. 
        """
    )
):
    """
    Decrypt obfuscated trees.

    To get the decrypting texts, the easiest and best way is to first
    obtain the original Keyaki treebank and run the following script:

    \b
    ```sh
    cat treebank/*closed*.psd \\
        | munge-trees -y \\
        | awk -F " " '
    {
        printf "%s\\t", $NF;
        for (i = 1; i < NF; i++) {
            if ( !($i ~ /\\*.+\\*/ || $i == "*") )  {
                printf "%s", $i;
            }
        }
        printf "\\n";
    }
    ' >! keyaki-closed.tsv
    ```

    You can save the yields to run decryption at any time.
    """
    def _parse_source(line: str):
        line_broken = line.strip().split("\t")
        return (
            Keyaki_ID.from_string(line_broken[0]) or Keyaki_ID.new(), 
            line_broken[1]
        )

    with open(source) as h_source:
        source_dict = dict(
            _parse_source(line) for line in h_source
        )

    skip_ill_trees = ctx.obj["CONFIG"]["skip-ill-trees"]
    tb: typing.List[typing.Tuple[RecordID, Tree]] = ctx.obj["treebank"]
    matcher = re.compile(filter)

    def _yield(tb) -> typing.Iterator[typing.Tuple[RecordID, Tree]]:
        for ID, tree in tqdm(tb, desc = "Decrypt trees"):
            try:
                if matcher.search(ID.name):
                    yield (
                        ID, 
                        abctk.obfuscate.decrypt_tree(
                            tree, 
                            source_dict[ID], 
                            ID = ID
                        )[0],
                    )
                else:
                    yield ID, tree
            except Exception as e:
                if skip_ill_trees:
                    logger.warning(
                        "An exception was raised by the convertion function. "
                        f"Tree ID: {ID}. "
                        "The tree will be abandoned."
                    )
                else:
                    logger.error(
                        "An exception was raised by the convertion function. "
                        f"Tree ID: {ID}. "
                        "The process has been aborted."
                    )
                    raise

    ctx.obj["treebank"] = list(_yield(tb))


_COMMAND_TABLE: typing.Dict[
    str, 
    typing.Tuple[
        typing.Callable[[typer.Context], typing.Any], 
        str,
    ]
] = {
    "relax": (
        lambda _: None,
        "Do nothing (Just load trees and check the annotations therein)."
    ),
    "parse-ABC-label": (
        lift_func("parse-ABC-label", "Parse all ABC labels")(
            lambda tree, ID: (
                nt.parse_all_labels_ABC(tree),
                ID
            ),
        ),
        "Parse all ABC labels in given trees."
    ),
    "check-comp": (
        lift_func("check-comp", "Check #comp feats")(
            lambda tree, ID: abctk.check_comp_feat.check_comp_feats(
                abctk.check_comp_feat.collect_comp_feats(
                    tree, ID,
                ),
                ID
            )
        ),
        "Do nothing (but health-check #comp features)."
    ),
    "bin-conj": (
        lift_func_newobj("bin-conj", "Binarize CONJPs")(
            abctk.transform_ABC.binconj.binarize_conj_tree
        ),
        "Binarize conjunctions.",
    ),
    "flatten-conj": (
        lambda ctx: NotImplemented,
        "Flatten conjunctions.",
        #"Flattening CONJPs",
    ),
    "elim-empty": (
        lift_func("elim-empty", "Eliminate empty nodes")(
            abctk.transform_ABC.elim_empty.elim_empty_terminals
        ),
        "Eliminate nodes of empty categories.",
    ),
    "restore-empty": (
        lambda ctx: NotImplemented,
        "Restore nodes of empty categories.",
        # "Restore empty nodes"
    ),
    "elim-trace": (
        lambda ctx: NotImplemented,
        "Eliminate traces of relative clauses.",
        # "Eliminating *T*"
    ),
    "restore-trace": (
        cmd_restore_trace,
        ""
    ),
    "restore-trace-in-comp": (
        lift_func_newobj(
            "restore-trace-in-comp",
            "Restore *T* *pro* in #comp"
        )(
            abctk.gen_comp.restore_traces_on_demand
        ),
        "Restore empty categories in #comp"
    ),
    "janome": (
        lift_func(
            "janome",
            "Adding Janome analyses"
        )(
            abctk.transform_ABC.morph_janome.add_morph_janome
        ),
        "Add Janome morphological analyses",
    ),
    "del-janome": (
        lift_func(
            "janome",
            "Removing Janome analyses"
        )(
            abctk.transform_ABC.morph_janome.del_morph_janome
        ),
        "Delete Janome morphological analyses",
    ),
    "min-nodes": (
        cmd_minimize_tree,
        "Minimize node annotations",
    ),
    "elab-cat-annots": (
        cmd_elaborate_cat_annotations,
        "Elaborate category annotations on nodes",
    ),
    "elab-char-spans": (
        cmd_elaborate_char_spans,
        "Elaborate char span annotations on nodes",
    ),
    "obfus": (
        cmd_obfuscate_tree,
        "Obfuscate lexical nodes",
    ),
    "decrypt": (
        cmd_decrypt_tree,
        "Decrypt lexical nodes",
    )
}

# Register all commands in `_COMMAND_TABLE`
for name, (command, desc) in _COMMAND_TABLE.items():
    app = typer.Typer()
    app_treebank.command(
        name,
        help = desc or None
    )(command)
    app_file.command(
        name,
        help = desc or None
    )(command)

# ------------
# Writer 
# ------------
def cmd_write(
    ctx: typer.Context, 
    dest_path: pathlib.Path = typer.Argument(
        ...,
        file_okay = True,
        dir_okay = True,
        allow_dash = True,
        help = """
        The destination. `-` indicates STDOUT.
        """
    ),
    force_dir: bool = typer.Option(
        False,
        "--force-dir/--no-force-dir",
    )
):
    dest_file: typing.Optional[typing.TextIO] = None
    if dest_path.name == "-":
        dest_file = sys.stdout
    elif not force_dir and not dest_path.is_dir():
        dest_file = open(str(dest_path.resolve()), "w")

    if dest_file:
        for ID, tree in tqdm(
            ctx.obj["treebank"], 
            desc = "Writing out ABC trees"
        ):
            dest_file.writelines(
                (
                    nt.flatten_tree_with_ID(
                        ID, tree
                    ),
                    "\n",
                )
            )
    else:
        with fs.open_fs(str(dest_path), create = True) as folder:
            nt.dump_ABC_to_psd(ctx.obj["treebank"], folder)

app_treebank.command(
    "write",
    help = "Write out (the current state of) the trees."
)(cmd_write)
app_file.command(
    "write",
    help = "Write out (the current state of) the trees."
)(cmd_write)

# ================
# Main
# ================
app = typer.Typer()
app.add_typer(app_treebank, name = "treebank")
app.add_typer(app_file, name = "file")

@app.callback()
def cmd_main():
    """
    Tweak ABC trees.
    """