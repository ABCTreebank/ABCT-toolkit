import pathlib

import fs
from tqdm.auto import tqdm
import typer


import abctk.transform_ABC.elim_empty as ee
import abctk.io.nltk_tree as nt

app = typer.Typer()

@app.callback()
def cmd_main():
    """
    Eliminate empty categories from ABC trees.
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
    Eliminate empty terminals from the ABC Treebank.
    """
    tb = list(nt.load_ABC_psd(source_path))

    for ID, tree in tqdm(   
        tb,
        desc = "Eliminating empty terminals",
    ):
        # normalize
        ee.elim_empty_terminals(tree, ID)

    with fs.open_fs(str(dest_path), create = True) as folder:
        nt.dump_ABC_to_psd(tb, folder)
        
@app.command("stdin")
def cmd_from_stdin():
    """
    
    """

    raise NotImplementedError