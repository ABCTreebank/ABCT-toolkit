import logging
logger = logging.getLogger(__name__)
import pathlib
import typing

import fs
from tqdm.auto import tqdm
import typer
from nltk.tree import Tree

import abctk.io.nltk_tree as nt
import abctk.transform_ABC.norm as norm


from abctk.transform_ABC.elim_empty import elim_empty_terminals
from abctk.transform_ABC.elim_trace import restore_rel_trace

def parse_command(command: str) -> typing.Callable[[Tree, str], typing.Any]:
        com_args = command.split(".")
        com_name, others = com_args[0], com_args[1:]
        
        if com_name == "bin-conj":
            if not others:
                logger.info("Command: binarize conjunctions")
                raise NotImplementedError
            else:
                raise ValueError
        elif com_name == "flatten-conj":
            if not others:
                logger.info("Command: flatten conjunctions")
                raise NotImplementedError
            else:
                raise ValueError
        elif com_name == "elim-empty":
            if not others:
                logger.info("Command: eliminate empty nodes")
                return elim_empty_terminals
            else:
                raise ValueError
        elif com_name == "elab-empty":
            if not others:
                logger.info("Command: restore empty nodes")
                return restore_rel_trace
            else:
                raise ValueError
        elif com_name == "elim-trace":
            if not others:
                logger.info("Command: eliminate relative clause traces")
                raise NotImplementedError
            else:
                raise ValueError
        elif com_name == "elab-trace":
            if not others:
                logger.info("Command: restore relative clause traces")
                raise NotImplementedError
            else:
                raise ValueError
        elif com_name == "janome":
            if not others:
                raise NotImplementedError
            else:
                raise ValueError
        elif com_name == "del-janome":
            if not others:
                raise NotImplementedError
            else:
                raise ValueError
        elif com_name == "min-nodes":
            raise NotImplementedError
        elif com_name == "elab-nodes":
            raise NotImplementedError
        elif com_name == "obfus":
            raise NotImplementedError
        else:
            raise ValueError

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
    func_list = tuple(parse_command(com) for com in commands)

    # load trees
    tb = list(nt.load_ABC_psd(source_path))

    for ID, tree in tqdm(tb, desc = "Tweaking ABC trees"):
        for f in func_list:
            # apply tweaks
            f(tree, ID)

    with fs.open_fs(str(dest_path), create = True) as folder:
        nt.dump_ABC_to_psd(tb, folder)
        
@app.command("stdin")
def cmd_from_stdin():
    """
    
    """

    raise NotImplementedError