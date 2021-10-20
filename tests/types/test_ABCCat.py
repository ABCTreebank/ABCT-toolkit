import pytest

from abctk.types.ABCCat import *

class Test_DepMk:
    def test_parse(self):
        assert DepMk("none") == DepMk.NONE
        assert DepMk("h") == DepMk.HEAD
        assert DepMk("c") == DepMk.COMPLEMENT
        assert DepMk("a") == DepMk.ADJUNCT
        assert DepMk("ac") == DepMk.ADJUNCT_CONTROL

def test_parse_pprint_annot():
    test_items = (
        ("a", "#role=c"),
        ("<a/b/c>", "#deriv=stref#comp-id=1"),
    )

    for item in test_items:
        cat, feats = parse_annot("".join(item))
        assert cat == item[0]
        feat_str = annot_feat_pprint(feats)
        cat, feats_2 = parse_annot(feat_str)
        assert feats == feats_2

class Test_ABCCat:
    parse_items = (
        ("⊥", ABCCatBot.BOT),
        ("NP", ABCCatBase("NP")),
        ("<NP\\S>", ABCCatFunctor(
                func_mode = ABCCatFunctorMode.LEFT,
                ant = ABCCatBase("NP"),
                conseq = ABCCatBase("S"),
            )
        ),
        ("<S/NP>", ABCCatFunctor(
                func_mode = ABCCatFunctorMode.RIGHT,
                ant = ABCCatBase("NP"),
                conseq = ABCCatBase("S"),
            )
        ),
        ("S/NP", ABCCatFunctor(
                func_mode = ABCCatFunctorMode.RIGHT,
                ant = ABCCatBase("NP"),
                conseq = ABCCatBase("S"),
            )
        ),
        ("S|NP", ABCCatFunctor(
                func_mode = ABCCatFunctorMode.VERT,
                ant = ABCCatBase("NP"),
                conseq = ABCCatBase("S"),
            )
        ),
    )

    @pytest.mark.parametrize("input, answer", parse_items)
    def test_parse(self, input, answer):
        assert ABCCat.parse(input) == answer

    def test_parse_pprint(self):
        test_items = (
            "⊥", "NP", "NP\\S", "<NP\\S>", "<S/NP>",
            "<NP\\<NP\\NP>>",
            "<S/NP>\\<S/NP>",
            "S|NP",
            "S|NP|NP",
        )

        for item in test_items:
            parse_1 = ABCCat.parse(item)
            parse_2 = ABCCat.parse(parse_1.pprint())
            assert parse_1 == parse_2

    def test_r(self):
        assert ABCCat.p("S").r("NP") == ABCCat.p("S/NP")
        assert ABCCat.p("S") / "NP" == ABCCat.p("S/NP")
    
    def test_l(self):
        assert ABCCat.p("NP").l("S") == ABCCat.p("NP\\S")

    def test_adjunct(self):
        assert ABCCat.p("S/NP").adj_l() == ABCCat.p("<S/NP>\\<S/NP>")
        assert ABCCat.p("NP\\S").adj_r() == ABCCat.p("<NP\\S>/<NP\\S>")

    _lexer_items = [
        (
            "<ABC/DE>>F//G\\\\H<>JJK//L/MM/N",
            ("<", "ABC", "/", "DE", ">", ">", "F", "/", "/", "G", "\\", "\\", "H", "<", ">", "JJK", "/", "/", "L", "/", "MM", "/", "N"),
            None
        ),
        ("DE//<", ("DE", "/", "/", "<"), None),
        (
            "(ABC/DE))F//G\\\\H()JJK//L/MM/N",
            ("(", "ABC", "/", "DE", ")", ")", "F", "/", "/", "G", "\\", "\\", "H", "(", ")", "JJK", "/", "/", "L", "/", "MM", "/", "N"),
            "/\\()⊥⊤"
        ),
        ("DE//(", ("DE", "/", "/", "("), "/\\()⊥⊤"),
    ]

    @pytest.mark.parametrize("input, answer, symbols", _lexer_items)
    def test__lexer(self, input, answer, symbols):
        if symbols:
            res = tuple(ABCCat._lexer(input, symbols))
        else:
            res = tuple(ABCCat._lexer(input))

        assert res == answer

    simp_items = [
        (("S/NP", "NP"), ("S", ">")),
        (("S|NP", "NP"), ("S", "|")),
        (("PPs", "S|PPs"), ("S", "|")),
        (("NP", "NP\\S"), ("S", "<")),
        (("A\\B", "B\\C"), ("A\\C", "<B1")),
        (("C/B", "B/A"), ("C/A", ">B1")),
        (("C/<B\\A>", "B\\A"), ("C", ">")),
        (
            (
                "<<PPs\\Srel>/<PPs\\Srel>>",
                "<<<PPs\\Srel>/<PPs\\Srel>>\\<<PPs\\Srel>/<PPs\\Srel>>>"
            ),
            ("<<PPs\\Srel>/<PPs\\Srel>>", "<"),
        )
    ]

    @pytest.mark.parametrize("input, answer", simp_items)
    def test_simplify_exh(self, input, answer):
        left, right = input
        cat_exp, res_exp = answer
        
        res_set = ABCCat.simplify_exh(left, right)
        assert (ABCCat.p(cat_exp), res_exp) in {
            (cat, str(res)) for cat, res in res_set
        }

    @pytest.mark.parametrize("input, answer", simp_items)
    def test_mul(self, input, answer):
        left, right = input
        cat_exp, res_exp = answer

        res = ABCCat.p(left) * right
        assert res == ABCCat.p(cat_exp)

    def test_invert_dir(self):
        test_items = (
            ("⊥", "⊥"),
            ("NP", "NP"),
            ("NP\\S", "S/NP"),
            ("NP/S", "S\\NP"),
            ("S|NP", "S|NP"),
        )

        for item, res_exp in test_items:
            item_parsed = ABCCat.p(item)
            res_exp_parsed = ABCCat.p(res_exp)

            assert ~item_parsed == res_exp_parsed
            assert item_parsed == ~res_exp_parsed

        assert ~(ABCCat.p("S") / ABCCat.p("NP")) == ABCCat.p("NP\\S")

