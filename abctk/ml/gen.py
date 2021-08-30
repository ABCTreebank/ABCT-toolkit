"""
Generating training & testing datasets that feed depccg / AllenNLP model training.
"""

from collections import Counter
import itertools
import logging
logger = logging.getLogger(__name__)
import numbers
import pathlib
import random
random.seed()
import sys
import typing

import tqdm

import attr
import fs
import fs.base
import simplejson as json

import abctk.types.ABCCat as abcc

UNK = "*UNKNOWN*"
"""
The special token for unknown words.
"""

START = "*START*"
"""
The dummy token put at the beginning of a sentence.
"""

END = "*END*"
"""
The dummy token that is put at the end of a sentence.
"""

IGNORE = -1

@attr.s(auto_attribs = True, slots = True)
class DepCCGIneligibleTreeException(Exception):
    """
    An exception raised when a given ABC Treebank tree is not
    eligible for the purpose of the depccg model training.
    """
    message: str

@attr.s(auto_attribs = True, slots = True)
class DepCCGDataSetGenerationSettings:
    """
    A collection of settings relevant 
    to the model training dataset generation process.
    """
    
    sents_test_ext: typing.Tuple[
        str,
        numbers.Real
    ] = ("ratio", 0.2)
    """
    The specification of the number or ratio of test data, which is a complex tuple comprised of two elements.
    
    The first element of the tuple specifies the way that the number of test data is decided. `abs` determines the count absolutely.
    When it is set to `ratio`, the count will be a relativized ratio to
    the number of the whole input sentences.

    The second element of the tuple specifies the number of the test sentences, either an absolute count or a relativized ratio. 
    """

    cat_freq_cut: int = 10
    word_freq_cut: int = 5
    affix_feq_cut: int = 5
    char_freq_cut: int = 5

NodeOfInstance = typing.Tuple[int, str, str, int]
# id, word, cat (pprinted in the DepCCG format), head_id

