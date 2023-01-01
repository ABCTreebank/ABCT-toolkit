import logging
logger = logging.getLogger(__name__)
import re
import typing

import janome.lattice
from janome.lattice import Node as JNode
import janome.tokenizer
from janome.tokenizer import Token as JToken

from nltk.tree import Tree
import lxml.etree as et
from abctk import ABCTException

import abctk.obj.ABCCat as abcc

class ABCMorphAnalyzer(janome.tokenizer.Tokenizer):
    def analyze(
        self, 
        text: typing.Sequence[str], 
        *, 
        baseform_unk: bool = True, 
        dotfile: str = ''
    ) -> list[JToken]:
        """
        Give a morphological analysis of an input text which is divided into words beforehand.

        Arguments
        ----------
        text:
            An iterable of unicode strings that is divieded beforehand
        baseform_unk: bool
            If given True sets base_form attribute for unknown tokens.
        dotfile:
            If specified, graphviz dot file is output to the path for later visualizing
            of the lattice graph.
            This option is ignored when the input length is
            larger than MAX_CHUNK_SIZE.

        Yields
        ------
        token: tokens or str
            tokens (wakati=False) or string (wakati=True)
        """
        return self.__analyze(
            text,
            baseform_unk,
            dotfile 
                if dotfile and len(text) < janome.tokenizer.Tokenizer.MAX_CHUNK_SIZE 
                else None
        )
    # === END ===

    def __analyze(
        self, 
        text: typing.Iterable[str], 
        baseform_unk, 
        dotfile
    ) -> list[JToken]:
        chunk_size = min(
            sum(map(len, text)),
            janome.tokenizer.Tokenizer.MAX_CHUNK_SIZE
        )
        
        lattice = janome.lattice.Lattice(chunk_size, self.sys_dic)

        for w in text:
            matched: bool = False
            encoded_partial_text = w.encode('utf-8')

            # user dictionary
            if self.user_dic:
                entries = self.user_dic.lookup(encoded_partial_text)
                for e in filter(lambda ent: ent[1] == w, entries):
                    lattice.add(janome.lattice.SurfaceNode(e, janome.lattice.NodeType.USER_DICT))
                matched |= bool(entries)
            else:
                pass
            # == END IF ===

            # system dictionary
            entries = self.sys_dic.lookup(encoded_partial_text)
            for e in filter(lambda ent: ent[1] == w, entries):
                lattice.add(janome.lattice.SurfaceNode(e, janome.lattice.NodeType.SYS_DICT))
                matched |= bool(entries)

            # unknown
            cates = self.sys_dic.get_char_categories(w[0])
            if cates:
                for cate in cates:
                    if matched and not self.sys_dic.unknown_invoked_always(cate):
                        continue
                    # unknown word length
                    length = self.sys_dic.unknown_length(cate) \
                        if not self.sys_dic.unknown_grouping(cate) else self.max_unknown_length
                    assert length >= 0

                    unknown_entries = self.sys_dic.unknowns.get(cate)
                    assert unknown_entries

                    for entry in unknown_entries:
                        left_id, right_id, cost, part_of_speech = entry
                        base_form = w if baseform_unk else '*'
                        dummy_dict_entry = (
                            w, 
                            left_id, 
                            right_id, 
                            cost, 
                            part_of_speech, 
                            '*', 
                            '*', 
                            base_form, 
                            '*', 
                            '*'
                        )
                        lattice.add(JNode(dummy_dict_entry, janome.lattice.NodeType.UNKNOWN))
                    # === END FOR entry ===
                # === END FOR cate ===
            # === END IF ===
            lattice.forward()
        # === END FOR w ===

        lattice.end()

        min_cost_path = lattice.backward()
        assert isinstance(min_cost_path[0], janome.lattice.BOS)
        assert isinstance(min_cost_path[-1], janome.lattice.EOS)

        tokens = []
        for node in min_cost_path[1:-1]:
            if type(node) == janome.lattice.SurfaceNode and node.node_type == janome.lattice.NodeType.SYS_DICT:
                tokens.append(JToken(node, self.sys_dic.lookup_extra(node.num)))
            elif type(node) == janome.lattice.SurfaceNode and node.node_type == janome.lattice.NodeType.USER_DICT:
                tokens.append(JToken(node, self.user_dic.lookup_extra(node.num)))
            else:
                tokens.append(JToken(node))
        if dotfile:
            lattice.generate_dotfile(filename=dotfile)

        return tokens
    # === END ===

_janome_tokenizer: typing.Optional[ABCMorphAnalyzer] = None