class Test_ABCCatBase:
    def test_tell_feature(self):
        test_items = (
            ("S", "m"),
            ("S3m", None),
            ("S", "m3"),
        )

        for cat, feat in test_items:
            if feat is None:
                assert typing.cast(ABCCatBase, ABCCat.p(cat)).tell_feature() is None
            else:
                d = typing.cast(ABCCatBase, ABCCat.p(cat + feat)).tell_feature()
                assert d is not None
                assert cat == d["cat"]
                assert feat == d["feat"]

class Test_ABCCatFunctor:
    def test_reduce_with(self):
        test_items = (
            (("S/NP", "NP", False), "S"),
            (("NP\\S", "NP", True), "S"),
            (("C/<B\\A>", "B\\A", False), "C"),
            (("C|<B\\A>", "B\\A", False), "C"),
        )

        for (func, ant, ant_left), res_exp in test_items:
            f = typing.cast(ABCCatFunctor, ABCCat.parse(func))
            res = f.reduce_with(ant, ant_left)
            assert res == ABCCat.parse(res_exp)

    pprint_items = (
        ("C/<B\\A>", ABCCatReprMode.TLCG, "<C/<B\\A>>"),
        ("C/<B\\A>", ABCCatReprMode.TRADITIONAL, "<C/<A\\B>>"),
        ("C/<Bm3/A>", ABCCatReprMode.DEPCCG, "(C/(B[m3]/A))"),
    )

    @pytest.mark.parametrize("input, mode, answer", pprint_items)
    def test_pprint(self, input, mode, answer):

        assert ABCCat.p(input).pprint(mode) == answer