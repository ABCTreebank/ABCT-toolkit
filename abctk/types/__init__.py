from .ABCCat import (
    ABCCatFunctorMode, 
    ABCCatFunctor,
    ABCCatBot,
    ABCCat,
    parser_ABCCat,
    parse_ABCCat,
)
from .ABCCatPlus import (
    ABCDepMarking,
    ABCCatPlus,
    parser_ABCCatPlus,
)
from .trees import (
    Tree,
    Tree_with_ID,
    parser_Tree,
    parse_Tree,
    parser_Tree_with_ID,
    parser_Tree_Maybe_with_ID,
    parse_Tree_Maybe_with_ID,
    parse_ManyTrees_Maybe_with_ID,
)

import logging
logger = logging.getLogger(__name__)
import sys

RECURSION_LIMIT: int = 10000
sys.setrecursionlimit(RECURSION_LIMIT)
logger.info(
    f"The recursion limit is set to {RECURSION_LIMIT} in order to deal with trees with deep recursion. "
    "This will be made customizable in the future."
)