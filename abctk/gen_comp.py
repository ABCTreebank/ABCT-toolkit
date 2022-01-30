import logging
import shutil

logger = logging.getLogger(__name__)
import pathlib
import typing
import re
import subprocess

from nltk.tree import Tree

import abctk.config
import abctk.cli_typer.renumber
import abctk.io.nltk_tree as nt
import abctk.types.ABCCat as abcc
import abctk.transform_ABC.elim_trace

X = typing.TypeVar("X", Tree, str)
def restore_traces_on_demand(
    tree: X,
    ID: str
) -> X:
    if isinstance(tree, Tree):
        label: abcc.Annot[abcc.ABCCat] = tree.label()

        return Tree(
            node = label,
            children = [
                _restore_pro_on_demand_inner(
                    child,
                    ID,
                    label.cat,
                    is_unary = len(tree) < 2
                )
                for child in tree
            ]
        )
    else:
        return tree

_re_root_cont = re.compile(
    r"(?P<index>^[0-9]+),root,cont$"
)

def _restore_pro_on_demand_inner(
    tree: X,
    ID: str,
    parent_node_cat: abcc.ABCCat,
    is_unary: bool,
) -> X:
    if isinstance(tree, Tree):
        label: abcc.Annot[abcc.ABCCat] = tree.label()
        cat = label.cat

        if (
            isinstance(cat, abcc.ABCCatFunctor) 
            and cat.equiv_to(
                abcc.ABCCat.p("<PP\\S>"),
                ignore_feature = True,
            )
            and (
                feat_comp_match 
                := _re_root_cont.match(label.feats.get("comp", ""))
            )
        ):
            index = feat_comp_match.group("index")

            ant = cat.ant # PP
            conseq = cat.conseq # S

            is_rel: bool = is_unary and (
                parent_node_cat.equiv_to(
                    abcc.ABCCat.p("<N/N>"),
                    ignore_feature = True,
                ) or
                parent_node_cat.equiv_to(
                    abcc.ABCCat.p("<NP/NP>"),
                    ignore_feature = True,
                )
            )

            root_new_feats = {
                k:v for k, v in label.feats.items()
                if k != "comp"
            }
            root_new_feats["comp"] = f"{index},root" # get rid of "cont"

            return Tree(
                node = abcc.Annot( # node: S|PP
                    cat = conseq.v(ant),
                    feats = (
                        {"rel": "bind"} if is_rel
                        else {"adv-pro": "bind"}
                    ),
                    pprinter_cat = abcc.ABCCat.pprint,
                ),
                children = [
                    Tree(
                        node = abcc.Annot( # node: S#comp={index},root#...
                            cat = conseq,
                            feats = root_new_feats,
                            pprinter_cat = abcc.ABCCat.pprint,
                        ),
                        children = [
                            Tree(
                                node = abcc.Annot( # node: PP#comp={index},cont
                                    cat = ant,
                                    feats = {"comp": f"{index},cont"},
                                    pprinter_cat = abcc.ABCCat.pprint,
                                ),
                                children = [
                                    ("*T*" if is_rel else "*TRACE-pro*")
                                ]
                            ),
                            Tree(
                                node = abcc.Annot(
                                    cat = cat, # cat PP
                                    pprinter_cat = abcc.ABCCat.pprint,
                                ),
                                children = [
                                    _restore_pro_on_demand_inner(
                                        child, ID,
                                        cat,
                                        len(tree) < 2
                                    )
                                    for child in tree
                                ]
                            ),
                        ]
                    ), #unary
                ]
            )
        else:
            return Tree(
                node = label,
                children = [
                    _restore_pro_on_demand_inner(
                        child, ID,
                        cat, len(tree) < 2
                    )
                    for child in tree
                ]
            )
    else:
        return tree


