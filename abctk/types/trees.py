import typing
import enum

import collections
import itertools

import attr
import parsy

from nltk.tree import Tree
import lxml.etree as le
from . import jigg

@attr.s(
    auto_attribs = True, # Unnecessary in newer version of Python
    frozen = True,
    slots = True,
)
class Tree_with_ID():
    ID: typing.Any
    content: Tree

    @classmethod
    def from_Tree(cls, tree: Tree):
        id_got: typing.Any = None
        tree_got: Tree = tree

        if len(tree) == 2:
            first_child = tree[0]
            last_child = tree[1]
            if (
                isinstance(last_child, Tree) 
                and last_child.label() == "ID"
                and len(last_child) == 1
            ):
                id_node = last_child[0]
                if not isinstance(id_node, Tree):
                    tree_got, id_got = first_child, id_node
                else:
                    pass
            else:
                pass
        else:
            pass

        return cls(id_got, tree_got)
    # === END ===


    def to_jigg(
        self, 
        counter: int = 0,
        label_prefix: typing.Optional[str] = None,
        non_term_to_jigg: typing.Optional[jigg.Func_to_Jigg] = None,
        term_to_jigg: typing.Optional[jigg.Func_to_Jigg] = None,
        spacer: str = " ",
    ) -> jigg.Results_Jigg:
        if label_prefix is None:
            label_prefix = str(self.ID)
        else:
            pass
        # === END IF ===
        self_tree: Tree = self.content

        res: "le._Element" = le.Element(
            "sentence",
            id = label_prefix,
        )

        # append the raw text
        res.text = spacer.join(map(str, self_tree.leaves()))

        # append tokens

        res_tree_overall: jigg.Results_Jigg = subtree_to_jigg(
            subtree = self_tree,
            counter = counter,
            label_prefix = f"{label_prefix}_",
            non_term_to_jigg = non_term_to_jigg,
            term_to_jigg = term_to_jigg,
        )

        res_groups: typing.DefaultDict[str, "le._Element"] = dict()

        for group, elem in res_tree_overall.elems:
            if group in res_groups:
                res_groups[group].append(elem)
            else:
                group_new: "le._Element" = le.Element(
                    group,
                )
                group_new.append(elem)
                res_groups[group] = group_new
            # === END IF ===
        # === END FOR group, elem === 
        #print(res_groups)
        res.extend(res_groups.values())

        return jigg.Results_Jigg(
            counter_incr = counter,
            attrs_to_be_added = tuple(),
            elems = (
                ("sentences", res),
            )
        )
    # === END ===
# === END CLASS ===

def subtree_to_jigg(
    subtree: typing.Union[Tree, typing.Any],
    counter: int = 0,
    label_prefix: str = 0,
    non_term_to_jigg: typing.Optional[jigg.Func_to_Jigg] = None,
    term_to_jigg: typing.Optional[jigg.Func_to_Jigg] = None,
) -> jigg.Results_Jigg:
    if isinstance(subtree, Tree):
        # non-terminal
        label: typing.Any = subtree.label()
        label_id: str = f"{label_prefix}s{counter}"; counter += 1

        label_elem: "le._Element" = le.Element(
            "span",
            id = label_id,
            symbol = str(label),
        )

        children_elems: typing.Iterator[typing.Tuple[str, "le._Element"]] = iter(())
        children_atts_to_be_added: typing.DefaultDict[str, typing.List[str]] = collections.defaultdict(list)
        
        for child in subtree:
            res_child_overall: jigg.Results_Jigg = subtree_to_jigg(
                subtree = child,
                counter = counter,
                label_prefix = label_prefix,
                non_term_to_jigg = non_term_to_jigg,
                term_to_jigg = term_to_jigg,
            ); counter = res_child_overall.counter_incr

            for attr, val in res_child_overall.attrs_to_be_added:
                children_atts_to_be_added[attr].append(val)
            # === END FOR attr, val ===

            children_elems = itertools.chain(children_elems, res_child_overall.elems)
        # === END FOR child ===

        res_label_addelems: typing.Iterator[typing.Tuple[str, "le._Element"]] = iter(())

        if non_term_to_jigg:
            res_label_addelem_overall: jigg.Results_Jigg = non_term_to_jigg(
                label,
                counter = counter,
                label_prefix = label_prefix,
            ); counter = res_label_addelem_overall.counter_incr

            for attr, val in res_label_addelem_overall.attrs_to_be_added:
                children_atts_to_be_added[attr].append(val)
            # === END FOR attr, val ===

            res_label_addelems = res_label_addelem_overall.elems
        else:
            pass
        # === END IF ===

        label_elem.attrib.update(
            (attr, " ".join(val))
            for attr, val in children_atts_to_be_added.items()
        )

        return jigg.Results_Jigg(
            counter_incr = counter,
            attrs_to_be_added = (
                ("children", label_id),
            ),
            elems = itertools.chain(
                (
                    ("spans", label_elem),
                ),
                children_elems,
                res_label_addelems,
            ),
        )
    else:
        # terminal
        token_id: str = f"{label_prefix}t{counter}"; counter += 1

        token_elem: "le._Element" = le.Element(
            "token",
            id = token_id,
            form = str(subtree),
        )

        res_token_addelems: typing.Iterator[typing.Tuple[str, "le._Element"]] = iter(())
        token_attrs_to_be_added: typing.DefaultDict[str, typing.List[str]] = collections.defaultdict(list)

        if term_to_jigg:
            res_token_addelem_overall: jigg.Results_Jigg = term_to_jigg(
                label,
                counter,
            ); counter = res_token_addelem_overall.counter_incr

            for attr, val in res_token_addelem_overall.attrs_to_be_added:
                token_attrs_to_be_added[attr].append(val)
            # === END FOR attr, val ===

            res_token_addelems = res_token_addelem_overall.elems
        else:
            pass
        # === END IF ===
        
        token_elem.attrib.update(
            (attr, " ".join(val))
            for attr, val in token_attrs_to_be_added.items()
        )

        return jigg.Results_Jigg(
            counter_incr = counter,
            attrs_to_be_added = (
                ("children", token_id),
            ),
            elems = itertools.chain(
                (
                    ("tokens", token_elem),
                ),
                res_token_addelems
            ),
        )
    # === END IF ===
