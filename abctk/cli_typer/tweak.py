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
import abctk.transform_ABC.unary
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

        tb = list(
            nt.load_Keyaki_Annot_psd(
                str(temp_folder.name),
                re_filter = ".*"
            )
        )
        
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
X = typing.TypeVar("X")
class CommandObject(typing.NamedTuple):
    callback: typing.Callable[[typer.Context], typing.Any]
    help_text: str
    
    @classmethod
    def wrap_modifier(
        cls, 
        function: typing.Callable[[Tree, str], typing.Any],
        name: str, 
        bar_desc: str = "",
        help_text: str = "",
    ): 
        '''
        Parameters
        ----------
        function

        name
            The name of the subcommand.
        bar_desc
            A string that describes the progress bar for the :module:`tqdm` library.
        help_text
            A help text for the subcommand.
        '''

        def cmd(ctx: typer.Context):
            skip_ill_trees = ctx.obj["CONFIG"]["skip-ill-trees"]

            logger.info(f"Subcommand invoked: {name}")
            for ID, tree in tqdm(
                ctx.obj["treebank"], 
                desc = bar_desc or f"Running {name}",
            ):
                try:
                    function(tree, ID)
                except Exception as e:
                    if skip_ill_trees:
                        logger.warning(
                            "An exception was raised by the conversion function. "
                            "The tree will be abandoned."
                            f"Tree ID: {ID}. "
                            f"Exception: {e}"
                        )
                    else:
                        logger.error(
                            "An exception was raised by the conversion function. "
                            "The process has been aborted."
                            f"Tree ID: {ID}. "
                            f"Exception: {e}"
                        )
                        raise
        return cls(cmd, help_text)

    @classmethod
    def wrap_creator(
        cls, 
        function: typing.Callable[[X, str], X],
        name: str, 
        bar_desc: str = "",
        help_text: str = "",
    ):
        '''
        Parameters
        ----------
        function

        name
            The name of the subcommand.
        bar_desc
            A string that describes the progress bar for the :module:`tqdm` library.
        help_text
            A help text for the subcommand.
        '''

        def cmd(ctx: typer.Context):
            skip_ill_trees = ctx.obj["CONFIG"]["skip-ill-trees"]

            logger.info(f"Subcommand invoked: {name}")
        
            def _yield(tb):
                for ID, tree in tqdm(
                    tb, 
                    desc = bar_desc or f"Running {name}"
                ):
                    try:
                        yield ID, function(tree, ID)
                    except Exception as e:
                        if skip_ill_trees:
                            logger.warning(
                                "An exception was raised by the conversion function. "
                                "The tree will be abandoned."
                                f"Tree ID: {ID}. "
                                f"Exception: {e}"
                            )
                        else:
                            logger.error(
                                "An exception was raised by the conversion function. "
                                "The process has been aborted."
                                f"Tree ID: {ID}. "
                                f"Exception: {e}"
                            )
                            raise

            ctx.obj["treebank"] = list(_yield(ctx.obj["treebank"]))
        
        return cls(cmd, help_text)

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

# ----------------
# Incorporating comparative annotations
# ----------------
def cmd_incorporate_comps(
    ctx: typer.Context,
    comp_file: typer.FileText = typer.Argument(
        ...,
        help = "Path to a comparative annotation file"
    ),
    comp_file_format: str = typer.Option(
        "yaml",
        "--format", "-f",
        help = "The format of the comparative annotation file"
    ),
):
    import json
    import ruamel.yaml

    from abctk.obj.ID import SimpleRecordID
    from abctk.obj.Keyaki import Keyaki_ID
    from abctk.obj.comparative import CompRecord, ABCTComp_BCCWJ_ID
    from abctk.transform_ABC.incorporate_comp import incorporate_all_comps

    # Load file
    comp_file_format = comp_file_format.lower()

    if comp_file_format == "jsonl":
        comp_annots_raw: typing.Iterator[dict] = (
            json.loads(line) for line in comp_file
        )
    elif comp_file_format == "yaml":
        yaml = ruamel.yaml.YAML()
        comp_annots_raw: typing.Iterator[dict] = (
            yaml.load(comp_file)
        )
    else:
        logger.error(
            f"Wrong option for --format: {comp_file_format}. "
            "Choose between `yaml` and `jsonl`."
        )
        raise ValueError

    def _parse_comp_raw(record: dict):
        ID_raw = record["ID"]
        ID_parsed = (
            ABCTComp_BCCWJ_ID.from_string(ID_raw)
            or Keyaki_ID.from_string(ID_raw)
            or SimpleRecordID.from_string(ID_raw)
        )

        return (
            ID_parsed,
            CompRecord.from_brackets(
                line = record["annot"],
                ID_v1 = record.get("ID_v1"),
                ID = ID_raw,
            ).dice()
        )

    # indexing
    comp_annots = dict(_parse_comp_raw(record) for record in comp_annots_raw)

    for ID, tree in tqdm(
        ctx.obj["treebank"], 
        desc = "Incorporating comparative annotations"
    ):
        comp_record = comp_annots.get(ID)
        if comp_record:
            incorporate_all_comps(
                comp_record.comp,
                tree,
                ID,
            )
        else:
            logger.warning(
                f"Comparative annotations are not found for the tree (ID: {ID}). "
                f"This tree will be skipped."
            )