@attr.s(auto_attribs = True, slots = True)
class Instance:
    """
    Representing a piece of data (an instance) of AllenNLP training processes.
    """
    analysis: typing.Sequence[NodeOfInstance]
    """
    A collection of nodes comprising a tree.
    """
    
    ID: str = "<UNKNOWN>"
    """
    The ID in the ABC Treebank.
    """

    def spellout(self):
        """
        Spell out the sentence, each word separated by a whitespace.
        """
        return " ".join(
            sent for _, sent, _, _ in sorted(self.analysis)
        )

    @classmethod
    def from_ABC_NLTK_tree(
        cls, 
        tree: "nltk.Tree", 
        ID: str = "<UNKNOWN>"
    ) -> typing.Tuple[
        "Instance",
        typing.List[typing.Tuple[str, str]],
        typing.List[typing.Tuple[str, str]],
    ]:
        """
        Read an ABC tree represented as an NLTK tree instance
        and try to create an instance from it.

        Returns
        -------
        instance: Instance
        unary_nodes: typing.Tuple[str, str]
        binary_rules_seen: typing.Tuple[str, str]

        Raises
        ------
        DepCCGIneligibleTreeException:
            It might be raised when encountering an non-unary non-eligible branching.
        """
        from nltk import Tree

        counter = 0
        stack: typing.List[
            typing.Tuple[
                typing.Union[str, Tree], 
                bool
            ]
        ] = [
            (tree, True),
            (tree, False),
        ]
        list_node = []
        nodes_head_annotated: typing.Set[
            typing.Tuple[int, str, str, int]
        ] = set()
        list_unary = []
        list_binary_seen = []

        while stack:
            pointer, is_returning = stack.pop()

            if not is_returning:
                if isinstance(pointer, Tree):
                    pointer_cat_raw, pointer_feats = abcc.parse_annot(pointer.label())
                    pointer_cat_parsed = abcc.ABCCat.p(pointer_cat_raw).pprint(abcc.ABCCatReprMode.DEPCCG)
                    len_children = len(pointer)

                    if pointer_feats.get("deriv", "") == "leave":
                        raise DepCCGIneligibleTreeException("Non-CCG derivations are not supported")
                    elif len_children == 1:
                        only_child = pointer[0]
                        # check if it is a terminal node with just one lexical node
                        if isinstance(only_child, str):
                            # (pointer: terminal) - (only_child : lexical node)
                            counter += 1
                            if only_child.startswith("*") or only_child.startswith("__"):
                                raise DepCCGIneligibleTreeException("Empty categories are not supported as of now.")
                                
                            list_node.append(
                                (counter, only_child, pointer_cat_parsed)
                            )

                        elif isinstance(only_child, Tree):
                            # unary node
                            only_child_cat_raw, _ = abcc.parse_annot(only_child.label())
                            only_child_cat_parsed = abcc.ABCCat.p(only_child_cat_raw).pprint(abcc.ABCCatReprMode.DEPCCG)

                            list_unary.append(
                                (pointer_cat_parsed, only_child_cat_parsed)
                            )
                            stack.extend(
                                (
                                    (pointer, True),
                                    (only_child, False)
                                )
                            )
                        else:
                            raise TypeError
                    elif len_children == 2:
                        # binary branching
                        child_1, child_2 = pointer
                        child_1_cat_raw, _ = abcc.parse_annot(child_1.label())
                        child_1_cat_converted = abcc.ABCCat.p(child_1_cat_raw).pprint(abcc.ABCCatReprMode.DEPCCG)
                        child_2_cat_raw, _ = abcc.parse_annot(child_2.label())
                        child_2_cat_converted = abcc.ABCCat.p(child_2_cat_raw).pprint(abcc.ABCCatReprMode.DEPCCG)

                        list_binary_seen.append(
                            (child_1_cat_converted, child_2_cat_converted)
                        )
                        stack.extend(
                            (
                                (pointer, True),
                                (child_2, False),
                                (child_1, False),
                            )
                        )
                    else:
                        raise DepCCGIneligibleTreeException("Non-binary branching detected")
                else:
                    raise TypeError
            else: # is_returning
                if len(list_node) > 0:
                    num_childern = len(pointer)
                    list_node, lex_node_children_others, lex_node_children_last = list_node[:-num_childern], list_node[-num_childern:-1], list_node[-1]
                    
                    head_index, head_word, head_cat = lex_node_children_last

                    nodes_head_annotated.update(
                        (i, w, cat, head_index)
                        for i, w, cat
                        in lex_node_children_others
                    )

                    list_node.append(
                        (
                            head_index, head_word, head_cat
                        )
                    )
                else:
                    raise RuntimeError
            
        nodes_head_annotated.update(
            (i, w, cat, 0)
            for i, w, cat in list_node
        )
        return (
            cls(nodes_head_annotated, ID = ID),
            list_unary, list_binary_seen
        )

    def to_json_list(self):
        ana = self.analysis
        return [
            " ".join(word for _, word, _, _ in ana),
            [
                [cat  for _, _, cat, _  in ana],
                [head for _, _, _, head in ana],
            ]
        ]
    