# ========================
# Conversion Procedures
# ========================
def convert_io(
    f_src: typing.TextIO,
    f_dest: typing.TextIO,
    temp_folder: typing.Union[str, pathlib.Path],
    src_name: typing.Any = "<INPUT>",
    dest_name: typing.Any = "<OUTPUT>",
    conf: typing.Dict[str, typing.Any] = abctk.config.CONF_DEFAULT,
    log_prefix: typing.Union[None, str, pathlib.Path] = None,
    **kwargs
) -> int:
    basename = pathlib.Path(src_name).stem

    logger.info(
        f"Commence a comparative conversion on the file/stream {src_name}"
    )

    if isinstance(temp_folder, pathlib.Path):
        temp_folder = str(temp_folder.resolve())

    # ========================
    # 1. Select trees
    # ========================
    command_select = f"""
    {conf["bin-sys"]["ruby"]} {conf["runtimes"]["unsimplify-ABC-tags"]} - 
| {conf["bin-sys"]["munge-trees"]} -w 
| {conf["bin-sys"]["awk"]} -e '/typical|関係節|連用節/' 
| {conf["bin-sys"]["sed"]} -e 's/(COMMENT {{.*}})//g'
"""
    if log_prefix:
        command_select += f" | tee {log_prefix}-00-selected.psd"
        logger.info(
            f"The trace file of Step 1 will be saved at {log_prefix}-00-selected.psd"
        )

    command_select = command_select.strip().replace("\n", "")
    
    logger.info(
        f"Step 1: Command to be executed: {command_select}"
    )

    temp_file_name_selected = pathlib.Path(
        f"{temp_folder}/{basename}-00-selected.psd"
    )

    with open(temp_file_name_selected, "w") as f_temp:
        proc = subprocess.Popen(
            command_select,
            shell = True,
            stdin = f_src,
            stdout = f_temp,
        )
        proc.wait()

        return_code = proc.returncode

        if return_code: # <> 0
            logger.warning(f"warning: conversion failed: {src_name}")
        else:
            logger.info(
                f"Successfully complete Step 1. "
                f"The outcome is stored at `{temp_file_name_selected}'."
            )
        # === END IF ===

    # ========================
    # 2. renumber trees
    # ========================
    logger.info(
        f"Step 2: renumber trees"
    )

    temp_file_name_renumbered = pathlib.Path(
        f"{temp_folder}/{basename}-10-renum.psd"
    )
    abctk.cli_typer.renumber.cmd_from_file(
        source_path = temp_file_name_selected,
        dest_path = temp_file_name_renumbered,
        fmt = f"{{id_orig.number}}_{basename}"
    )
    if log_prefix:
        shutil.copy(
            temp_file_name_renumbered,
            f"{log_prefix}-10-renum.psd"
        )
        logger.info(
            f"The trace file of Step 2 is saved at {log_prefix}-10-selected.psd"
        )

    logger.info(
        f"Successfully complete Step 2. "
        f"The outcome is stored at {temp_file_name_renumbered}."
    )

    # ========================
    # 3. restore *T* and pro
    # ========================
    logger.info(
        f"Step 3: restore *T* and *pro*"
    )

    filter_re = re.escape(temp_file_name_renumbered.name)

    logger.info(
        f"Try reading the file: {temp_file_name_renumbered} "
        f"(filter: {filter_re})",
    )

    trees = list(
        nt.load_ABC_psd(
            temp_folder,
            re_filter = filter_re,
            skip_ill_trees = True,
            prog_stream = None,
        )
    )

    trees = [
        (ID, restore_traces_on_demand(tree, str(ID)))
        for ID, tree in trees
    ]

    temp_file_restored = pathlib.Path(
        f"{temp_folder}/{basename}-20-restored.psd"
    )

    with open(temp_file_restored, "w") as h_restored:
        h_restored.write(
            "\n".join(
                nt.flatten_tree_with_ID(
                    ID, tree
                )
                for ID, tree in trees
            )
        )

    if log_prefix:
        shutil.copy(
            temp_file_restored,
            f"{log_prefix}-20-restored.psd"
        )
        logger.info(
            f"The trace file of Step 3 is saved at {log_prefix}-20-restored.psd"
        )
    
    logger.info(
        f"Successfully complete Step 2. "
        f"The outcome is stored at `{temp_file_restored}'."
    )

    # ========================
    # 4. remove #role=none & move
    # ========================
    if log_prefix:
        command = f"""
{conf["bin-sys"]["sed"]} -e 's/#role=none//g'
| tee {log_prefix}-30-remrole.psd
| {conf["bin-custom"]["tsurgeon_script"]} {conf["runtimes"]["move-comparative"]}
| tee {log_prefix}-40-move.psd
    """
    else:
        command = f"""
{conf["bin-sys"]["sed"]} -e 's/#role=none//g'
| {conf["bin-custom"]["tsurgeon_script"]} {conf["runtimes"]["move-comparative"]}
    """

    command = command.strip().replace("\n", "")

    logger.info(
        f"Step 4: remove #role=none and move comp-related nodes: {command}"
    )

    with (
        open(temp_file_restored) as f_restore,
    ):
        proc = subprocess.Popen(
            command,
            shell = True,
            stdin = f_restore,
            stdout = f_dest,
        )
        proc.wait()

        return_code = proc.returncode

        if return_code: # <> 0
            logger.warning(f"warning: conversion failed: {src_name}")
        else:
            logger.info(
                f"Successfully complete Step 4. "
                f"The outcome is stored at `{dest_name}'."
            )
        # === END IF ===

    return return_code
# === END ===

def convert_file(
    src: pathlib.Path, 
    dest: pathlib.Path,
    temp_folder: typing.Union[str, pathlib.Path],
    conf: typing.Dict[str, typing.Any] = abctk.config.CONF_DEFAULT,
    log_prefix: typing.Union[None, str, pathlib.Path] = None,
    **kwargs
) -> int:
    dest_file_name_bare = dest.stem
    dest_name_bare: pathlib.Path = dest.parent / dest_file_name_bare
    dest_path_abs: str = str(dest_name_bare) + "-comp_moved.psd"

    # temp_folder = None
    # try:
    #     temp_folder = tempfile.TemporaryDirectory(prefix = "ABCT-gen-comp_")
    #     logger.info(
    #         f"Temporary folder created at: {temp_folder}"
    #     )

    with open(src, "r") as h_src, open(dest_path_abs, "w") as h_dest:
        res = convert_io(
            h_src, h_dest,
            temp_folder = temp_folder,
            src_name = src, 
            dest_name = dest_path_abs,
            conf = conf,
            log_prefix = (
                f"{log_prefix}/{dest_file_name_bare}"
                if log_prefix else None
            ),
            # TODO: more flexible log_prefix
            **kwargs
        )
    # === END WITH h_src, h_dest ===
    # finally:
    #     if temp_folder:
    #         temp_folder.cleanup()
    #         logger.info(
    #             f"The temporary folder has been cleaned up"
    #         )

    return res
# === END ===
