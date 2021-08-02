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
    def test_parse(self):
        assert ABCCat.parse("⊥") == ABCCatBot.BOT
        assert ABCCat.parse("NP") == ABCCatBase("NP")
        assert ABCCat.parse("<NP\\S>") == ABCCatFunctor(
            func_mode = ABCCatFunctorMode.LEFT,
            ant = ABCCatBase("NP"),
            conseq = ABCCatBase("S"),
        )
        assert ABCCat.parse("<S/NP>") == ABCCatFunctor(
            func_mode = ABCCatFunctorMode.RIGHT,
            ant = ABCCatBase("NP"),
            conseq = ABCCatBase("S"),
        )
        assert ABCCat.parse("S/NP") == ABCCatFunctor(
            func_mode = ABCCatFunctorMode.RIGHT,
            ant = ABCCatBase("NP"),
            conseq = ABCCatBase("S"),
        )
#
    def test_parse_pprint(self):
        test_items = (
            "⊥", "NP", "NP\\S", "<NP\\S>", "<S/NP>",
            "<NP\\<NP\\NP>>",
            "<S/NP>\\<S/NP>",
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

    def test_apply(self):
        test_items = (
            (("S/NP", "NP"), ("S", "R0")),
            (("NP", "NP\\S"), ("S", "L0")),
            (("A\\B", "B\\C"), ("A\\C", "L1")),
            (("C/B", "B/A"), ("C/A", "R1")),
            (("C/<B\\A>", "B\\A"), ("C", "R0")),
        )
        for item, res_expected in test_items:
            cat, code = ABCCat.apply(*item)
            assert cat == ABCCat.p(res_expected[0])
            assert str(code) == res_expected[1]

    def test_mul(self):
        test_items = (
            (("S/NP", "NP"), "S"),
            (("NP", "NP\\S"), "S"),
            (("A\\B", "B\\C"), "A\\C"),
            (("C/B", "B/A"), "C/A"),
            (("C/<B\\A>", "B\\A"), "C"),
        )

        for item, res_expected in test_items:
            assert ABCCat.p(item[0]) * ABCCat.p(item[1]) == ABCCat.p(res_expected)

    def test_invert_dir(self):
        test_items = (
            ("⊥", "⊥"),
            ("NP", "NP"),
            ("NP\\S", "S/NP"),
            ("NP/S", "S\\NP"),
        )

        for item, res_exp in test_items:
            item_parsed = ABCCat.p(item)
            res_exp_parsed = ABCCat.p(res_exp)

            assert ~item_parsed == res_exp_parsed
            assert item_parsed == ~res_exp_parsed

        assert ~(ABCCat.p("S") / ABCCat.p("NP")) == ABCCat.p("NP\\S")