# === END ===

class TreeParen(enum.Enum):
    OPEN = "("
    CLOSE = ")"
# === END CLASS ===

lexer_Tree: parsy.Parser = (
    parsy.from_enum(TreeParen)
    | parsy.regex(r"[^\s()]+")
    | parsy.whitespace.result(None)
).many().map(lambda li: list(filter(None, li)))

def parser_Tree(
    parser_non_terminal: parsy.Parser = parsy.regex(r".*"),
    parser_terminal: parsy.Parser = parsy.regex(r".*"),
) -> parsy.Parser:
    _parser_str: parsy.Parser = parsy.test_item(
        lambda i: isinstance(i, str),
        "a string demarcated by the lexer"
    )

    @parsy.generate
    def _parser_comp_node(): 
        yield parsy.match_item(TreeParen.OPEN) 
        label = yield _parser_str.map(parser_non_terminal.parse).optional()
        children = yield (
            _parser_str.map(parser_terminal.parse)
            | _parser_comp_node
        ).many()
        yield parsy.match_item(TreeParen.CLOSE)

        return Tree(label, children)
    # === END ===

    return _parser_comp_node
# === END ===

def parse_Tree(
    text: str, 
    parser_non_terminal: parsy.Parser = parsy.regex(r".*"),
    parser_terminal: parsy.Parser = parsy.regex(r".*"),
) -> Tree:
    text_lexed: typing.List[str] = lexer_Tree.parse(text)
    return parser_Tree(parser_non_terminal, parser_terminal).parse(text_lexed)
# === END ===

def parser_Tree_with_ID(
    parser_non_terminal: parsy.Parser = parsy.regex(r".*"),
    parser_terminal: parsy.Parser = parsy.regex(r".*"),
) -> parsy.Parser:
    _parser_str: parsy.Parser = parsy.test_item(
        lambda i: isinstance(i, str),
        "a string demarcated by the lexer"
    )

    @parsy.generate
    def _parser(): 
        yield parsy.match_item(TreeParen.OPEN)
        tree = yield parser_Tree(
            parser_non_terminal = parser_non_terminal,
            parser_terminal = parser_terminal,
        )

        yield parsy.match_item(TreeParen.OPEN)
        yield parsy.match_item("ID")
        ID = yield parsy.test_item(
            lambda i: isinstance(i, str),
            "a Tree ID",
        )
        yield parsy.match_item(TreeParen.CLOSE)
        yield parsy.match_item(TreeParen.CLOSE)

        return Tree_with_ID(
            ID = ID,
            content = tree,
        )
    # === END ===

    return _parser
# === END ===

def parse_Tree_with_ID(
    text: str, 
    parser_non_terminal: parsy.Parser = parsy.regex(r".*"),
    parser_terminal: parsy.Parser = parsy.regex(r".*"),
) -> Tree_with_ID:
    text_lexed: typing.List[str] = lexer_Tree.parse(text)
    return (
        parser_Tree_with_ID(parser_non_terminal, parser_terminal)
        | parser_Tree(parser_non_terminal, parser_terminal).map(
            lambda tree: Tree_with_ID(
                ID = "<N/A>",
                content = tree,
            )
        )
    ).parse(text_lexed)
# === END ===