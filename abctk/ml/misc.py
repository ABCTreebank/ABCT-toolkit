import typing
import io

import itertools
import functools

import os
import shutil
import pathlib
import datetime
import json

# ======
# Data Types
# ======
class ModderSettings:
    """
        Settings for the `depccg.tools.ja.keyaki_reader` modifier.
        Attributes are added dynamically.
    """
# === END CLASS ===

# ======
# Parser
# ======
def parse_mod_target_line(line: str) -> typing.Optional[str]:
    """
        Parse a line of `target.txt` 
        (the list of categories occurring in the treebank) 
        in the directory of a digested treebank.
        Parameters
        ----------
        line : str
            A line of `target.txt`.
        Returns
        -------
        category : str, optional
            The category found in the given line.
            None when nothing is found.
    """
    entry_tokens = line.split()

    if not entry_tokens:
        return None
    # === END IF ===

    entry = entry_tokens[0]

    if entry in ["*START*", "*END*"]:
        return None
    else:
        return entry
    # === END IF ===
# === END ===

def parse_mod_unary_line(line: str) -> typing.List[str]:
    """
        Parse a line of `unary_rules.txt`
        (the list of unary rules in the treebank)
        in the directory of a digested treebank.
        Parameters
        ----------
        line : str
            A line of `unary_rules.txt`.
        Returns
        -------
        unary_rule : typing.List[str]
            A pair of categories which represents a permitted unary branching.
            The upper node goes to the second element of the list
            and the lower node to the first one.
            A empty list is returned 
            if the given line fails to represent a unary rule.
    """
    entry_tokens = line.split()

    if len(entry_tokens) < 2:
        return []
    else:
        return entry_tokens[0:2]
    # === END IF ===
# === END ===

CAT_CLAUSES: typing.Set[str] = {
    "S[m]", "S[a]", "S[e]", "S[sub]", 
    "S[imp]", "S[smc]", "S[nml]", "S[rel]",
    "CP[t]", "CP[q]", "CP[x]", "CP[f]", "multi-sentence"
}

CAT_PPS : typing.Set[str] = {
    "PP[s]", "PP[s2]", "PP[o1]", "PP[o2]"
}

CAT_NPS: typing.Set[str] = {
    "N", "N[s]", "NP", "NP[q]"
}

CAT_PP_LISTS_ORTHODOX_PL: typing.Set[typing.Tuple[str, ...]] = {
    ("PP[s2]", "PP[s]",) ,
    
    ("PP[o1]", "PP[s]"),
    ("PP[o1]", "PP[s2]", "PP[s]"),

    ("PP[o2]", "PP[o1]", "PP[s]"),
    ("PP[o2]", "PP[o1]", "PP[s2]", "PP[s]"),

    ("CP[t]", "PP[o1]", "PP[s]"),
    ("CP[t]", "PP[o1]", "PP[s2]", "PP[s]"),
}
    
CAT_PP_LISTS_ORTHODOX = CAT_PP_LISTS_ORTHODOX_PL | {("PP[s]", )}
CAT_PP_LISTS_ORTHODOX_WITHZERO = CAT_PP_LISTS_ORTHODOX | {tuple()}

CAT_PP_LISTS_SCRAMBLED: typing.Dict[tuple, typing.Set[tuple]] = {
    ortho:(
        set(
            itertools.permutations(ortho)
        ).difference({ortho})
    )
    for ortho in CAT_PP_LISTS_ORTHODOX_PL
}

def generate_category(
    head: str, 
    args: typing.Sequence[str], 
    is_bracketed = False
) -> str:
    if args:
        return "{br_open}{others}\\{arg}{br_close}".format(
            br_open = "(" if is_bracketed else "",
            br_close = ")" if is_bracketed else "",
            arg = args[0],
            others = generate_category(head, args[1:], True)
        )
    else:
        return head
    # === END IF ===
# === END ===