def _morph_analyze_janome(tokens_root: et._Element):
    tokens = tuple(tokens_root.xpath("token"))

    surf_tokens: tuple[str, ...] = tuple(
        token.get("surf", "*")
        for token in tokens
    )

    surf_tokens_mask = tuple(
        not form.startswith("*")
        and not form.startswith("__")
        for form in surf_tokens
    )

    surf_token_nonempty = tuple(
        form 
        for form, is_non_empty 
        in zip(surf_tokens, surf_tokens_mask)
        if is_non_empty
    )

    surf_token_nonempty_indices = tuple(
        i
        for i, is_non_empty 
        in enumerate(surf_tokens_mask)
        if is_non_empty
    )

    global _janome_tokenizer
    if _janome_tokenizer is None:
        _janome_tokenizer = ABCMorphAnalyzer()

    for i, token_analyzed in zip(
        surf_token_nonempty_indices,
        _janome_tokenizer.analyze(
            text = surf_token_nonempty,
        )
    ):
        token_xml = tokens[i]

        attribs = {
            "base": token_analyzed.base_form,
            "pron": token_analyzed.phonetic,
            "yomi": token_analyzed.reading,
            "lemma": "", # no viable attrib?
            "cForm": token_analyzed.info_form,
            "cType": token_analyzed.infl_type,
        }
        for key, val in attribs.items():
            token_xml.set(key, val or "*")

        pos = str(token_analyzed.part_of_speech)
        pos_split = pos.split(",")
        if len(pos_split) == 1:
            token_xml.set("pos", pos)
        else:
            for i, pos_i in enumerate(pos_split):
                token_xml.set(f"pos{i}", pos_i)

    tokens_root.set(
        "annotators",
        "janome"
    )
    # === END ===

class _t2jg_Writer(typing.NamedTuple):
    token_span_begin: int
    token_span_end: int
    token_span_name: str
    is_terminal: bool = False
    pointer: typing.Optional[et._Element] = None

class JIGGConvException(ABCTException):
    ID: str

    def __init__(self, ID: str):
        self.ID = ID
        super().__init__(f'Conversion error at Tree {ID}')

