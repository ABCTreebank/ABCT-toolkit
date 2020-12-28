import typing
import itertools
import sys
import io
import pathlib 

import click

from . import core

# ======
# Commandline commands
# ======

@click.command(
    name = "parse",
    short_help = "parse sentences",
)
@click.option(
    "--model", "-m",
    type = click.Path(
        exists = True,
        file_okay = False,
        dir_okay = True,
    ),
    #default = "/...",
    metavar = "<user_model>",
    help = "path to a user model"
)
@click.option(
    "--batchsize", "-b", "batch_size",
    type = click.IntRange(min = 1, max = None),
    default = 32,
    metavar = "<batch_size>",
)
@click.option(
    "--tokenize/--no-tokenize", "-t/-nt", "is_to_tokenize",
    default = False,
    help = "whether to tokenize sentences before parsing"
)
@click.option(
    "--output-format", "--format", "-f", "output_format",
    type = click.Choice(
        [
            "ABCT", 
            'auto', 
            'deriv', 
            'xml', 
            'conll', 
            'html', 
            'prolog', 
            'jigg_xml', 
            'ptb', 
            'json'
        ],
        case_sensitive = False
    ),
    default = "ABCT",
    metavar = "<output_format>",
    help = "the printing format of parsed sentences"
)
@click.pass_context
def cmd_main(
    ctx: click.Context,
    model: str,
    batch_size: int,
    is_to_tokenize: bool,
    output_format: str
):
    """
    Parse sentences in STDIN which are separated by line breaks.
    """
    parsed_trees, doc_tagged = core.parse_doc(
        doc = sys.stdin, 
        model_path = model,
        is_to_tokenize = is_to_tokenize,
        batchsize = batch_size
    )

    if output_format.lower() == "abct":
        for i, (parsed, tokens) in enumerate(zip(parsed_trees, doc_tagged), 1):
            core.dump_parsed_ABCT(parsed, tokens, i)
        # === END FOR ===
    else:
        core.dump_batch_parsed_others(
            parsed_trees,
            doc_tagged,
            output_format = output_format,
            lang = "ja",
            stream = sys.stdout,
        )
    # === END IF ===
# === END ===