@functools.lru_cache()
def gen_unary_rules() -> typing.List[typing.Tuple[str, str]]:
    """
        Generate all the unary rules for the ABC Treebank.
        Returns
        -------
        unary_rules : typing.List[typing.Tuple[str, str]]
            A list of pairs of 
                categories which represents a permitted unary branching.
            Upper nodes are the second elements of the pairs
                and lower nodes are the first elements.
    """

    res: typing.List[typing.Tuple[str, str]] = []

    # ======
    # Scramblings
    # ======

    for ortho, scrs in CAT_PP_LISTS_SCRAMBLED.items():
        res.extend(
            (
                generate_category(cl, ortho), # inner 
                generate_category(cl, scr)    # outer
            )
            for scr in scrs
            for cl in CAT_CLAUSES
        )

    # ======
    # Covert pronominals
    # ======

    res.extend(
        (
            generate_category(cl, args),    # inner 
            generate_category(cl, args[1:]) # outer
        )
        for args in CAT_PP_LISTS_ORTHODOX
        for cl in CAT_CLAUSES
    )

    # ======
    # Adnominal clauses
    # ======
    res.extend(
        (
            generate_category("S[rel]", (arg, )), # inner
            f"{np}/{np}",                         # outer
        )
        for arg in CAT_PPS
        for np in CAT_NPS
    )

    # =====
    # Adverbial clauses
    # ======
    for cl, args in itertools.product(
            CAT_CLAUSES, 
            CAT_PP_LISTS_ORTHODOX_WITHZERO
    ):
        pred: str = generate_category(cl, args, is_bracketed = True)

        # Full
        res.append(
            (
                "S[a]",            # inner
                f"{pred}/{pred}", # outer
            )
        )

        # Controlled
        res.append(
            (
                "S[a]\\PP[s]",    # inner
                f"{pred}/{pred}", # outer
            )
        )
    # === END FOR ===

    # =====
    # Nominal Predicates
    # ======
    res.extend(
        (
            np,             # inner
            f"{cl}\\PP[s]", # outer
        )
        for cl in CAT_CLAUSES
        for np in CAT_NPS
    )
    # == END FOR ===

    # =====
    # Caseless DPs
    # ======
    for pp in CAT_PPS:
        res.append(
            (
                "NP", # inner
                pp,   # outer
            )
        )
    # === END FOR ===


    # ======
    # Other rules
    # ======

    res.extend(
        (
            ("N", "NP"), # Covert Determiner
            ("N", "NP[q]"), # Covert Determiner
            ("N[s]", "NP"), # Covert Determiner
            ("N[s]", "NP[q]"), # Covert Determiner

            ("S[sub]", "CP[q]", ), # Covert question marker

            # Admoninal NPs??
            # ("NP/NP", "NP"), 
            ("NP", "N/N", ), 
            ("NP", "N[s]/N[s]", ), 
            ("NP[q]", "N/N", ), 
            ("NP[q]", "N[s]/N[s]", ), 

            # Adverbial NPs  (frequent ones only)
            # e.g. きょう，昨日
            # ("(S[m]\\PP[s])/(S[m]\\PP[s])", "NP"),
            # ("(S[sub]\\PP[s])/(S[sub]\\PP[s])", "NP"),
            ("NP", "(S[m]\\PP[s])/(S[m]\\PP[s])", ),
            ("NP", "(S[e]\\PP[s])/(S[e]\\PP[s])", ),
            ("NP", "(S[a]\\PP[s])/(S[a]\\PP[s])", ),
            ("NP", "(S[rel]\\PP[s])/(S[rel]\\PP[s])", ),
            ("NP", "(CP[f]\\PP[s])/(CP[f]\\PP[s])", ),
            ("NP", "S[sub]/S[sub]", ),
            ("NP", "S[a]/S[a]", ),

            # Adverbial QPs
            ("NP[q]", "(S[m]\\PP[s])/(S[m]\\PP[s])", ),
            ("NP[q]", "(S[a]\\PP[s])/(S[a]\\PP[s])", ),
            ("NP[q]", "S[m]/S[m]", ),

            # Peculiar Srel
            ("S[rel]", "NP/NP", ),

            # single NUM
            ("NUM", "N"), 
            ("NUM", "N[s]"), 
        )
    )

    return res
# === END ===

def create_mod_treebank(
    p_treebank: pathlib.Path,
    dir_output: pathlib.Path,
    mode: str
) -> ModderSettings:
    """
        Digest a raw treebank file via `depccg.tools.ja.keyaki_reader` and 
        dump the results to the designated output folder.
        The used settings is what this function returns.
        Parameters
        ----------
        p_treebank : pathlib.Path
            The path to the treebank, which is a single file.
        Returns
        -------
        parser_settings : ModderSettings
            A default set of settings of the digester,
            which may be necessary later.
    """

    modder_settings = ModderSettings()
    modder_settings.PATH = p_treebank
    modder_settings.OUT = dir_output
    modder_settings.word_freq_cut = 5
    modder_settings.afix_freq_cut = 5
    modder_settings.char_freq_cut = 5
    modder_settings.cat_freq_cut = 5

    import depccg.tools.ja.keyaki_reader as kr

    # Do the digest
    if mode == "train":
        kr.TrainingDataCreator.create_traindata(
            modder_settings,
        )
        # Add the list of categories to the modder settings
        with open(dir_output / "target.txt") as h_target:
            modder_settings.targets = list(
                filter(
                    None,
                    map(parse_mod_target_line, h_target)
                )
            )
        # === END WITH h_target ===            

        # Add the list of unary rules to the modder settings
        modder_settings.unary_rules = gen_unary_rules()
    elif mode == "test":
        kr.TrainingDataCreator.create_testdata(
            modder_settings,
        )
    else:
        raise ValueError
    # === END IF ===

    return modder_settings
# === END ===