app_treebank.command(
    "incorp-comps",
    help = "Incorporate comparative annotations to trees."
)(cmd_incorporate_comps)
app_file.command(
    "incorp-comps",
    help = "Incorporate comparative annotations to trees."
)(cmd_incorporate_comps)

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
                        "The tree will be abandoned. "
                        f"Error: {e}"
                    )
                else:
                    logger.error(
                        "An exception was raised by the convertion function. "
                        f"Tree ID: {ID}. "
                        "The process has been aborted. "
                        f"Error: {e}"
                    )
                    raise

    ctx.obj["treebank"] = list(_yield(tb))

_COMMAND_TABLE: typing.Dict[str, CommandObject] = {
    "relax": CommandObject.wrap_modifier(
        function = lambda tree, ID: None,
        name = "relax",
        bar_desc = "",
        help_text = "Do nothing (Just load trees and check meta-annotations)."
    ),
    "parse-ABC-cats": CommandObject.wrap_modifier(
        function = nt.parse_all_labels_ABC,
        name = "parse-ABC-cats",
        bar_desc = "Parsing ABC cats",
        help_text = "Parse all ABC categories in given trees."
    ),
    "check-comp": CommandObject.wrap_modifier(
        function = lambda tree, ID: abctk.check_comp_feat.check_comp_feats(
            abctk.check_comp_feat.collect_comp_feats(
                tree, ID,
            ),
            ID,
        ),
        name = "check-comp",
        bar_desc = "Checking #comp",
        help_text = "Health-check #comp features."
    ),
    "collapse-unary-nodes": CommandObject.wrap_creator(
        function = abctk.transform_ABC.unary.collapse_unary_nodes,
        name = "collapse-unary-nodes",
        bar_desc = "Collapsing unaries",
        help_text = "Collaps unary nodes. Must be invoked before parse-ABC-label."
    ),
    "restore-unary-nodes": CommandObject.wrap_creator(
        function = abctk.transform_ABC.unary.restore_unary_nodes,
        name = "restore-unary-nodes",
        bar_desc = "Restoring unaries",
        help_text = "Restore unary nodes. Must be invoked before parse-ABC-label."
    ),
    "bin-conj": CommandObject.wrap_creator(
        function = abctk.transform_ABC.binconj.binarize_conj_tree,
        name = "bin-conj",
        bar_desc = "Binarizing CONJPs",
        help_text = "Binarize conjunctions. Expected to be invoked after parse-ABC-label."
    ),
    "flatten-conj": CommandObject(
        lambda ctx: NotImplemented,
        "Flatten conjunctions.",
        #"Flattening CONJPs",
    ),
    "elim-empty": CommandObject.wrap_modifier(
        function = abctk.transform_ABC.elim_empty.elim_empty_terminals,
        name = "elim-empty",
        bar_desc = "Del'ing * and __",
        help_text = "Eliminate nodes of empty categories."
    ),
    "restore-empty": CommandObject(
        lambda ctx: NotImplemented,
        "Restore nodes of empty categories.",
        # "Restore empty nodes"
    ),
    "elim-trace": CommandObject(
        lambda ctx: NotImplemented,
        "Eliminate traces of relative clauses.",
        # "Eliminating *T*"
    ),
    "restore-trace": CommandObject(
        cmd_restore_trace,
        "Restore traces of relative clauses."
    ),
    "restore-trace-in-comp": CommandObject.wrap_creator(
        function = abctk.gen_comp.restore_traces_on_demand,
        name = "restore-trace-in-comp",
        bar_desc = "Restoring *T* and *pro* in #comp",
        help_text = "Restore *T* and  *pro* in #comp.",
    ),
    "janome": CommandObject.wrap_modifier(
        function = abctk.transform_ABC.morph_janome.add_morph_janome,
        name = "janome",
        bar_desc = "Adding Janome analyses",
        help_text = "Add Janome morphological analyses."
    ),
    "del-janome": CommandObject.wrap_modifier(
        function = abctk.transform_ABC.morph_janome.del_morph_janome,
        name = "del-janome",
        bar_desc = "Del'ing Janome analyses",
        help_text = "Delete Janome morphological analyses."
    ),
    "min-nodes": CommandObject(
        cmd_minimize_tree,
        "Minimize node annotations",
    ),
    "elab-cat-annots": CommandObject(
        cmd_elaborate_cat_annotations,
        "Elaborate meta annotations on nodes",
    ),
    "elab-char-spans": CommandObject(
        cmd_elaborate_char_spans,
        "Elaborate char span annotations on nodes.",
    ),
    "obfus": CommandObject(
        cmd_obfuscate_tree,
        "Obfuscate lexical nodes.",
    ),
    "decrypt": CommandObject(
        cmd_decrypt_tree,
        "Decrypt lexical nodes.",
    )
}

# Register all commands in `_COMMAND_TABLE`
for name, (command, desc) in _COMMAND_TABLE.items():
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
    ),
    hide_all_feats: bool = typer.Option(
        False,
        "--hide-feats/--no-hide-feats",
        help = "Hide all meta features. Can be overwritten by `--print-feat`.",
    ),
    feats_to_print: typing.List[str] = typer.Option(
        [],
        "--print-feat",
    ),
    verbose_role: bool = typer.Option(
        False,
        "--verbose-role/--no-verbose-role",
        help = "Verbosely print `#role=none` if set."
    ),
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
                        ID, tree,
                        hide_all_feats = hide_all_feats,
                        feats_to_print = feats_to_print,
                        verbose_role = verbose_role,
                    ),
                    "\n",
                )
            )
    else:
        with fs.open_fs(str(dest_path), create = True) as folder:
            nt.dump_ABC_to_psd(
                ctx.obj["treebank"], 
                folder,
                hide_all_feats = hide_all_feats,
                feats_to_print = feats_to_print,
                verbose_role = verbose_role,
            )

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