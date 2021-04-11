from .core import (
    IPrettyPrintable,
    TypedTree,
    TypedTreeIndex,
    get_ID_from_TypedTree,
    get_ID_maybe_from_TypedTree,
    gen_random_ID_of_str_against_TypedTreeIndex,
    sample_from_TypedTreeIndex,
    TypedTreebank,
    treeIDstr_to_path_default,
)

from .real import (
    ABCDepMarking,
    ABCCatPlus,
    KeyakiCat,
    KeyakiCat_ABCCatPlus,
    ABCCatBot,
    ABCCatFunctorMode,
    ABCCatFunctor,
    ABCCat,
    ABCCat_ABCCatPlus,
    KeyakiTree,
    KeyakiTree_ABCCatPlus,
    ABCTree_ABCCatPlus,
    parser_ABCCat,
    make_path_from_Keyaki_or_ABC_ID,
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