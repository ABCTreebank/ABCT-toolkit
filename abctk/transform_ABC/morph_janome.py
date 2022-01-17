import typing

from nltk.tree import Tree
import janome.lattice
from janome.lattice import Node as JNode
import janome.tokenizer
from janome.tokenizer import Token as JToken

import abctk.types.ABCCat as abcc

class ABCMorphAnalyzer(janome.tokenizer.Tokenizer):
    def analyze(
        self, 
        text: typing.Sequence[str], 
        *, 
        baseform_unk: bool = True, 
    ) -> list[JToken]:
        """
        Give a morphological analysis of an input text which is tokenized beforehand.

        Arguments
        ----------
        text:
            A text, tokenized beforehand.
        baseform_unk: bool
            If given True sets base_form attribute for unknown tokens.

        Yields
        ------
        token: str
        """

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

        return tokens

_janome_tokenizer: typing.Optional[ABCMorphAnalyzer] = None

def _serialize_JToken(ana: JToken):
    return f'{ana.part_of_speech},{ana.infl_type},{ana.infl_form},{ana.base_form},{ana.reading},{ana.phonetic}'
    # TODO: escape #

def add_morph_janome(
    tree: Tree,
    ID: str = "<UNKNOWN>"
):
    # 1. Collect lexical nodes
    def yield_tokens(node: Tree):
        for child in node:
            if isinstance(child, Tree):
                yield from yield_tokens(child)
            elif isinstance(child, str):
                if (
                    not child.startswith("*")
                    and not child.startswith("__")
                ):
                    yield (child, node)
            else:
                pass
    tokens = tuple(yield_tokens(tree))

    # 2. Analyze
    global _janome_tokenizer
    if _janome_tokenizer is None:
        _janome_tokenizer = ABCMorphAnalyzer()

    tokens_analyzed = _janome_tokenizer.analyze(
        tuple(word for word, _ in tokens)
    )

    # 3. Merge into the tree nodes
    for ana, (_, node) in zip(tokens_analyzed, tokens):
        label = node.label()
        if isinstance(label, abcc.Annot):
            label.feats["janome"] = _serialize_JToken(ana)
        else:
            node.set_label(
                abcc.Annot(
                    cat = label,
                    feats = {
                        "janome": _serialize_JToken(ana)
                    }
                )
            )
    # === END ===

def del_morph_janome(tree: Tree, ID: str = "<UNKNOWN>"):
    label = tree.label()

    if isinstance(label, abcc.Annot):
        label.feats.pop("janome", None)

    for child in tree:
        if isinstance(child, Tree):
            del_morph_janome(child, ID)
