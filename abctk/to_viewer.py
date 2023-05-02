from typing import Any, Union, Optional

import svgling
from nltk import Tree

from abctk.obj.ID import RecordID
from abctk.obj.Keyaki import Keyaki_ID

def to_viewer(
    tree: Union[Tree, str],
    ID: Optional[RecordID] = None,
) -> dict[str, Any]:
    """
    Pack tree info to the amoove viewer.

    Returns
    -------
    """
    return {
        "id": (ID if ID else Keyaki_ID.new()).__dict__,
        "parse": svgling.draw_tree(tree)._repr_svg_(),
    }