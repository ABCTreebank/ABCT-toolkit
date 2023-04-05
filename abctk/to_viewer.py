from typing import Any, Union, Optional

import svgling
from nltk import Tree

from abctk.obj.Keyaki import Keyaki_ID

def to_viewer(
    tree: Union[Tree, str],
    ID: Optional[Keyaki_ID] = None,
) -> dict[str, Any]:
    """
    Pack tree info to the amoove viewer.

    Returns
    -------
    """
    return {
        "id": (ID if ID else Keyaki_ID("", 0, ""))._asdict(),
        "parse": svgling.draw_tree(tree)._repr_svg_(),
    }