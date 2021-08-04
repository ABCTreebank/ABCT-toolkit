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
        assert ABCCat.parse("S|NP") == ABCCatFunctor(
            func_mode = ABCCatFunctorMode.VERT,
            ant = ABCCatBase("NP"),
            conseq = ABCCatBase("S"),
        )
#
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

    def test_simplify_exh(self):
        test_items = (
            (("S/NP", "NP"), ("S", "R0")),
            (("S|NP", "NP"), ("S", "V0")),
            (("NP", "NP\\S"), ("S", "L0")),
            (("A\\B", "B\\C"), ("A\\C", "L1")),
            (("C/B", "B/A"), ("C/A", "R1")),
            (("C/<B\\A>", "B\\A"), ("C", "R0")),
        )
        for (left, right), (cat_exp, res_exp) in test_items:
            res_set = ABCCat.simplify_exh(left, right)
            assert (ABCCat.p(cat_exp), res_exp) in {
                (cat, str(res)) for cat, res in res_set
            }

    def test_mul(self):
        test_items = (
            (("S/NP", "NP"), ("S", "R0")),
            (("S|NP", "NP"), ("S", "V0")),
            (("NP", "NP\\S"), ("S", "L0")),
            (("A\\B", "B\\C"), ("A\\C", "L1")),
            (("C/B", "B/A"), ("C/A", "R1")),
            (("C/<B\\A>", "B\\A"), ("C", "R0")),
        )
        for (left, right), (cat_exp, _) in test_items:
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