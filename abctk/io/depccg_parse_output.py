import jsonlines
import typing

from nltk import Tree

from abctk.obj.Keyaki import Keyaki_ID
from abctk.obj.ABCCat import ABCCat, ABCCatReprMode, Annot

def load_ABC_parsed_jsonl_psd(
    input: typing.TextIO,
    name: str = "RESULT"
) -> typing.Iterator[typing.Tuple[Keyaki_ID, Tree]]:
    def _conv(tree: dict) -> Tree:
        if "children" in tree:
            children_conved = list(
                _conv(child) for child in tree["children"]
            )
            return Tree(
                Annot(
                    ABCCat.parse(tree["cat"], mode = ABCCatReprMode.DEPCCG),
                    pprinter_cat = ABCCat.pprint
                ),
                children_conved
            )
        else:
            # lexical node
            return Tree(
                Annot(
                    ABCCat.parse(tree["cat"], mode = ABCCatReprMode.DEPCCG),
                    pprinter_cat = ABCCat.pprint
                ),
                [tree["word"]]
            )
    # === END ===

    for i, obj in enumerate(jsonlines.Reader(input)):
        for j, tree in enumerate(obj["trees"]):
            prob = tree["log_prob"]
            tree = _conv(tree)
            tree.append(
                Tree(
                    "COMMENT",
                    [f"{{prob={prob}}}"]
                )
            )
            yield Keyaki_ID(name, i**3 + j**2, ""), tree
# === END ===