def tree_to_jigg(
    tree: Tree,
    ID: str = "<UNKNOWN>",
    jigg_ID: typing.Any = 0,
    postag_dict: typing.Optional[list] = None,
) -> et._Element:
    """
    Put an ABC Tree in the JIGG format.
    
    Parameters
    ----------
    tree
    ID
    jigg_ID
    postag_dict

    Returns
    ------
    xml

    Raises
    ------
    JIGGConvException
    """
    if not postag_dict: 
        postag_dict = []

    xml_pool: et._Element = et.Element(
        "sentence",
        abc_id = str(ID),
    )
    # NOTE: no ID yet

    try:
        xml_pool.text = "".join(tree.leaves())
        xml_tokens: et._Element = et.SubElement(xml_pool, "tokens")
        # NOTE: no ID yet

        xml_ccgs: et._Element = et.SubElement(xml_pool, "ccg")
        xml_ccgs.set("id", f"{jigg_ID}_ccg0")

        # 1. Annotation creation
        call_stack: list[tuple[Tree, bool]] = [(tree, False)]
        return_stack: list[_t2jg_Writer] = list()

        token_id_count: int = 0
        span_id_count: int = 0
        token_offset_count: int = 0
        while call_stack:
            pointer, is_back = call_stack.pop()
            if is_back:
                # take return values
                if not isinstance(pointer, Tree):
                    raise TypeError

                children_num = len(pointer)

                return_stack, return_values = return_stack[:-children_num], return_stack[-children_num:]

                label = pointer.label()
                if not isinstance(label, abcc.Annot):
                    raise TypeError
                label_cat = abcc.ABCCat.p(label.cat)
                
                token_span_begin = min(w.token_span_begin for w in return_values)
                token_span_end = min(w.token_span_end for w in return_values)
                token_span_name = f"s{jigg_ID}_sp{span_id_count}"


                xml_span = et.SubElement(
                    xml_ccgs,
                    "span",
                    category = label_cat.pprint(
                        mode = abcc.ABCCatReprMode.CCG2LAMBDA
                    ),
                    begin = str(token_span_begin),
                    end = str(token_span_end),
                    id = token_span_name,
                )

                return_first_child = return_values[0]
                is_subterminal = len(return_values) == 1 and return_first_child.is_terminal

                # find the derivational rule of the subtree
                if not is_subterminal:
                    span_rule = label.feats.get("deriv", "unknown")
                    # "unknown" by default

                    if span_rule != "unknown":
                        # rule manually specified
                        # do nothing
                        pass
                    else:
                        # find whether it is a comparative binding
                        comparative_maybe: str = label.feats.get("comp", "")
                        _re = re.compile(r"(?P<num>[0-9]+),(?P<role>[a-zA-Z]+),bind")
                        comp_parsed = _re.match(comparative_maybe)
                        if comp_parsed:
                            # comparative binding
                            d = comp_parsed.groupdict()
                            # trace = f"*{d['role']}{d['num']}*"
                            span_rule = f"|-intro-{d['role']}{d['num']}"
                        else:
                            # find whether it is a relative or adv clause binding
                            binder: str = ""
                            is_bound: bool = label.feats.get("rel", "") == "bind"
                            if is_bound:
                                binder = "rel"
                            elif (is_bound := label.feats.get("adv-pro", "") == "bind"):
                                binder = "adv-pro"

                            if is_bound:
                                # unselective binding (to *T* and *TRACE-pro*)
                                span_rule = f"|-intro-{binder}"
                            else:
                                # try to automatically find it
                                if children_num == 2:
                                    child_1, child_2 = pointer
                                    child_1_cat: abcc.ABCCat = abcc.ABCCat.parse(child_1.label().cat)
                                    child_2_cat: abcc.ABCCat= abcc.ABCCat.parse(child_2.label().cat)
                                    simp_candidates = abcc.ABCCat.simplify_exh(child_1_cat, child_2_cat)
                                    if simp_candidates:
                                        _, simp_elimtype = next(iter(simp_candidates))
                                        span_rule = str(simp_elimtype)

                                        # hack: specify direction for |-elim rules
                                        # ccg2lambda_tools.py: 103
                                        if span_rule == "|":
                                            if isinstance(child_1_cat, abcc.ABCCatFunctor) and child_1_cat.ant == child_2_cat:
                                                # (_|child_2) child_2
                                                span_rule = "|>"
                                            else:
                                                span_rule = "|<"
                                elif children_num == 1:
                                    span_rule = "unary" # the default unary rule

                    xml_span.set(
                        "rule",
                        span_rule,
                    )
                # === END IF not is_subterminal ===

                if len(return_values) == 1:
                    return_unary_child, = return_values
                    pointer_token = return_unary_child.pointer
                    if (
                        return_unary_child.is_terminal
                        and pointer_token is not None
                    ):
                        xml_span.set(
                            "terminal",
                            return_unary_child.token_span_name,
                        )
                        # add additional POS
                        # match with
                        for tag in postag_dict:
                            if (
                                label_cat.unify(tag["category"])
                                and pointer_token.attrib["base"] in tag["base"]
                            ):
                                pointer_token.set("pos", tag["pos"])
                                break

                    else:
                        xml_span.set(
                            "child",
                            " ".join(
                                w.token_span_name for w in return_values
                            ),
                        )
                else:
                    xml_span.set(
                        "child",
                        " ".join(
                            w.token_span_name for w in return_values
                        ),
                    )


                return_stack.append(
                    _t2jg_Writer(
                        token_span_begin = token_span_begin,
                        token_span_end = token_span_end,
                        token_span_name = token_span_name,
                    )
                )

                span_id_count += 1
            else: # not
                if isinstance(pointer, Tree):
                    # The tree is non-terminal:
                    call_stack.append((pointer, True))
                    call_stack.extend((child, False) for child in reversed(pointer))
                    # child_1-call, ... , child_n-call, pointer-back, ++ ...
                elif isinstance(pointer, str):
                    # The tree is terminal
                    token_id_count_end = token_id_count + 1
                    token_offset_count_end = token_offset_count + len(pointer)
                    token_name = f"s{jigg_ID}_{token_id_count}"
                    token_xml = et.SubElement(
                        xml_tokens,
                        "token",
                        base = pointer,
                        surf = pointer,
                        id = token_name,
                        offsetBegin = str(token_offset_count),
                        offsetEnd = str(token_offset_count_end),
                    )
                    return_stack.append(
                        _t2jg_Writer(
                            token_span_begin = token_id_count,
                            token_span_end = token_id_count_end,
                            token_span_name = token_name,
                            is_terminal = True,
                            pointer = token_xml,
                        )
                    )

                    # update counters
                    token_id_count = token_id_count_end
                    token_offset_count = token_offset_count_end
                else:
                    raise TypeError

        # get the root node
        xml_ccgs.set("root", return_stack[0].token_span_name)

        # 2. Morph Analysis
        _morph_analyze_janome(xml_tokens)

        return xml_pool
    except Exception as e:
        logger.error(
            f"Conversion error at Tree {ID}. The tree will be discarded.",
            exc_info = True,
        )
        raise JIGGConvException(ID) from e
