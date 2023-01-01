from collections import Counter
import logging
logger = logging.getLogger(__name__)

import typing
import re

from nltk.tree import Tree

from abctk import ABCTException
from abctk.obj.ABCCat import Annot

_re_comp = re.compile(r"^(?P<index>[0-9]),(?P<names>.+)$")

class UngrammaticalCompFeatureException(ABCTException):
    ID: str
    feat: str

    def __init__(self, ID: str, feat: str) -> None:
        self.ID = ID
        self.feat = feat

        super().__init__(
            f"A ungrammatical #comp feature is found: '{self.feat}'. "
            f"Tree ID: {ID}"
        )

class IncorrectlyPlacedCompFeatureException(ABCTException):
    ID: str
    feat: str

    def __init__(self, ID: str, feat: str) -> None:
        self.ID = ID
        self.feat = feat

        super().__init__(
            f"An incorrectly placed #comp feature is found: '{self.feat}'. Maybe it is not dominated by '#comp=root'. "
            f"Tree ID: {ID}"
        )


class ExcessiveCompFeatureException(ABCTException):
    ID: str
    index: str
    feat: str
    count: int

    def __init__(self, ID: str, index: str, feat: str, count: int) -> None:
        self.ID = ID
        self.feat = feat

        super().__init__(
            "Excessive #comp feature is found. "
            f"There are/is {count} {feat}(s) with index {index}, which are/is excessive/not enough. "
            f"Tree ID: {ID}"
        )


def check_comp_feats(
    root_found: typing.Dict[str, typing.Counter[str]],
    ID: str = "<UNKNOWN>",
) -> None:
    for index, counter in root_found.items():
        if "root" not in counter:
            raise ExcessiveCompFeatureException(
                ID, index, "root", 0
            )
        
        for feat, count in counter.items():
            if count > 1:
                raise ExcessiveCompFeatureException(
                    ID, index, feat, count
                )

def collect_comp_feats(
    tree: Tree,
    ID: str = "<UNKNOWN>",
    root_found: typing.Optional[typing.Dict[str, typing.Counter[str]]] = None,
) -> typing.Dict[str, typing.Counter[str]]:
    root_found = root_found or dict()

    # Collect info of the children
    for child in tree:
        if isinstance(child, Tree):
            collect_comp_feats(child, ID, root_found)

    label: Annot = tree.label()

    if (
        (feat_comp := label.feats.get("comp"))
    ):
        if (feat_comp_match := _re_comp.match(feat_comp)):
            match_res = feat_comp_match.groupdict()
            index = match_res["index"]
            feats = match_res["names"].split(",")

            if "bind" in feats:
                # skip this feature
                # do nothing 
                pass
            else:
                if len(feats) == 0:
                    raise UngrammaticalCompFeatureException(ID, feat_comp)

                if index not in root_found:
                    root_found["index"] = Counter()
                
                counter = root_found["index"]
                if ("root" in counter and len(feats) > 0):
                    raise IncorrectlyPlacedCompFeatureException(ID, feat_comp)

                if any(
                    f not in ("root", "prej", "cont", "deg", "diff", "auto")
                    for f in feats
                ):
                    raise IncorrectlyPlacedCompFeatureException(ID, feat_comp)

                # Tests passed
                root_found["index"].update(feats)
        else:
            raise UngrammaticalCompFeatureException(ID, feat_comp)

    return root_found