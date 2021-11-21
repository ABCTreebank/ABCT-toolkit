from enum import Enum
import pathlib

import fs
from tqdm.auto import tqdm

import typer

import abctk.io.nltk_tree as nt
import abctk.transform_ABC.norm as norm

class NormType(Enum):
    FULL = "full"
    MIN = "min"

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
    label_mode: NormType = typer.Option(
        NormType.FULL.value,
        "--label",
        case_sensitive = False,
        help = """
        The way to normalize labels.
        """
    ),
    discard_trace: bool = typer.Option(
        True,
        help = """
        Whether to discard existent trace features.
        """
    ),
    reduction_check: bool = typer.Option(
        True,
        help = """
        If true, check the validity of beta-reduction before minimizing away categories.
        Incorrect derivations, which might contain valuable mistakes (contra correct derivations, in which the resulting categories can be readily recovered), will be kept untouched.
        
        Skipping it will fasten the program.
        """
    )
):
    """
    Normalize the ABC Treebank as a whole.
    """
    tb = list(nt.load_ABC_psd(source_path))

    if label_mode == NormType.MIN:
        for ID, tree in tqdm(
            tb,
            desc = "Minifying ABC trees",
        ):
            # normalize
            norm.minimize_tree(
                tree,
                ID,
                discard_trace,
                reduction_check,
            )
    elif label_mode == NormType.FULL:
        for ID, tree in tqdm(
            tb,
            desc = "Elaborating ABC trees",
        ):
            norm.elaborate_tree(
                tree,
                ID,
            )
    else:
        raise NotImplementedError

    with fs.open_fs(str(dest_path), create = True) as folder:
        nt.dump_ABC_to_psd(tb, folder)
        
@app.command("stdin")
def cmd_from_stdin():
    """
    
    """

    raise NotImplementedError