"""Phase 2 automated tests — Versioned Rule Engine.

Run: python -m kf_asset_manager.tests_phase2
Exits non-zero on any failure.
"""
import sys

from . import rules

PASS, FAIL = [], []


def check(name, cond):
    (PASS if cond else FAIL).append(name)
    print(("  ok  " if cond else " FAIL ") + name)


def run():
    p = lambda fn, folder=None: rules.parse(fn, folder)

    # --- flat curtains -----------------------------------------------------
    L = p("Kids-3141-L.jpg")
    R = p("Kids-3141-R.jpg")
    check("flat curtain matched by flat_curtain rule", L["rule"] == "flat_curtain")
    check("curtain L side normalised to L", L["side"] == "L")
    check("curtain R side normalised to R", R["side"] == "R")
    check("curtain L/R share a design key", L["design_key"] == R["design_key"])
    A = p("Paintings 4098-A.jpg")
    B = p("Paintings 4098-B.jpg")
    check("legacy curtain A -> L", A["side"] == "L")
    check("legacy curtain B -> R", B["side"] == "R")
    check("legacy curtain A flagged legacy_ab", A["legacy_ab"] is True)
    check("curtain A/B share design key (one paired design)", A["design_key"] == B["design_key"])
    C = p("Kids-3061-C.jpg")
    check("curtain -C is merged single", C["is_merged"] is True)
    check("merged single has its own design key", C["design_key"] != p("Kids-3061-L.jpg")["design_key"])

    # --- batched sets ------------------------------------------------------
    s1 = p("(18-11) C4-A.jpg")
    s2 = p("(18-11) C4-A-cushion.jpg")
    check("set matched by batched_set rule", s1["rule"] == "batched_set")
    check("set code is batch-qualified", s1["set_code"] == "18-11/C4")
    check("set curtain typed as Curtain Panel Set", s1["asset_type"] == "Curtain Panel Set")
    check("set cushion typed as Cushion", s2["asset_type"] == "Cushion")
    check("set curtain and cushion are different designs",
          s1["design_key"] != s2["design_key"])
    n1 = p("(18-11) C6-cushion 1.jpg")
    n2 = p("(18-11) C6-cushion 2.jpg")
    check("numbered cushions are distinct designs", n1["design_key"] != n2["design_key"])
    cur6 = p("(18-11) C6.jpg")
    check("set with no piece word is the curtain", cur6["asset_type"] == "Curtain Panel Set")
    # batch is part of identity
    check("(18-11) C1 != (19-11) C1",
          p("(18-11) C1-A.jpg")["set_code"] != p("(19-11) C1-A.jpg")["set_code"])

    # --- D-variants (new canonical convention) -----------------------------
    d1 = p("(20-11) C5-D1.jpg")
    d2 = p("(20-11) C5-D2.jpg")
    check("D-variant parsed in set", d1["design_variant"] == "D1")
    check("D1 and D2 are distinct designs", d1["design_key"] != d2["design_key"])
    check("D-variant is NOT a legacy_ab", d1["legacy_ab"] is False)

    # --- legacy non-curtain A/B (backward-compatible only) -----------------
    ca = p("(18-11) C3-A-cushion.jpg")
    cb = p("(18-11) C3-B-cushion.jpg")
    check("legacy cushion A/B flagged legacy_ab", ca["legacy_ab"] is True and cb["legacy_ab"] is True)
    check("legacy cushion A/B are distinct designs", ca["design_key"] != cb["design_key"])

    # --- versioning + review ----------------------------------------------
    check("rules_version present on result", L["rules_version"] == rules.RULES_VERSION)
    junk = p("totally_unstructured_name.jpg", "Curtains")
    check("unrecognised name falls back and needs review", junk["needs_review"] is True)
    check("fallback confidence is low", junk["confidence"] <= 0.5)
    check("matched rule confidence is high", s1["confidence"] >= 0.9)

    print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
    return 0 if not FAIL else 1


def _base_main():
    return run()


def run_panel():
    """Engineered-panel (P####) rule — added when the real library audit justified it."""
    import sys
    from . import rules
    p = lambda fn: rules.parse(fn, "Curtains")
    P, F = [], []
    def ck(n, c): (P if c else F).append(n); print(("  ok  " if c else " FAIL ")+n)
    ck("P#### no-space parses", p("P4186-L.jpg")["rule"] == "engineered_panel")
    ck("P #### legacy space parses to same code", p("P 4022-L.jpg")["family_code"] == "P4022")
    ck("L/R panels share one design", p("P4186-L.jpg")["design_key"] == p("P4186-R.jpg")["design_key"])
    ck("derived cushion stays in curtain design",
       p("P4186-L-cush.jpg")["design_key"] == p("P4186-L.jpg")["design_key"])
    ck("derived cushion flagged is_derived", p("P4186-L-cush.jpg")["is_derived"] is True)
    ck("cushion artwork_role Derived", p("P4186-L-cush.jpg")["artwork_role"] == "Derived")
    ck("V2 is a sibling design (different key)",
       p("P4204-V2.jpg")["design_key"] != p("P4204.jpg")["design_key"])
    ck("V2 shares the family code with master",
       p("P4204-V2.jpg")["family_code"] == p("P4204.jpg")["family_code"] == "P4204")
    ck("merged C is the same design as L/R",
       p("P 4022-C.jpg")["design_key"] == p("P 4022-L.jpg")["design_key"])
    ck("bare -2 normalises to V2 (sibling design)", p("P4124-2.jpg")["design_variant"] == "V2")
    ck("-2 cushion is derived in the V2 design",
       p("P4124-2-cush.jpg")["design_key"] == p("P4124-2.jpg")["design_key"]
       and p("P4124-2-cush.jpg")["is_derived"] is True)
    ck("bare -A is a version sibling (not a side)",
       p("P4206-A.jpg")["design_variant"] == "A" and p("P4206-A.jpg")["side"] is None)
    ck("-A design differs from the master design",
       p("P4206-A.jpg")["design_key"] != p("P4206.jpg")["design_key"])
    ck("double/standalone spaces tolerated", p("P  4063.jpg")["rule"] == "engineered_panel")
    ck("version + side combine (P 4047-2-L)",
       p("P 4047-2-L.jpg")["design_variant"] == "V2" and p("P 4047-2-L.jpg")["side"] == "L")
    ck(f"rules_version is {rules.RULES_VERSION}", p("P4186-L.jpg")["rules_version"] == rules.RULES_VERSION)
    print(f"\n{len(P)} passed, {len(F)} failed")
    return 0 if not F else 1


if __name__ == "__main__":
    import sys as _s
    rc1 = run()
    print("\n--- engineered panel ---")
    rc2 = run_panel()
    _s.exit(rc1 or rc2)