@attr.s(auto_attribs = True, slots = True)
class DepCCGDataSet:
    """
    A stockpile of training / testing instances created from the ABC Treebank.
    """
    
    sents_train: typing.List[Instance] = attr.ib(factory = list)
    """
    A collection of instances for training.
    """
    
    sents_test: typing.List[Instance] = attr.ib(factory = list)
    """
    A collection of instances for testing.
    """

    unary_rules: typing.Counter[typing.Tuple[str, str]] = attr.ib(factory = Counter)
    """
    A collection of unary rules with frequencies.
    """

    binary_rules_seen: typing.Counter[typing.Tuple[str, str]] = attr.ib(factory = Counter)
    """
    A collection of attested binary rules with frequencies.
    """
    
    settings: DepCCGDataSetGenerationSettings = attr.ib(
        factory = DepCCGDataSetGenerationSettings
    )
    """
    An assortment of settings.
    """

    def count_sents(self) -> typing.Dict[str, int]:
        """
        Count the number of sentences.

        Returns
        -------
        info: dict
        """

        return {
            "sents_train": len(self.sents_train),
            "sents_test": len(self.sents_test),
        }
    
    def gen_vocab(self, do_cut: bool = True):
        """
        Create a vocabulary from the stored sentences.

        Arguments
        ---------
        do_cut : bool
            When `True`, cut words whose frequency is below what is set in the settings.
        """
        res = Counter(
            word 
            for _, word, _, _ 
            in itertools.chain.from_iterable(
                inst.analysis
                for inst in self.sents_train
            )
        )
        cut = self.settings.word_freq_cut

        if do_cut:
            for word in list(res.keys()):
                if res[word] < cut:
                    del res[word]

        res.update(
            UNK = cut,
            START = cut,
            END = cut,
        )

        return res
    
    def gen_cat(self, do_cut: bool = True):
        """
        Create a set of attestd lexical categories from the stored sentences.

        Arguments
        ---------
        do_cut : bool
            When `True`, cut categories whose frequency is below what is set in the settings.
        """

        res = Counter(
            cat 
            for _, _, cat, _ 
            in itertools.chain.from_iterable(
                inst.analysis
                for inst in self.sents_train
            )
        )

        cut = self.settings.cat_freq_cut
        if do_cut:
            for word in list(res.keys()):
                if res[word] < cut:
                    del res[word]

        res.update(
            START = cut,
            END = cut,
        )
        return res

    @classmethod
    def from_ABC_NLTK_trees(
        cls, 
        trees: typing.Sequence["nltk.Tree"],
        settings: DepCCGDataSetGenerationSettings = DepCCGDataSetGenerationSettings(),
        prog_stream: typing.Optional[typing.IO] = sys.stderr,
    ):
        """
        Convert the ABC Treebank into a dataset for model training.
        Each sentence of the treebank is supposed to be parsed as an NLTK tree beforehand, as the type signature evidently tells.

        Arguments
        ---------
        trees: typing.Sequence[nltk.Tree]
        settings: DepCCGDataSetGenerationSettings
        prog_stream: typing.IO, optional
            The stream where tqdm progress bars are redirected to and show up there.
            Feature disabled when set to `None`. 
        """
        from nltk import Tree
        dataset = cls(settings = settings)
        size_before_filter = len(trees)

        # convert trees before dispatching
        if prog_stream:
            prog_obj = tqdm.tqdm(
                desc = "trees read",
                total = size_before_filter,
                file = prog_stream,
                position = 0,
                bar_format = "{desc:<25}|{bar:50}|{percentage:3.0f}%, {n_fmt}/{total_fmt} [{elapsed}<{remaining}]"
            )
            prog_elim = tqdm.tqdm(
                desc = "trees not discarded (yet)",
                total = size_before_filter,
                initial = size_before_filter,
                file = prog_stream,
                position = 1,
                ascii = " ▒▒▒▒▒▒▒▒▒▒▒",
                bar_format = "{desc:<25}|{bar:50}|{percentage:3.0f}%, {n_fmt}/{total_fmt}"

            )
        else:
            prog_obj = None
            prog_elim = None

        def _convert_ABC_tree(
            tree: Tree,
            pg_obj: typing.Optional[tqdm.tqdm],
            pg_disc: typing.Optional[tqdm.tqdm],
        ):
            # ripping off IDs
            if len(tree) == 2:
                child_1, child_2 = tree
                if child_2.label() == "ID" and len(child_2) == 1 and isinstance(child_2[0], abcc.ABCCatReady.__args__):
                    ID = child_2[0]
                    tree = child_1
                else:
                    ID = "<UNKNOWN>"
            else:
                ID = "<UNKWOWN>"

            try: # to create an instance
                res = Instance.from_ABC_NLTK_tree(
                    tree, ID
                )
            except DepCCGIneligibleTreeException as e:
                logger.info(
                    "Tree (ID: {ID}) is discarded. Reason: {e.message}"
                )
                res = None

                if pg_disc is not None:
                    pg_disc.update(-1)

            if pg_obj is not None:
                pg_obj.update()

            return res

        trees_parsed: typing.Tuple[
            typing.Tuple[
                "Instance",
                typing.List[typing.Tuple[str, str]],
                typing.List[typing.Tuple[str, str]],
            ], ...
            ] = tuple(
            filter(
                None,
                (
                    _convert_ABC_tree(tree, prog_obj, prog_elim)
                    for tree in trees
                )
            )
        )

        # randomly pick up sentences for testing
        size = len(trees_parsed)
        
        test_ext_type, test_ext_value = settings.sents_test_ext
        if test_ext_type == "ratio":
            size_test = int(size * test_ext_value)
        else:
            size_test = int(test_ext_value)
        
        mask_sents = list(
                (False, ) * size_test
                + (True, ) * (size - size_test)
            )
        random.shuffle(mask_sents)

        for (inst, unaries, binary_seen), is_training in zip(trees_parsed, mask_sents):
            if is_training:
                dataset.sents_train.append(inst)
                dataset.unary_rules.update(unaries)
                dataset.binary_rules_seen.update(binary_seen)
            else:
                dataset.sents_test.append(inst)

        return dataset

    def collect_parser_config(
        self, 
        add_seen_rules: bool = False
    ) -> typing.Dict[str, typing.KeysView]:
        """
        Organize a vocabulary and a set of categories and rules
        that are required by model prediction (parsing).

        Arguments
        ---------
        add_seen_rules: bool

        Notes
        -----
        The values are of type `typing.KeywView`,
            which is not supported by the buitlin `json` package.
        `Simplejson <https://pypi.org/project/simplejson/>`_, which does support it, is used instead in this module, whic, by the way, is recommended on other occasions.
        """

        res = {
            "targets": self.gen_cat().keys(),
            "unary_rules": self.unary_rules.keys(),
        }

        if add_seen_rules:
            res["seen_rules"] = self.binary_rules_seen.keys()

        return res

    def dump(
        self, 
        folder: typing.Union[str, pathlib.Path, fs.base.FS],
        add_seen_rules: bool = False,
    ) -> None:
        """
        Dump the dataset to the disk.
        The following files will be generated.
        * traindata.json
        * testdata.json
        * config_abc.json: a conf file for prediction (parsing).

        Warnings
        --------
        Existing files will be overwritten without any notice.

        Arguments
        ---------
        folder: str or pathlib.Path or fs.base.FS
            A destination folder.
            This supports `PyFilesystems2 <https://pypi.org/project/fs/>`_, which enables us to treat archives and web repositories as if they were just a directory.
        """
        if isinstance(folder, pathlib.Path):
            folder = str(folder)
        
        with fs.open_fs(folder) as output_fs:
            with output_fs.open("traindata.json", "w") as f_traindata:
                json.dump(
                    (inst.to_json_list() for inst in self.sents_train),
                    f_traindata,
                    iterable_as_array = True,
                )
            with output_fs.open("testdata.json", "w") as f_testdata:
                json.dump(
                    (inst.to_json_list() for inst in self.sents_train),
                    f_testdata,
                    iterable_as_array = True,
                )

            with output_fs.open("config_abc.json", "w") as f_config_abc:
                json.dump(
                    self.collect_parser_config(add_seen_rules),
                    f_config_abc,
                    iterable_as_array = True,
                )

            # Vocabulary folder
            output_fs.makedir("vocabulary", recreate = True)

            with output_fs.open("vocabulary/head_tags.txt", "w") as f_head_tags:
                f_head_tags.write("@@UNKNOWN@@\n")
                f_head_tags.write(
                    "\n".join(self.gen_cat().keys())
                )

            with output_fs.open("vocabulary/tokens.txt", "w") as f_tokens:
                f_tokens.write("@@UNKNOWN@@\n")
                f_tokens.write(
                    "\n".join(self.gen_vocab().keys())
                )
                
            output_fs.create("vocabulary/non_padded_namespaces.txt")
